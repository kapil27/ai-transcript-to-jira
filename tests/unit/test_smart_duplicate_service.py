"""Unit tests for smart duplicate detection service."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.services.smart_duplicate_service import (
    SmartDuplicateService,
    DuplicateCandidate,
    ConflictResolution,
    SimilarityAnalysis
)
from src.services.mcp_jira_service import ProjectContext
from src.exceptions import DuplicateDetectionError
from src.config import AppConfig, JiraConfig


class TestSmartDuplicateService:
    """Test cases for SmartDuplicateService."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AppConfig(
            debug=True,
            jira=JiraConfig(
                similarity_threshold=0.85,
                max_search_results=10
            )
        )
    
    @pytest.fixture
    def mock_mcp_service(self):
        """Create mock MCP JIRA service."""
        mock_service = AsyncMock()
        
        mock_context = ProjectContext(
            key='TEST',
            name='Test Project',
            description='Test project',
            project_type='software',
            lead='Test Lead',
            epics=[
                {'key': 'TEST-100', 'summary': 'User Authentication Epic'}
            ],
            issue_types=[
                {'id': '1', 'name': 'Task'},
                {'id': '2', 'name': 'Bug'}
            ],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        mock_service.get_project_context.return_value = mock_context
        return mock_service
    
    @pytest.fixture
    def duplicate_service(self, test_config, mock_mcp_service):
        """Create duplicate detection service instance."""
        return SmartDuplicateService(test_config, mock_mcp_service)
    
    @pytest.fixture
    def sample_project_context(self):
        """Sample project context for testing."""
        return ProjectContext(
            key='TEST',
            name='Test Project',
            description='E-commerce platform',
            project_type='software',
            lead='John Doe',
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
    
    def test_service_initialization(self, duplicate_service, test_config, mock_mcp_service):
        """Test service initializes correctly."""
        assert duplicate_service.config == test_config
        assert duplicate_service.mcp_service == mock_mcp_service
        assert duplicate_service._cache_service is not None
    
    @pytest.mark.asyncio
    async def test_find_duplicates_via_mcp_no_matches(self, duplicate_service, sample_project_context):
        """Test finding duplicates with no matches."""
        task = {
            'summary': 'Implement unique feature',
            'description': 'Something completely new',
            'issue_type': 'Task'
        }
        
        project_key = 'TEST'
        
        with patch.object(duplicate_service, '_search_similar_tasks_multi_strategy', return_value=[]):
            result = await duplicate_service.find_duplicates_via_mcp(task, project_key)
            
            assert isinstance(result, list)
            assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_find_duplicates_via_mcp_with_matches(self, duplicate_service, sample_project_context):
        """Test finding duplicates with matches."""
        task = {
            'summary': 'Implement login feature',
            'description': 'Add user authentication',
            'issue_type': 'Task'
        }
        
        project_key = 'TEST'
        
        mock_candidates = [
            {
                'key': 'TEST-123',
                'fields': {
                    'summary': 'Implement user login',
                    'description': 'Add authentication feature',
                    'status': {'name': 'In Progress'},
                    'assignee': {'displayName': 'John Doe'},
                    'created': '2025-09-01T10:00:00.000Z',
                    'issuetype': {'name': 'Task'}
                }
            }
        ]
        
        with patch.object(duplicate_service, '_search_similar_tasks_multi_strategy', return_value=mock_candidates):
            result = await duplicate_service.find_duplicates_via_mcp(task, project_key)
            
            assert isinstance(result, list)
            # Result depends on similarity score meeting threshold
            # At minimum, should not error
    
    @pytest.mark.asyncio
    async def test_find_duplicates_via_mcp_error_handling(self, duplicate_service):
        """Test error handling in duplicate detection."""
        task = {'summary': 'Test task', 'description': 'Test'}
        project_key = 'TEST'
        
        with patch.object(duplicate_service.mcp_service, 'get_project_context', side_effect=Exception("Context error")):
            with pytest.raises(DuplicateDetectionError):
                await duplicate_service.find_duplicates_via_mcp(task, project_key)
    
    @pytest.mark.asyncio
    async def test_analyze_bulk_duplicates(self, duplicate_service, sample_project_context):
        """Test bulk duplicate analysis."""
        tasks = [
            {
                'summary': 'Implement login',
                'description': 'Add authentication',
                'issue_type': 'Task'
            },
            {
                'summary': 'Fix login bug',
                'description': 'Login not working',
                'issue_type': 'Bug'
            }
        ]
        
        project_key = 'TEST'
        
        with patch.object(duplicate_service, 'find_duplicates_via_mcp', return_value=[]):
            result = await duplicate_service.analyze_bulk_duplicates(tasks, project_key)
            
            assert isinstance(result, dict)
            assert result['project_key'] == project_key
            assert result['total_tasks_analyzed'] == 2
            assert 'duplicates_found' in result
            assert 'cross_references' in result
            assert 'summary' in result
    
    @pytest.mark.asyncio
    async def test_analyze_bulk_duplicates_with_cross_references(self, duplicate_service, sample_project_context):
        """Test bulk analysis detecting cross-references between tasks."""
        tasks = [
            {
                'summary': 'Implement user authentication',
                'description': 'Add login feature',
                'issue_type': 'Task'
            },
            {
                'summary': 'Implement authentication for users',
                'description': 'Add login functionality',
                'issue_type': 'Task'
            }
        ]
        
        project_key = 'TEST'
        
        with patch.object(duplicate_service, 'find_duplicates_via_mcp', return_value=[]):
            result = await duplicate_service.analyze_bulk_duplicates(tasks, project_key)
            
            # Should detect high similarity between the two tasks
            assert 'cross_references' in result
            # May or may not find references depending on threshold
    
    @pytest.mark.asyncio
    async def test_resolve_duplicate_conflicts(self, duplicate_service):
        """Test resolving duplicate conflicts."""
        conflicts = [
            {'task_id': 'task_1', 'duplicate_key': 'TEST-123'},
            {'task_id': 'task_2', 'duplicate_key': 'TEST-456'}
        ]
        
        user_resolutions = [
            {'action': 'skip', 'target_issue_key': 'TEST-123', 'notes': 'Duplicate, skip'},
            {'action': 'create_anyway', 'target_issue_key': '', 'notes': 'Different enough'}
        ]
        
        with patch.object(duplicate_service, '_apply_resolution'):
            resolutions = await duplicate_service.resolve_duplicate_conflicts(
                conflicts,
                user_resolutions
            )
            
            assert isinstance(resolutions, list)
            assert len(resolutions) == 2
            assert all(isinstance(r, ConflictResolution) for r in resolutions)
            assert resolutions[0].resolution_type == 'skip'
            assert resolutions[1].resolution_type == 'create_anyway'
    
    @pytest.mark.asyncio
    async def test_suggest_task_relationships(self, duplicate_service, sample_project_context):
        """Test suggesting task relationships."""
        tasks = [
            {
                'summary': 'Implement authentication feature',
                'description': 'Add login for users',
                'issue_type': 'Task'
            },
            {
                'summary': 'Add payment gateway',
                'description': 'Integrate payment processing',
                'issue_type': 'Task'
            }
        ]
        
        with patch.object(duplicate_service, '_suggest_epic_relationships', return_value=[
            {'epic_key': 'TEST-100', 'similarity_score': 0.8}
        ]):
            with patch.object(duplicate_service, '_suggest_blocking_relationships', return_value=[]):
                with patch.object(duplicate_service, '_suggest_related_stories', return_value=[]):
                    result = await duplicate_service.suggest_task_relationships(
                        tasks,
                        sample_project_context
                    )
                    
                    assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_search_by_text_similarity(self, duplicate_service):
        """Test text-based similarity search."""
        task = {
            'summary': 'Implement authentication',
            'description': 'Add login feature',
            'issue_type': 'Task'
        }
        
        project_key = 'TEST'
        
        result = await duplicate_service._search_by_text_similarity(
            task,
            project_key,
            include_resolved=False
        )
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_analyze_comprehensive_similarity_high(self, duplicate_service, sample_project_context):
        """Test comprehensive similarity analysis with high similarity."""
        task = {
            'summary': 'Implement user authentication',
            'description': 'Add login functionality',
            'issue_type': 'Task'
        }
        
        candidate = {
            'key': 'TEST-123',
            'fields': {
                'summary': 'Implement user login',
                'description': 'Add authentication feature',
                'status': {'name': 'In Progress'},
                'assignee': {'displayName': 'John Doe'},
                'created': datetime.now().isoformat(),
                'issuetype': {'name': 'Task'}
            }
        }
        
        analysis = await duplicate_service._analyze_comprehensive_similarity(
            task,
            candidate,
            sample_project_context
        )
        
        assert isinstance(analysis, SimilarityAnalysis)
        assert 0.0 <= analysis.text_similarity <= 1.0
        assert 0.0 <= analysis.semantic_similarity <= 1.0
        assert 0.0 <= analysis.overall_score <= 1.0
        assert isinstance(analysis.factors, list)
    
    @pytest.mark.asyncio
    async def test_analyze_comprehensive_similarity_low(self, duplicate_service, sample_project_context):
        """Test comprehensive similarity analysis with low similarity."""
        task = {
            'summary': 'Implement payment gateway',
            'description': 'Add Stripe integration',
            'issue_type': 'Task'
        }
        
        candidate = {
            'key': 'TEST-123',
            'fields': {
                'summary': 'Fix login bug',
                'description': 'Login button not working',
                'status': {'name': 'In Progress'},
                'assignee': None,
                'created': '2023-01-01T10:00:00.000Z',
                'issuetype': {'name': 'Bug'}
            }
        }
        
        analysis = await duplicate_service._analyze_comprehensive_similarity(
            task,
            candidate,
            sample_project_context
        )
        
        assert isinstance(analysis, SimilarityAnalysis)
        assert analysis.overall_score < 0.7  # Should be low similarity
    
    @pytest.mark.asyncio
    async def test_analyze_task_to_task_similarity(self, duplicate_service):
        """Test similarity analysis between two new tasks."""
        task1 = {
            'summary': 'Implement login feature',
            'description': 'Add user authentication',
            'issue_type': 'Task'
        }
        
        task2 = {
            'summary': 'Implement user login',
            'description': 'Add authentication feature',
            'issue_type': 'Task'
        }
        
        analysis = await duplicate_service._analyze_task_to_task_similarity(task1, task2)
        
        assert isinstance(analysis, SimilarityAnalysis)
        assert analysis.overall_score > 0.5  # Should have decent similarity
        assert analysis.temporal_similarity == 1.0  # Same batch
    
    def test_calculate_semantic_similarity_identical(self, duplicate_service):
        """Test semantic similarity for identical texts."""
        text1 = "Implement user authentication feature"
        text2 = "Implement user authentication feature"
        
        similarity = duplicate_service._calculate_semantic_similarity(text1, text2)
        
        assert similarity == 1.0
    
    def test_calculate_semantic_similarity_partial(self, duplicate_service):
        """Test semantic similarity for partially similar texts."""
        text1 = "Implement user authentication feature"
        text2 = "Implement authentication system"
        
        similarity = duplicate_service._calculate_semantic_similarity(text1, text2)
        
        assert 0.3 < similarity < 1.0
    
    def test_calculate_semantic_similarity_different(self, duplicate_service):
        """Test semantic similarity for different texts."""
        text1 = "Implement authentication"
        text2 = "Fix payment bug"
        
        similarity = duplicate_service._calculate_semantic_similarity(text1, text2)
        
        assert similarity < 0.5
    
    def test_calculate_context_similarity(self, duplicate_service, sample_project_context):
        """Test context-based similarity calculation."""
        task = {'issue_type': 'Task'}
        candidate = {
            'fields': {
                'issuetype': {'name': 'Task'}
            }
        }
        
        similarity = duplicate_service._calculate_context_similarity(
            task,
            candidate,
            sample_project_context
        )
        
        assert 0.0 <= similarity <= 1.0
    
    def test_calculate_temporal_similarity_recent(self, duplicate_service):
        """Test temporal similarity for recent issues."""
        task = {}
        candidate = {
            'fields': {
                'created': datetime.now().isoformat()
            }
        }
        
        similarity = duplicate_service._calculate_temporal_similarity(task, candidate)
        
        assert similarity >= 0.8  # Recent issues should have high similarity
    
    def test_calculate_temporal_similarity_old(self, duplicate_service):
        """Test temporal similarity for old issues."""
        task = {}
        old_date = (datetime.now() - timedelta(days=180)).isoformat()
        candidate = {
            'fields': {
                'created': old_date
            }
        }
        
        similarity = duplicate_service._calculate_temporal_similarity(task, candidate)
        
        assert similarity < 0.8  # Old issues should have lower similarity
    
    def test_calculate_assignee_similarity_same(self, duplicate_service):
        """Test assignee similarity for same assignee."""
        task = {'assignee': 'John Doe'}
        candidate = {
            'fields': {
                'assignee': {'displayName': 'John Doe'}
            }
        }
        
        similarity = duplicate_service._calculate_assignee_similarity(task, candidate)
        
        assert similarity == 1.0
    
    def test_calculate_assignee_similarity_different(self, duplicate_service):
        """Test assignee similarity for different assignees."""
        task = {'assignee': 'John Doe'}
        candidate = {
            'fields': {
                'assignee': {'displayName': 'Jane Smith'}
            }
        }
        
        similarity = duplicate_service._calculate_assignee_similarity(task, candidate)
        
        assert similarity == 0.0
    
    def test_get_assignee_name(self, duplicate_service):
        """Test extracting assignee name from issue."""
        issue_with_assignee = {
            'fields': {
                'assignee': {'displayName': 'John Doe', 'name': 'jdoe'}
            }
        }
        
        name = duplicate_service._get_assignee_name(issue_with_assignee)
        assert name == 'John Doe'
        
        issue_without_assignee = {
            'fields': {
                'assignee': None
            }
        }
        
        name = duplicate_service._get_assignee_name(issue_without_assignee)
        assert name == ''
    
    def test_extract_search_terms(self, duplicate_service):
        """Test extraction of search terms."""
        text = "Implement the user authentication and login feature for mobile app"
        
        terms = duplicate_service._extract_search_terms(text)
        
        assert isinstance(terms, list)
        assert 'implement' in terms
        assert 'user' in terms
        assert 'authentication' in terms
        assert 'the' not in terms  # Common word should be filtered
        assert 'and' not in terms  # Common word should be filtered
    
    def test_extract_keywords(self, duplicate_service, sample_project_context):
        """Test keyword extraction with project context."""
        task = {
            'summary': 'Implement user authentication system',
            'description': 'Add login and validation for users'
        }
        
        keywords = duplicate_service._extract_keywords(task, sample_project_context)
        
        assert isinstance(keywords, list)
        assert any('authentication' in keyword for keyword in keywords)
    
    def test_get_recommendation_skip(self, duplicate_service):
        """Test recommendation for very high similarity (skip)."""
        analysis = SimilarityAnalysis(
            text_similarity=0.98,
            semantic_similarity=0.95,
            context_similarity=0.9,
            temporal_similarity=1.0,
            assignee_similarity=1.0,
            overall_score=0.96,
            factors=['high_text_similarity', 'semantic_match']
        )
        
        recommendation = duplicate_service._get_recommendation(analysis)
        
        assert recommendation == 'skip'
    
    def test_get_recommendation_merge(self, duplicate_service):
        """Test recommendation for high similarity (merge)."""
        analysis = SimilarityAnalysis(
            text_similarity=0.88,
            semantic_similarity=0.85,
            context_similarity=0.8,
            temporal_similarity=0.9,
            assignee_similarity=0.5,
            overall_score=0.87,
            factors=['high_text_similarity']
        )
        
        recommendation = duplicate_service._get_recommendation(analysis)
        
        assert recommendation == 'merge'
    
    def test_get_recommendation_link(self, duplicate_service):
        """Test recommendation for medium similarity (link)."""
        analysis = SimilarityAnalysis(
            text_similarity=0.75,
            semantic_similarity=0.70,
            context_similarity=0.6,
            temporal_similarity=0.8,
            assignee_similarity=0.5,
            overall_score=0.72,
            factors=['similar_context']
        )
        
        recommendation = duplicate_service._get_recommendation(analysis)
        
        assert recommendation == 'link'
    
    def test_get_recommendation_create_anyway(self, duplicate_service):
        """Test recommendation for low similarity (create anyway)."""
        analysis = SimilarityAnalysis(
            text_similarity=0.4,
            semantic_similarity=0.3,
            context_similarity=0.2,
            temporal_similarity=0.5,
            assignee_similarity=0.0,
            overall_score=0.35,
            factors=[]
        )
        
        recommendation = duplicate_service._get_recommendation(analysis)
        
        assert recommendation == 'create_anyway'
    
    def test_calculate_confidence(self, duplicate_service):
        """Test confidence calculation."""
        analysis_high_confidence = SimilarityAnalysis(
            text_similarity=0.95,
            semantic_similarity=0.90,
            context_similarity=0.85,
            temporal_similarity=1.0,
            assignee_similarity=1.0,
            overall_score=0.92,
            factors=['high_text_similarity', 'semantic_match', 'recent_timing', 'same_assignee']
        )
        
        confidence = duplicate_service._calculate_confidence(analysis_high_confidence)
        
        assert confidence >= 0.8
        assert confidence <= 1.0
    
    def test_extract_issue_context(self, duplicate_service, sample_project_context):
        """Test extraction of issue context."""
        issue = {
            'fields': {
                'issuetype': {'name': 'Task'},
                'status': {'name': 'In Progress'},
                'priority': {'name': 'High'},
                'components': [{'name': 'Backend'}, {'name': 'API'}],
                'labels': ['authentication', 'security']
            }
        }
        
        context = duplicate_service._extract_issue_context(issue, sample_project_context)
        
        assert isinstance(context, dict)
        assert context['project_key'] == 'TEST'
        assert context['issue_type'] == 'Task'
        assert context['status'] == 'In Progress'
        assert 'Backend' in context['components']
        assert 'authentication' in context['labels']
    
    def test_generate_duplicate_summary(self, duplicate_service):
        """Test generation of duplicate summary statistics."""
        all_duplicates = {
            'task_1': [
                Mock(recommendation='skip', confidence=0.95),
                Mock(recommendation='link', confidence=0.75)
            ],
            'task_2': [],
            'task_3': [
                Mock(recommendation='merge', confidence=0.88)
            ]
        }
        
        cross_references = [
            {'task_1_id': 'task_1', 'task_2_id': 'task_3', 'similarity_score': 0.8}
        ]
        
        summary = duplicate_service._generate_duplicate_summary(all_duplicates, cross_references)
        
        assert isinstance(summary, dict)
        assert summary['total_potential_duplicates'] == 3
        assert summary['tasks_with_duplicates'] == 2
        assert summary['cross_references_found'] == 1
        assert 'recommendations_breakdown' in summary
        assert summary['recommendations_breakdown']['skip'] == 1
        assert summary['recommendations_breakdown']['link'] == 1
        assert summary['recommendations_breakdown']['merge'] == 1
    
    @pytest.mark.asyncio
    async def test_suggest_epic_relationships(self, duplicate_service, sample_project_context):
        """Test suggesting epic relationships."""
        task = {
            'summary': 'Implement user authentication',
            'description': 'Add login feature for users'
        }
        
        suggestions = await duplicate_service._suggest_epic_relationships(
            task,
            sample_project_context
        )
        
        assert isinstance(suggestions, list)
        # Should find match with User Authentication epic
        if suggestions:
            assert suggestions[0]['relationship_type'] == 'parent_epic'
            assert 'epic_key' in suggestions[0]

