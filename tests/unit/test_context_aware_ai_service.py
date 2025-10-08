"""Unit tests for context-aware AI service."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.services.context_aware_ai_service import (
    ContextAwareAIService,
    EnhancedTask
)
from src.services.mcp_jira_service import ProjectContext
from src.services.ai_service import OllamaService
from src.config import AppConfig, OllamaConfig, JiraConfig


class TestContextAwareAIService:
    """Test cases for ContextAwareAIService."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AppConfig(
            debug=True,
            ollama=OllamaConfig(
                model_name="test-model",
                base_url="http://localhost:11434",
                timeout=30
            ),
            jira=JiraConfig(
                similarity_threshold=0.85,
                max_search_results=10
            )
        )
    
    @pytest.fixture
    def mock_mcp_service(self):
        """Create mock MCP JIRA service."""
        mock_service = AsyncMock()
        
        # Mock project context
        mock_context = ProjectContext(
            key='TEST',
            name='Test Project',
            description='Test project description',
            project_type='software',
            lead='Test Lead',
            active_sprint={'id': 'sprint-1', 'name': 'Sprint 1'},
            epics=[
                {'key': 'TEST-100', 'summary': 'User Authentication Epic'},
                {'key': 'TEST-200', 'summary': 'Payment Integration Epic'}
            ],
            issue_types=[
                {'id': '1', 'name': 'Story'},
                {'id': '2', 'name': 'Task'},
                {'id': '3', 'name': 'Bug'}
            ],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        mock_service.get_project_context.return_value = mock_context
        return mock_service
    
    @pytest.fixture
    def context_aware_service(self, test_config, mock_mcp_service):
        """Create context-aware AI service instance."""
        return ContextAwareAIService(test_config, mock_mcp_service)
    
    @pytest.fixture
    def sample_project_context(self):
        """Sample project context for testing."""
        return ProjectContext(
            key='TEST',
            name='Test Project',
            description='E-commerce platform',
            project_type='software',
            lead='John Doe',
            active_sprint={'id': 'sprint-1', 'name': 'Sprint 1'},
            epics=[
                {'key': 'TEST-100', 'summary': 'User Authentication'},
                {'key': 'TEST-200', 'summary': 'Payment Processing'}
            ],
            issue_types=[
                {'id': '1', 'name': 'Story'},
                {'id': '2', 'name': 'Task'},
                {'id': '3', 'name': 'Bug'}
            ],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
    
    def test_service_initialization(self, context_aware_service, test_config, mock_mcp_service):
        """Test service initializes correctly."""
        assert context_aware_service.config == test_config
        assert context_aware_service.mcp_service == mock_mcp_service
        assert isinstance(context_aware_service.base_ai_service, OllamaService)
    
    @pytest.mark.asyncio
    async def test_extract_with_project_context_success(self, context_aware_service):
        """Test successful extraction with project context."""
        transcript = "John: Can you implement the login feature? Sarah: Yes, I'll work on that."
        project_key = "TEST"
        
        # Mock base AI service response
        mock_tasks = [
            {
                'summary': 'Implement login feature',
                'description': 'Add user login functionality',
                'issue_type': 'Task',
                'reporter': 'test@example.com',
                'due_date': ''
            }
        ]
        
        with patch.object(context_aware_service.base_ai_service, 'parse_transcript', return_value=mock_tasks):
            with patch.object(context_aware_service, '_enhance_task_with_context') as mock_enhance:
                mock_enhanced = EnhancedTask(
                    summary='Implement login feature',
                    description='Add user login functionality',
                    issue_type='Task',
                    confidence_score=0.8
                )
                mock_enhance.return_value = mock_enhanced
                
                result = await context_aware_service.extract_with_project_context(
                    transcript,
                    project_key,
                    "Additional context"
                )
                
                assert isinstance(result, list)
                assert len(result) > 0
                assert isinstance(result[0], EnhancedTask)
    
    @pytest.mark.asyncio
    async def test_extract_with_project_context_fallback(self, context_aware_service, mock_mcp_service):
        """Test extraction with fallback when context fails."""
        transcript = "Test transcript"
        project_key = "TEST"
        
        # Make context retrieval fail
        mock_mcp_service.get_project_context.side_effect = Exception("Context error")
        
        mock_tasks = [
            {
                'summary': 'Test task',
                'description': 'Test description',
                'issue_type': 'Task'
            }
        ]
        
        with patch.object(context_aware_service.base_ai_service, 'parse_transcript', return_value=mock_tasks):
            result = await context_aware_service.extract_with_project_context(
                transcript,
                project_key
            )
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], EnhancedTask)
    
    @pytest.mark.asyncio
    async def test_suggest_issue_types_success(self, context_aware_service, sample_project_context):
        """Test successful issue type suggestions."""
        task_content = "Fix the login button alignment bug"
        
        # Mock AI response
        mock_response = {
            'suggestions': [
                {
                    'type': 'Bug',
                    'confidence': 0.9,
                    'reasoning': 'Task describes a fix for a bug'
                },
                {
                    'type': 'Task',
                    'confidence': 0.3,
                    'reasoning': 'Could be a general task'
                }
            ]
        }
        
        with patch.object(context_aware_service.base_ai_service, '_call_ollama', return_value="mock"):
            with patch.object(context_aware_service.base_ai_service, '_parse_single_task', return_value=mock_response):
                suggestions = await context_aware_service.suggest_issue_types(
                    task_content,
                    sample_project_context
                )
                
                assert isinstance(suggestions, list)
                assert len(suggestions) > 0
                assert suggestions[0]['type'] == 'Bug'
                assert suggestions[0]['confidence'] == 0.9
    
    @pytest.mark.asyncio
    async def test_suggest_issue_types_with_invalid_types(self, context_aware_service, sample_project_context):
        """Test issue type suggestions filtering out invalid types."""
        task_content = "Implement feature"
        
        mock_response = {
            'suggestions': [
                {'type': 'InvalidType', 'confidence': 0.9, 'reasoning': 'Test'},
                {'type': 'Task', 'confidence': 0.8, 'reasoning': 'Valid type'}
            ]
        }
        
        with patch.object(context_aware_service.base_ai_service, '_call_ollama', return_value="mock"):
            with patch.object(context_aware_service.base_ai_service, '_parse_single_task', return_value=mock_response):
                suggestions = await context_aware_service.suggest_issue_types(
                    task_content,
                    sample_project_context
                )
                
                # Should only include valid types
                assert len(suggestions) == 1
                assert suggestions[0]['type'] == 'Task'
    
    @pytest.mark.asyncio
    async def test_suggest_issue_types_fallback(self, context_aware_service, sample_project_context):
        """Test issue type suggestions with fallback."""
        task_content = "Test content"
        
        with patch.object(context_aware_service.base_ai_service, '_call_ollama', side_effect=Exception("AI error")):
            suggestions = await context_aware_service.suggest_issue_types(
                task_content,
                sample_project_context
            )
            
            # Should return default suggestions
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_validate_task_against_schema_valid(self, context_aware_service, sample_project_context):
        """Test validation of valid task against schema."""
        task = {
            'summary': 'Implement feature',
            'description': 'Add new feature to the system',
            'issue_type': 'Task'
        }
        
        result = await context_aware_service.validate_task_against_schema(
            task,
            sample_project_context
        )
        
        assert result['is_valid'] is True
        assert isinstance(result['warnings'], list)
        assert isinstance(result['errors'], list)
        assert isinstance(result['suggestions'], list)
    
    @pytest.mark.asyncio
    async def test_validate_task_against_schema_long_summary(self, context_aware_service, sample_project_context):
        """Test validation of task with too long summary."""
        task = {
            'summary': 'x' * 300,  # Exceeds 255 character limit
            'description': 'Test description',
            'issue_type': 'Task'
        }
        
        result = await context_aware_service.validate_task_against_schema(
            task,
            sample_project_context
        )
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert any('exceeds maximum length' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_validate_task_against_schema_invalid_issue_type(self, context_aware_service, sample_project_context):
        """Test validation of task with invalid issue type."""
        task = {
            'summary': 'Test task',
            'description': 'Test description',
            'issue_type': 'InvalidType'
        }
        
        result = await context_aware_service.validate_task_against_schema(
            task,
            sample_project_context
        )
        
        assert len(result['warnings']) > 0
        assert any('not available' in warning for warning in result['warnings'])
        assert len(result['suggestions']) > 0
    
    @pytest.mark.asyncio
    async def test_validate_task_against_schema_short_summary(self, context_aware_service, sample_project_context):
        """Test validation of task with very short summary."""
        task = {
            'summary': 'Hi',  # Too short
            'description': 'Test description',
            'issue_type': 'Task'
        }
        
        result = await context_aware_service.validate_task_against_schema(
            task,
            sample_project_context
        )
        
        assert result['is_valid'] is True  # Still valid but with warning
        assert any('very short' in warning for warning in result['warnings'])
    
    @pytest.mark.asyncio
    async def test_auto_categorize_by_epics_success(self, context_aware_service, sample_project_context):
        """Test automatic categorization by epics."""
        tasks = [
            EnhancedTask(
                summary='Implement login feature',
                description='Add user authentication',
                issue_type='Task',
                confidence_score=0.8,
                context_factors=['test']
            ),
            EnhancedTask(
                summary='Add payment gateway',
                description='Integrate payment processing',
                issue_type='Task',
                confidence_score=0.8,
                context_factors=['test']
            )
        ]
        
        with patch.object(context_aware_service, '_suggest_epic_for_task', side_effect=lambda t, c: t):
            result = await context_aware_service.auto_categorize_by_epics(
                tasks,
                sample_project_context
            )
            
            assert len(result) == 2
            assert all(isinstance(task, EnhancedTask) for task in result)
    
    @pytest.mark.asyncio
    async def test_auto_categorize_by_epics_no_epics(self, context_aware_service):
        """Test categorization when no epics available."""
        tasks = [
            EnhancedTask(
                summary='Test task',
                description='Test description',
                issue_type='Task',
                confidence_score=0.8
            )
        ]
        
        context_without_epics = ProjectContext(
            key='TEST',
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[],  # No epics
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        result = await context_aware_service.auto_categorize_by_epics(
            tasks,
            context_without_epics
        )
        
        assert len(result) == 1
        assert result[0].summary == 'Test task'
    
    def test_create_project_aware_context(self, context_aware_service, sample_project_context):
        """Test creation of project-aware context string."""
        additional_context = "Sprint goal: Implement core features"
        
        context_string = context_aware_service._create_project_aware_context(
            sample_project_context,
            additional_context
        )
        
        assert 'Test Project' in context_string
        assert 'TEST' in context_string
        assert 'software' in context_string
        assert 'Sprint 1' in context_string
        assert 'Story, Task, Bug' in context_string
        assert 'User Authentication' in context_string
        assert additional_context in context_string
    
    def test_create_project_aware_context_minimal(self, context_aware_service):
        """Test creation of context with minimal project data."""
        minimal_context = ProjectContext(
            key='MIN',
            name='Minimal Project',
            description='',
            project_type='software',
            lead='',
            epics=[],
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        context_string = context_aware_service._create_project_aware_context(
            minimal_context,
            ""
        )
        
        assert 'Minimal Project' in context_string
        assert 'MIN' in context_string
    
    @pytest.mark.asyncio
    async def test_enhance_task_with_context(self, context_aware_service, sample_project_context):
        """Test enhancement of a single task with context."""
        task = {
            'summary': 'Fix login bug',
            'description': 'Login button not working',
            'issue_type': 'Bug'
        }
        
        with patch.object(context_aware_service, 'suggest_issue_types', return_value=[
            {'type': 'Bug', 'confidence': 0.95, 'reasoning': 'Clear bug description'}
        ]):
            with patch.object(context_aware_service, 'validate_task_against_schema', return_value={
                'is_valid': True,
                'warnings': [],
                'errors': [],
                'suggestions': []
            }):
                with patch.object(context_aware_service, '_find_best_epic_match', return_value='TEST-100'):
                    enhanced = await context_aware_service._enhance_task_with_context(
                        task,
                        sample_project_context
                    )
                    
                    assert isinstance(enhanced, EnhancedTask)
                    assert enhanced.summary == 'Fix login bug'
                    assert enhanced.issue_type == 'Bug'
                    assert enhanced.suggested_epic == 'TEST-100'
                    assert enhanced.validation_status == 'valid'
                    assert enhanced.confidence_score >= 0.0
    
    def test_convert_to_enhanced_task(self, context_aware_service):
        """Test conversion of basic task to enhanced task."""
        basic_task = {
            'summary': 'Basic task',
            'description': 'Basic description',
            'issue_type': 'Task'
        }
        
        enhanced = context_aware_service._convert_to_enhanced_task(basic_task)
        
        assert isinstance(enhanced, EnhancedTask)
        assert enhanced.summary == 'Basic task'
        assert enhanced.description == 'Basic description'
        assert enhanced.issue_type == 'Task'
        assert enhanced.confidence_score == 0.3  # Low confidence for non-enhanced
    
    def test_analyze_issue_type_patterns(self, context_aware_service, sample_project_context):
        """Test analysis of issue type patterns."""
        patterns = context_aware_service._analyze_issue_type_patterns(sample_project_context)
        
        assert isinstance(patterns, dict)
        assert 'story_keywords' in patterns
        assert 'task_keywords' in patterns
        assert 'bug_keywords' in patterns
        assert isinstance(patterns['story_keywords'], list)
        assert isinstance(patterns['bug_keywords'], list)
    
    def test_create_issue_type_prompt(self, context_aware_service, sample_project_context):
        """Test creation of issue type classification prompt."""
        task_content = "Fix the login button"
        patterns = {
            'bug_keywords': ['fix', 'bug', 'error'],
            'task_keywords': ['implement', 'create']
        }
        
        prompt = context_aware_service._create_issue_type_prompt(
            task_content,
            sample_project_context,
            patterns
        )
        
        assert 'Fix the login button' in prompt
        assert 'Story' in prompt
        assert 'Task' in prompt
        assert 'Bug' in prompt
        assert 'JSON' in prompt
    
    def test_get_default_issue_type_suggestions(self, context_aware_service, sample_project_context):
        """Test getting default issue type suggestions."""
        suggestions = context_aware_service._get_default_issue_type_suggestions(
            sample_project_context
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) == len(sample_project_context.issue_types)
        
        # Task should have higher confidence as default
        task_suggestion = next(s for s in suggestions if s['type'] == 'Task')
        assert task_suggestion['confidence'] == 0.6
    
    @pytest.mark.asyncio
    async def test_find_best_epic_match_with_match(self, context_aware_service, sample_project_context):
        """Test finding best epic match with good match."""
        task = {
            'summary': 'Implement user login authentication',
            'description': 'Add login feature for users'
        }
        
        epic_match = await context_aware_service._find_best_epic_match(
            task,
            sample_project_context
        )
        
        # Should match with 'User Authentication' epic
        assert epic_match is not None
        assert epic_match == 'TEST-100'
    
    @pytest.mark.asyncio
    async def test_find_best_epic_match_no_match(self, context_aware_service, sample_project_context):
        """Test finding best epic match with no match."""
        task = {
            'summary': 'Completely unrelated task',
            'description': 'Something different entirely'
        }
        
        epic_match = await context_aware_service._find_best_epic_match(
            task,
            sample_project_context
        )
        
        # Should not match any epic
        assert epic_match is None
    
    @pytest.mark.asyncio
    async def test_find_best_epic_match_no_epics(self, context_aware_service):
        """Test finding epic match when no epics exist."""
        task = {'summary': 'Test task', 'description': 'Test'}
        
        context_without_epics = ProjectContext(
            key='TEST',
            name='Test',
            description='',
            project_type='software',
            lead='',
            epics=[],
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        epic_match = await context_aware_service._find_best_epic_match(
            task,
            context_without_epics
        )
        
        assert epic_match is None

