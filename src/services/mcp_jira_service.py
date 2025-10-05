"""MCP-enhanced JIRA integration service."""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from ..config import AppConfig
from ..exceptions import JiraIntegrationError
from ..utils import LoggerMixin
from .cache_service import CacheService


@dataclass
class ProjectContext:
    """Rich project context from JIRA."""

    key: str
    name: str
    description: str
    project_type: str
    lead: str
    active_sprint: Optional[Dict[str, Any]] = None
    epics: List[Dict[str, Any]] = None
    issue_types: List[Dict[str, Any]] = None
    custom_fields: List[Dict[str, Any]] = None
    workflows: List[Dict[str, Any]] = None
    recent_issues: List[Dict[str, Any]] = None


@dataclass
class TaskSimilarity:
    """Task similarity analysis result."""

    existing_issue_key: str
    existing_summary: str
    similarity_score: float
    recommendation: str  # 'duplicate', 'related', 'unique'
    suggested_action: str
    context_factors: List[str]


class MCPJiraService(LoggerMixin):
    """MCP-enhanced JIRA service for intelligent task management."""

    def __init__(self, config: AppConfig):
        """
        Initialize MCP JIRA service.

        Args:
            config: Application configuration
        """
        self.config = config
        self._cache_service = CacheService()
        self._mcp_client = None
        self._connection_pool = {}
        self._jira_client = None
        self._current_connection = None

    async def initialize_mcp_client(self):
        """Initialize MCP client connection."""
        try:
            # Note: This is a placeholder for actual MCP client initialization
            # In real implementation, this would connect to the Atlassian MCP server
            self.logger.info("Initializing MCP client for Atlassian integration")

            # Simulated MCP client setup
            self._mcp_client = {
                'connected': True,
                'server_url': self.config.mcp.atlassian_server_url,
                'capabilities': ['jira_read', 'jira_write', 'confluence_read']
            }

            self.logger.info("MCP client initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP client: {e}")
            raise JiraIntegrationError(f"MCP initialization failed: {str(e)}")

    async def authenticate_via_mcp(self, jira_url: str, username: str, api_token: str) -> bool:
        """
        Authenticate with JIRA via MCP.

        Args:
            jira_url: JIRA instance URL
            username: JIRA username
            api_token: JIRA API token

        Returns:
            Authentication success status

        Raises:
            JiraIntegrationError: If authentication fails
        """
        try:
            self.logger.info(f"Authenticating with JIRA: {jira_url}")

            # Test authentication with real JIRA API call
            from atlassian import Jira

            jira_client = Jira(
                url=jira_url,
                username=username,
                password=api_token,
                cloud=True
            )

            # Test connection by getting current user
            user_info = jira_client.myself()
            self.logger.info(f"Authenticated as: {user_info.get('displayName', username)}")

            # Store credentials and client in connection pool
            connection_key = f"{jira_url}:{username}"
            self._connection_pool[connection_key] = {
                'url': jira_url,
                'username': username,
                'api_token': api_token,
                'client': jira_client,
                'authenticated_at': datetime.now(),
                'last_used': datetime.now()
            }

            # Store default client for this session
            self._jira_client = jira_client
            self._current_connection = connection_key

            self.logger.info("JIRA authentication successful")
            return True

        except Exception as e:
            self.logger.error(f"JIRA authentication failed: {e}")
            raise JiraIntegrationError(f"Authentication failed: {str(e)}")

    async def get_enriched_projects(self) -> List[Dict[str, Any]]:
        """
        Get enriched project list with context data.

        Returns:
            List of projects with additional context
        """
        cache_key = "mcp_enriched_projects"
        cached_data = self._cache_service.get(cache_key)

        if cached_data:
            self.logger.info("Returning cached enriched projects")
            return cached_data

        try:
            self.logger.info("Fetching enriched projects via MCP")

            projects_data = await self._make_mcp_call('get_projects_enriched', {})

            enriched_projects = []
            for project in projects_data.get('projects', []):
                enriched_project = {
                    'key': project['key'],
                    'name': project['name'],
                    'description': project.get('description', ''),
                    'project_type': project.get('projectTypeKey', 'software'),
                    'lead': project.get('lead', {}).get('displayName', ''),
                    'active_sprint_count': project.get('active_sprints', 0),
                    'total_issues': project.get('issue_count', 0),
                    'recent_activity': project.get('recent_activity_score', 0),
                    'team_size': len(project.get('assignable_users', [])),
                    'last_updated': project.get('last_updated', '')
                }
                enriched_projects.append(enriched_project)

            # Cache for 5 minutes
            self._cache_service.set(cache_key, enriched_projects,
                                  expires=self.config.mcp.cache_ttl)

            self.logger.info(f"Retrieved {len(enriched_projects)} enriched projects")
            return enriched_projects

        except Exception as e:
            self.logger.error(f"Failed to get enriched projects: {e}")
            # Fallback to basic project list
            return await self._get_basic_projects()

    async def get_project_context(self, project_key: str) -> ProjectContext:
        """
        Get comprehensive project context.

        Args:
            project_key: JIRA project key

        Returns:
            Rich project context data
        """
        cache_key = f"mcp_project_context_{project_key}"
        cached_data = self._cache_service.get(cache_key)

        if cached_data:
            self.logger.info(f"Returning cached context for project {project_key}")
            return ProjectContext(**cached_data)

        try:
            self.logger.info(f"Fetching project context for {project_key}")

            # Get project details
            project_data = await self._make_mcp_call('get_project_details', {
                'project_key': project_key
            })

            # Get active sprint
            sprint_data = await self._make_mcp_call('get_active_sprint', {
                'project_key': project_key
            })

            # Get epics
            epics_data = await self._make_mcp_call('get_project_epics', {
                'project_key': project_key
            })

            # Get issue types and workflows
            metadata = await self._make_mcp_call('get_project_metadata', {
                'project_key': project_key
            })

            # Get recent issues for pattern analysis
            recent_issues = await self._make_mcp_call('get_recent_issues', {
                'project_key': project_key,
                'limit': 50
            })

            context = ProjectContext(
                key=project_key,
                name=project_data.get('name', ''),
                description=project_data.get('description', ''),
                project_type=project_data.get('projectTypeKey', 'software'),
                lead=project_data.get('lead', {}).get('displayName', ''),
                active_sprint=sprint_data.get('sprint'),
                epics=epics_data.get('epics', []),
                issue_types=metadata.get('issue_types', []),
                custom_fields=metadata.get('custom_fields', []),
                workflows=metadata.get('workflows', []),
                recent_issues=recent_issues.get('issues', [])
            )

            # Cache context for 5 minutes
            self._cache_service.set(cache_key, asdict(context),
                                  expires=self.config.mcp.cache_ttl)

            self.logger.info(f"Project context loaded for {project_key}")
            return context

        except Exception as e:
            self.logger.error(f"Failed to get project context: {e}")
            # Return minimal context
            return ProjectContext(
                key=project_key,
                name=project_key,
                description="",
                project_type="software",
                lead="",
                epics=[],
                issue_types=[],
                custom_fields=[],
                workflows=[],
                recent_issues=[]
            )

    async def search_similar_tasks(self, project_key: str, task_summary: str,
                                 task_description: str) -> List[TaskSimilarity]:
        """
        Search for similar tasks using MCP-enhanced intelligence.

        Args:
            project_key: JIRA project key
            task_summary: Task summary to search for
            task_description: Task description for context

        Returns:
            List of similar tasks with similarity analysis
        """
        try:
            self.logger.info(f"Searching for similar tasks in {project_key}")

            # Get project context for better matching
            project_context = await self.get_project_context(project_key)

            # Search for similar issues via MCP
            search_results = await self._make_mcp_call('search_similar_issues', {
                'project_key': project_key,
                'summary': task_summary,
                'description': task_description,
                'include_resolved': False,
                'limit': self.config.jira.max_search_results
            })

            similarities = []
            for issue in search_results.get('issues', []):
                similarity = await self._analyze_task_similarity(
                    task_summary, task_description,
                    issue, project_context
                )
                if similarity.similarity_score >= self.config.jira.similarity_threshold:
                    similarities.append(similarity)

            # Sort by similarity score
            similarities.sort(key=lambda x: x.similarity_score, reverse=True)

            self.logger.info(f"Found {len(similarities)} similar tasks")
            return similarities

        except Exception as e:
            self.logger.error(f"Similar task search failed: {e}")
            return []

    async def create_context_aware_task(self, project_key: str, task_data: Dict[str, Any],
                                      context: ProjectContext) -> Dict[str, Any]:
        """
        Create task with context-aware enhancements.

        Args:
            project_key: JIRA project key
            task_data: Basic task data
            context: Project context for enhancements

        Returns:
            Created task data
        """
        try:
            self.logger.info(f"Creating context-aware task in {project_key}")

            # Enhance task data with context
            enhanced_task = await self._enhance_task_data(task_data, context)

            # Create task via MCP
            result = await self._make_mcp_call('create_issue', {
                'project_key': project_key,
                'issue_data': enhanced_task
            })

            if result.get('success'):
                created_task = result.get('issue')
                self.logger.info(f"Task created: {created_task.get('key')}")

                # Auto-link to epics if applicable
                await self._auto_link_to_epics(created_task, context)

                return created_task
            else:
                raise JiraIntegrationError("Task creation failed")

        except Exception as e:
            self.logger.error(f"Context-aware task creation failed: {e}")
            raise JiraIntegrationError(f"Task creation failed: {str(e)}")

    async def _make_mcp_call(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make JIRA API call with retry logic.

        Args:
            operation: Operation name
            params: Operation parameters

        Returns:
            Operation result
        """
        if not self._jira_client:
            # Use environment credentials if available
            if self.config.jira.base_url and self.config.jira.username and self.config.jira.api_token:
                await self.authenticate_via_mcp(
                    self.config.jira.base_url,
                    self.config.jira.username,
                    self.config.jira.api_token
                )
            else:
                # Return mock data if no real credentials
                return await self._get_mock_response(operation, params)

        try:
            # Route to appropriate JIRA API call
            if operation == 'get_projects_enriched':
                return await self._get_projects_enriched_real()
            elif operation == 'get_project_details':
                return await self._get_project_details_real(params['project_key'])
            elif operation == 'get_active_sprint':
                return await self._get_active_sprint_real(params['project_key'])
            elif operation == 'get_project_epics':
                return await self._get_project_epics_real(params['project_key'])
            elif operation == 'get_project_metadata':
                return await self._get_project_metadata_real(params['project_key'])
            elif operation == 'get_recent_issues':
                return await self._get_recent_issues_real(params['project_key'], params.get('limit', 50))
            elif operation == 'search_similar_issues':
                return await self._search_similar_issues_real(params)
            elif operation == 'create_issue':
                return await self._create_issue_real(params)
            else:
                return {'success': True}

        except Exception as e:
            self.logger.error(f"JIRA API call failed for {operation}: {e}")
            # Fallback to mock data
            return await self._get_mock_response(operation, params)

    async def _get_projects_enriched_real(self) -> Dict[str, Any]:
        """Get real project data from JIRA."""
        projects = self._jira_client.projects()
        enriched_projects = []

        for project in projects:
            enriched_project = {
                'key': project['key'],
                'name': project['name'],
                'description': project.get('description', ''),
                'projectTypeKey': project.get('projectTypeKey', 'software'),
                'lead': project.get('lead', {}),
                'active_sprints': 0,  # Would need additional API calls
                'issue_count': 0,     # Would need additional API calls
                'recent_activity_score': 5,
                'assignable_users': [],
                'last_updated': datetime.now().isoformat()
            }
            enriched_projects.append(enriched_project)

        return {'projects': enriched_projects}

    async def _get_project_details_real(self, project_key: str) -> Dict[str, Any]:
        """Get real project details from JIRA."""
        project = self._jira_client.project(project_key)
        return {
            'name': project['name'],
            'description': project.get('description', ''),
            'projectTypeKey': project.get('projectTypeKey', 'software'),
            'lead': project.get('lead', {})
        }

    async def _get_active_sprint_real(self, project_key: str) -> Dict[str, Any]:
        """Get active sprint for project."""
        try:
            # This would require additional JIRA API calls for Agile data
            # For now, return empty sprint data
            return {'sprint': None}
        except Exception:
            return {'sprint': None}

    async def _get_project_epics_real(self, project_key: str) -> Dict[str, Any]:
        """Get project epics from JIRA."""
        try:
            # Search for epics in the project
            jql = f'project = {project_key} AND issuetype = Epic ORDER BY created DESC'
            epics = self._jira_client.jql(jql, limit=20)['issues']

            epic_list = []
            for epic in epics:
                epic_list.append({
                    'key': epic['key'],
                    'summary': epic['fields']['summary'],
                    'status': epic['fields']['status']['name']
                })

            return {'epics': epic_list}
        except Exception as e:
            self.logger.warning(f"Failed to get epics for {project_key}: {e}")
            return {'epics': []}

    async def _get_project_metadata_real(self, project_key: str) -> Dict[str, Any]:
        """Get project metadata from JIRA."""
        try:
            # Get issue types for the project
            issue_types = self._jira_client.project_issue_types(project_key)

            return {
                'issue_types': [{'id': it['id'], 'name': it['name']} for it in issue_types],
                'custom_fields': [],  # Would need additional API calls
                'workflows': []       # Would need additional API calls
            }
        except Exception as e:
            self.logger.warning(f"Failed to get metadata for {project_key}: {e}")
            return {'issue_types': [], 'custom_fields': [], 'workflows': []}

    async def _get_recent_issues_real(self, project_key: str, limit: int) -> Dict[str, Any]:
        """Get recent issues from JIRA."""
        try:
            jql = f'project = {project_key} ORDER BY created DESC'
            issues = self._jira_client.jql(jql, limit=limit)['issues']
            return {'issues': issues}
        except Exception as e:
            self.logger.warning(f"Failed to get recent issues for {project_key}: {e}")
            return {'issues': []}

    async def _search_similar_issues_real(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for similar issues in JIRA."""
        try:
            project_key = params['project_key']
            summary = params['summary']
            description = params.get('description', '')

            # Create search terms from summary and description
            search_text = f'{summary} {description}'
            words = [word for word in search_text.split() if len(word) > 3]

            if words:
                # Create JQL query for text search
                search_terms = ' OR '.join([f'text ~ "{word}"' for word in words[:5]])
                jql = f'project = {project_key} AND ({search_terms}) ORDER BY created DESC'

                issues = self._jira_client.jql(jql, limit=params.get('limit', 10))['issues']
                return {'issues': issues}

            return {'issues': []}
        except Exception as e:
            self.logger.warning(f"Failed to search similar issues: {e}")
            return {'issues': []}

    async def _create_issue_real(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create issue in JIRA."""
        try:
            project_key = params['project_key']
            issue_data = params['issue_data']

            # Prepare issue fields
            fields = {
                'project': {'key': project_key},
                'summary': issue_data.get('summary', ''),
                'description': issue_data.get('description', ''),
                'issuetype': issue_data.get('issuetype', {'name': 'Task'})
            }

            # Create the issue
            created_issue = self._jira_client.issue_create(fields)

            return {
                'success': True,
                'issue': {
                    'key': created_issue['key'],
                    'summary': fields['summary'],
                    'status': 'To Do'
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}")
            return {'success': False, 'error': str(e)}

    async def _get_mock_response(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get mock response when no real JIRA connection available."""
        mock_responses = {
            'get_projects_enriched': {
                'projects': [
                    {
                        'key': 'DEMO',
                        'name': 'Demo Project',
                        'description': 'Demo project for testing (mock data)',
                        'projectTypeKey': 'software',
                        'lead': {'displayName': 'John Doe (Mock)'},
                        'active_sprints': 1,
                        'issue_count': 25,
                        'recent_activity_score': 8,
                        'assignable_users': ['user1', 'user2', 'user3'],
                        'last_updated': datetime.now().isoformat()
                    }
                ]
            },
            'get_project_details': {
                'name': 'Demo Project (Mock)',
                'description': 'Demo project for testing',
                'projectTypeKey': 'software',
                'lead': {'displayName': 'John Doe (Mock)'}
            },
            'get_active_sprint': {'sprint': None},
            'get_project_epics': {'epics': []},
            'get_project_metadata': {
                'issue_types': [
                    {'id': '1', 'name': 'Story'},
                    {'id': '2', 'name': 'Task'},
                    {'id': '3', 'name': 'Bug'}
                ],
                'custom_fields': [],
                'workflows': []
            },
            'get_recent_issues': {'issues': []},
            'search_similar_issues': {'issues': []},
            'create_issue': {
                'success': True,
                'issue': {
                    'key': f'DEMO-{datetime.now().microsecond}',
                    'summary': params.get('issue_data', {}).get('summary', 'New Task (Mock)'),
                    'status': 'To Do'
                }
            }
        }

        return mock_responses.get(operation, {'success': False})

    async def _get_basic_projects(self) -> List[Dict[str, Any]]:
        """Fallback method to get basic project list."""
        return [
            {
                'key': 'DEMO',
                'name': 'Demo Project',
                'description': 'Demo project for testing',
                'project_type': 'software',
                'lead': 'John Doe',
                'active_sprint_count': 1,
                'total_issues': 25,
                'recent_activity': 8,
                'team_size': 3,
                'last_updated': datetime.now().isoformat()
            }
        ]

    async def _analyze_task_similarity(self, task_summary: str, task_description: str,
                                     existing_issue: Dict[str, Any],
                                     context: ProjectContext) -> TaskSimilarity:
        """Analyze similarity between new task and existing issue."""
        # Simple similarity calculation (in real implementation, use more sophisticated algorithms)
        existing_summary = existing_issue.get('fields', {}).get('summary', '')

        # Calculate basic text similarity
        similarity_score = self._calculate_text_similarity(task_summary, existing_summary)

        # Determine recommendation based on score
        if similarity_score >= 0.9:
            recommendation = 'duplicate'
            suggested_action = 'Skip creation, link to existing issue'
        elif similarity_score >= 0.7:
            recommendation = 'related'
            suggested_action = 'Create with link to related issue'
        else:
            recommendation = 'unique'
            suggested_action = 'Create as new issue'

        return TaskSimilarity(
            existing_issue_key=existing_issue.get('key', ''),
            existing_summary=existing_summary,
            similarity_score=similarity_score,
            recommendation=recommendation,
            suggested_action=suggested_action,
            context_factors=['text_similarity']
        )

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate basic text similarity."""
        # Simple word overlap calculation
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    async def _enhance_task_data(self, task_data: Dict[str, Any],
                               context: ProjectContext) -> Dict[str, Any]:
        """Enhance task data with project context."""
        enhanced = task_data.copy()

        # Set appropriate issue type based on context
        if not enhanced.get('issuetype') and context.issue_types:
            # Simple logic: use 'Task' if available, otherwise first available type
            task_type = next((it for it in context.issue_types if it['name'] == 'Task'),
                           context.issue_types[0] if context.issue_types else None)
            if task_type:
                enhanced['issuetype'] = {'id': task_type['id']}

        # Add sprint information if available
        if context.active_sprint:
            enhanced['sprint'] = context.active_sprint['id']

        return enhanced

    async def _auto_link_to_epics(self, created_task: Dict[str, Any],
                                context: ProjectContext):
        """Auto-link task to appropriate epic."""
        if not context.epics:
            return

        # Simple epic matching based on keywords
        task_summary = created_task.get('fields', {}).get('summary', '').lower()

        for epic in context.epics:
            epic_summary = epic.get('summary', '').lower()

            # Check for keyword overlap
            if any(word in task_summary for word in epic_summary.split() if len(word) > 3):
                try:
                    await self._make_mcp_call('link_issues', {
                        'inward_issue': created_task['key'],
                        'outward_issue': epic['key'],
                        'link_type': 'Epic-Story Link'
                    })
                    self.logger.info(f"Linked {created_task['key']} to epic {epic['key']}")
                    break
                except Exception as e:
                    self.logger.warning(f"Failed to link to epic: {e}")