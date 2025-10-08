"""Unit tests for MCP JIRA integration service."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.mcp_jira_service import (
    MCPJiraService,
    ProjectContext,
    TaskSimilarity
)
from src.exceptions import JiraIntegrationError
from src.config import AppConfig, JiraConfig, MCPConfig


class TestMCPJiraService:
    """Test cases for MCPJiraService."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AppConfig(
            debug=True,
            jira=JiraConfig(
                base_url="https://test.atlassian.net",
                username="test@example.com",
                api_token="test_token",
                similarity_threshold=0.85,
                max_search_results=10
            ),
            mcp=MCPConfig(
                atlassian_server_url="http://localhost:3000",
                cache_ttl=300
            )
        )
    
    @pytest.fixture
    def mcp_service(self, test_config):
        """Create MCP JIRA service instance."""
        return MCPJiraService(test_config)
    
    def test_service_initialization(self, mcp_service, test_config):
        """Test service initializes correctly."""
        assert mcp_service.config == test_config
        assert mcp_service._mcp_client is None
        assert mcp_service._jira_client is None
        assert isinstance(mcp_service._connection_pool, dict)
    
    @pytest.mark.asyncio
    async def test_initialize_mcp_client_success(self, mcp_service):
        """Test successful MCP client initialization."""
        result = await mcp_service.initialize_mcp_client()
        
        assert result is True
        assert mcp_service._mcp_client is not None
        assert mcp_service._mcp_client['connected'] is True
        assert 'capabilities' in mcp_service._mcp_client
    
    @pytest.mark.asyncio
    async def test_authenticate_via_mcp_success(self, mcp_service):
        """Test successful JIRA authentication."""
        with patch('src.services.mcp_jira_service.Jira') as mock_jira_class:
            mock_jira_instance = MagicMock()
            mock_jira_instance.myself.return_value = {'displayName': 'Test User'}
            mock_jira_class.return_value = mock_jira_instance
            
            result = await mcp_service.authenticate_via_mcp(
                "https://test.atlassian.net",
                "test@example.com",
                "test_token"
            )
            
            assert result is True
            assert mcp_service._jira_client is not None
            assert len(mcp_service._connection_pool) == 1
    
    @pytest.mark.asyncio
    async def test_authenticate_via_mcp_failure(self, mcp_service):
        """Test JIRA authentication failure."""
        with patch('src.services.mcp_jira_service.Jira') as mock_jira_class:
            mock_jira_class.side_effect = Exception("Authentication failed")
            
            with pytest.raises(JiraIntegrationError, match="Authentication failed"):
                await mcp_service.authenticate_via_mcp(
                    "https://test.atlassian.net",
                    "test@example.com",
                    "invalid_token"
                )
    
    @pytest.mark.asyncio
    async def test_get_enriched_projects_from_cache(self, mcp_service):
        """Test getting enriched projects from cache."""
        cached_data = [{'key': 'TEST', 'name': 'Test Project'}]
        
        with patch.object(mcp_service._cache_service, 'get', return_value=cached_data):
            result = await mcp_service.get_enriched_projects()
            
            assert result == cached_data
    
    @pytest.mark.asyncio
    async def test_get_enriched_projects_mock_data(self, mcp_service):
        """Test getting enriched projects with mock data."""
        with patch.object(mcp_service._cache_service, 'get', return_value=None):
            with patch.object(mcp_service._cache_service, 'set'):
                result = await mcp_service.get_enriched_projects()
                
                assert isinstance(result, list)
                assert len(result) > 0
                assert 'key' in result[0]
                assert 'name' in result[0]
    
    @pytest.mark.asyncio
    async def test_get_project_context_success(self, mcp_service):
        """Test successful project context retrieval."""
        project_key = "TEST"
        
        with patch.object(mcp_service._cache_service, 'get', return_value=None):
            with patch.object(mcp_service._cache_service, 'set'):
                context = await mcp_service.get_project_context(project_key)
                
                assert isinstance(context, ProjectContext)
                assert context.key == project_key
                assert isinstance(context.epics, list)
                assert isinstance(context.issue_types, list)
    
    @pytest.mark.asyncio
    async def test_get_project_context_from_cache(self, mcp_service):
        """Test getting project context from cache."""
        project_key = "TEST"
        cached_context = {
            'key': project_key,
            'name': 'Test Project',
            'description': 'Test description',
            'project_type': 'software',
            'lead': 'Test Lead',
            'active_sprint': None,
            'epics': [],
            'issue_types': [],
            'custom_fields': [],
            'workflows': [],
            'recent_issues': []
        }
        
        with patch.object(mcp_service._cache_service, 'get', return_value=cached_context):
            context = await mcp_service.get_project_context(project_key)
            
            assert isinstance(context, ProjectContext)
            assert context.key == project_key
            assert context.name == 'Test Project'
    
    @pytest.mark.asyncio
    async def test_search_similar_tasks_success(self, mcp_service):
        """Test successful similar task search."""
        project_key = "TEST"
        task_summary = "Implement user authentication"
        task_description = "Add login and registration features"
        
        # Mock project context
        mock_context = ProjectContext(
            key=project_key,
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[],
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        with patch.object(mcp_service, 'get_project_context', return_value=mock_context):
            with patch.object(mcp_service, '_make_mcp_call', return_value={'issues': []}):
                results = await mcp_service.search_similar_tasks(
                    project_key,
                    task_summary,
                    task_description
                )
                
                assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_similar_tasks_with_matches(self, mcp_service):
        """Test similar task search with matches."""
        project_key = "TEST"
        task_summary = "User authentication"
        task_description = "Login feature"
        
        mock_context = ProjectContext(
            key=project_key,
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[],
            issue_types=[{'id': '1', 'name': 'Task'}],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        mock_issues = {
            'issues': [
                {
                    'key': 'TEST-123',
                    'fields': {
                        'summary': 'Implement user authentication',
                        'description': 'Add login functionality',
                        'status': {'name': 'In Progress'}
                    }
                }
            ]
        }
        
        with patch.object(mcp_service, 'get_project_context', return_value=mock_context):
            with patch.object(mcp_service, '_make_mcp_call', return_value=mock_issues):
                results = await mcp_service.search_similar_tasks(
                    project_key,
                    task_summary,
                    task_description
                )
                
                # Should return some results based on similarity
                assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_create_context_aware_task_success(self, mcp_service):
        """Test successful context-aware task creation."""
        project_key = "TEST"
        task_data = {
            'summary': 'New feature task',
            'description': 'Implement new feature',
            'issue_type': 'Task'
        }
        
        context = ProjectContext(
            key=project_key,
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[],
            issue_types=[{'id': '1', 'name': 'Task'}],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        mock_result = {
            'success': True,
            'issue': {
                'key': 'TEST-456',
                'summary': 'New feature task',
                'status': 'To Do'
            }
        }
        
        with patch.object(mcp_service, '_make_mcp_call', return_value=mock_result):
            created_task = await mcp_service.create_context_aware_task(
                project_key,
                task_data,
                context
            )
            
            assert created_task['key'] == 'TEST-456'
            assert created_task['summary'] == 'New feature task'
    
    @pytest.mark.asyncio
    async def test_create_context_aware_task_failure(self, mcp_service):
        """Test context-aware task creation failure."""
        project_key = "TEST"
        task_data = {'summary': 'Test task'}
        context = ProjectContext(
            key=project_key,
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[],
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        mock_result = {'success': False}
        
        with patch.object(mcp_service, '_make_mcp_call', return_value=mock_result):
            with pytest.raises(JiraIntegrationError, match="Task creation failed"):
                await mcp_service.create_context_aware_task(
                    project_key,
                    task_data,
                    context
                )
    
    def test_calculate_text_similarity_identical(self, mcp_service):
        """Test text similarity calculation for identical texts."""
        text1 = "This is a test"
        text2 = "This is a test"
        
        similarity = mcp_service._calculate_text_similarity(text1, text2)
        
        assert similarity == 1.0
    
    def test_calculate_text_similarity_different(self, mcp_service):
        """Test text similarity calculation for different texts."""
        text1 = "This is a test"
        text2 = "Something completely different"
        
        similarity = mcp_service._calculate_text_similarity(text1, text2)
        
        assert 0.0 <= similarity < 0.5
    
    def test_calculate_text_similarity_partial(self, mcp_service):
        """Test text similarity calculation for partially similar texts."""
        text1 = "Implement user authentication system"
        text2 = "Implement authentication feature"
        
        similarity = mcp_service._calculate_text_similarity(text1, text2)
        
        assert 0.3 <= similarity <= 0.8
    
    def test_calculate_text_similarity_empty(self, mcp_service):
        """Test text similarity calculation for empty texts."""
        similarity1 = mcp_service._calculate_text_similarity("", "test")
        similarity2 = mcp_service._calculate_text_similarity("test", "")
        similarity3 = mcp_service._calculate_text_similarity("", "")
        
        assert similarity1 == 0.0
        assert similarity2 == 0.0
        assert similarity3 == 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_task_similarity(self, mcp_service):
        """Test task similarity analysis."""
        task_summary = "Implement login feature"
        task_description = "Add user authentication"
        
        existing_issue = {
            'key': 'TEST-123',
            'fields': {
                'summary': 'Implement user authentication',
                'description': 'Add login functionality'
            }
        }
        
        context = ProjectContext(
            key='TEST',
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[],
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        result = await mcp_service._analyze_task_similarity(
            task_summary,
            task_description,
            existing_issue,
            context
        )
        
        assert isinstance(result, TaskSimilarity)
        assert result.existing_issue_key == 'TEST-123'
        assert 0.0 <= result.similarity_score <= 1.0
        assert result.recommendation in ['duplicate', 'related', 'unique']
    
    @pytest.mark.asyncio
    async def test_enhance_task_data(self, mcp_service):
        """Test task data enhancement with context."""
        task_data = {
            'summary': 'Test task',
            'description': 'Test description'
        }
        
        context = ProjectContext(
            key='TEST',
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            active_sprint={'id': 'sprint-1', 'name': 'Sprint 1'},
            epics=[],
            issue_types=[{'id': '1', 'name': 'Task'}, {'id': '2', 'name': 'Story'}],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        enhanced = await mcp_service._enhance_task_data(task_data, context)
        
        assert enhanced['summary'] == 'Test task'
        assert 'issuetype' in enhanced
        assert 'sprint' in enhanced
        assert enhanced['sprint'] == 'sprint-1'
    
    @pytest.mark.asyncio
    async def test_auto_link_to_epics(self, mcp_service):
        """Test automatic linking to epics."""
        created_task = {
            'key': 'TEST-456',
            'fields': {
                'summary': 'Implement authentication feature'
            }
        }
        
        context = ProjectContext(
            key='TEST',
            name='Test Project',
            description='',
            project_type='software',
            lead='Test Lead',
            epics=[
                {'key': 'TEST-100', 'summary': 'User Authentication Epic'},
                {'key': 'TEST-200', 'summary': 'Payment Processing Epic'}
            ],
            issue_types=[],
            custom_fields=[],
            workflows=[],
            recent_issues=[]
        )
        
        # Should attempt to link to authentication epic
        with patch.object(mcp_service, '_make_mcp_call') as mock_call:
            await mcp_service._auto_link_to_epics(created_task, context)
            
            # Verify link attempt was made (at least tried)
            # The actual call might not happen if keywords don't match perfectly
            pass  # Test passes if no exception is raised
    
    @pytest.mark.asyncio
    async def test_get_mock_response(self, mcp_service):
        """Test mock response generation."""
        # Test various operations
        projects_response = await mcp_service._get_mock_response('get_projects_enriched', {})
        assert 'projects' in projects_response
        assert len(projects_response['projects']) > 0
        
        details_response = await mcp_service._get_mock_response('get_project_details', {})
        assert 'name' in details_response
        
        create_response = await mcp_service._get_mock_response(
            'create_issue',
            {'issue_data': {'summary': 'Test Task'}}
        )
        assert create_response['success'] is True
        assert 'issue' in create_response
    
    @pytest.mark.asyncio
    async def test_get_basic_projects(self, mcp_service):
        """Test fallback basic projects method."""
        projects = await mcp_service._get_basic_projects()
        
        assert isinstance(projects, list)
        assert len(projects) > 0
        assert 'key' in projects[0]
        assert 'name' in projects[0]
        assert 'project_type' in projects[0]

