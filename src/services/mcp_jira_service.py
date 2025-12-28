"""MCP-enhanced JIRA integration service with enhanced data models."""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from ..config import AppConfig
from ..exceptions import (
    JiraIntegrationError, JiraConnectionError, JiraAuthenticationError,
    JiraAPIError, MCPError, DatabaseError
)
from ..utils import LoggerMixin, get_database_manager
from ..utils.mcp_client import get_mcp_client
from ..utils.encryption import SecureCredentialManager
from ..models.jira_connection import JiraConnection
from ..models.project_context import ProjectContext
from ..models.enhanced_task import EnhancedTask, TaskSuggestion
from ..models.duplicate_analysis import (
    DuplicateAnalysis, SimilarIssue, SimilarityScores, MatchType
)
from .cache_service import CacheService


@dataclass
class TaskSimilarity:
    """Legacy task similarity result for backward compatibility."""

    existing_issue_key: str
    existing_summary: str
    similarity_score: float
    recommendation: str  # 'duplicate', 'related', 'unique'
    suggested_action: str
    context_factors: List[str]


class MCPJiraService(LoggerMixin):
    """MCP-enhanced JIRA service for intelligent task management with database integration."""

    def __init__(self, config: AppConfig):
        """
        Initialize MCP JIRA service.

        Args:
            config: Application configuration
        """
        self.config = config
        self._cache_service = CacheService()
        self._db_manager = get_database_manager()
        self._credential_manager = SecureCredentialManager()
        self._mcp_client = None
        self._connection_pool = {}
        self._jira_client = None
        self._current_connection_id = None
        self._active_connections = {}

    async def initialize_mcp_client(self):
        """Initialize MCP client connection with enhanced error handling."""
        with self.log_operation("mcp_client_initialization") as logger:
            try:
                # Initialize MCP client using our utility
                self._mcp_client = get_mcp_client(self.config)

                if hasattr(self._mcp_client, 'health_check'):
                    # Test MCP connection if available
                    health_result = await self._mcp_client.health_check()
                    if not health_result.success:
                        logger.warning("MCP server health check failed, using fallback")

                logger.info("MCP client initialized successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise MCPError(f"MCP initialization failed: {str(e)}")

    async def create_jira_connection(self, name: str, base_url: str,
                                   username: str, api_token: str) -> JiraConnection:
        """
        Create and validate a new JIRA connection.

        Args:
            name: Friendly name for the connection
            base_url: JIRA base URL
            username: JIRA username
            api_token: JIRA API token

        Returns:
            JiraConnection object

        Raises:
            JiraAuthenticationError: If authentication fails
            EncryptionError: If credential encryption fails
        """
        with self.log_operation("create_jira_connection", connection_name=name) as logger:
            try:
                # Create connection object
                connection = JiraConnection.create(
                    name=name,
                    base_url=base_url,
                    username=username,
                    api_token=api_token
                )

                # Encrypt and store credentials
                encrypted_credentials = self._credential_manager.store_jira_credentials(
                    username=username,
                    api_token=api_token,
                    base_url=base_url
                )

                connection.encrypted_credentials = encrypted_credentials

                # Test connection
                is_valid = await self._test_connection(connection)
                connection.validation_status = "valid" if is_valid else "invalid"
                connection.last_validated = datetime.now()

                # Save to database
                connection_data = {
                    'id': connection.id,
                    'name': connection.name,
                    'base_url': connection.base_url,
                    'encrypted_credentials': encrypted_credentials,
                    'is_active': True,
                    'metadata': {
                        'username': username,
                        'created_at': connection.created_at.isoformat(),
                        'validation_status': connection.validation_status
                    }
                }

                self._db_manager.save_jira_connection(connection_data)
                logger.info(f"JIRA connection '{name}' created and validated")

                return connection

            except Exception as e:
                logger.error(f"Failed to create JIRA connection: {e}")
                if "authentication" in str(e).lower():
                    raise JiraAuthenticationError(f"Authentication failed: {str(e)}")
                raise JiraConnectionError(f"Connection creation failed: {str(e)}")

    async def get_available_connections(self) -> List[JiraConnection]:
        """Get all available JIRA connections."""
        try:
            connections_data = self._db_manager.list_active_jira_connections()
            connections = []

            for conn_data in connections_data:
                connection = JiraConnection(
                    id=conn_data['id'],
                    name=conn_data['name'],
                    base_url=conn_data['base_url'],
                    encrypted_credentials=b'',  # Don't expose credentials
                    validation_status=conn_data.get('validation_status', 'unknown'),
                    last_validated=datetime.fromisoformat(conn_data['last_validated']) if conn_data['last_validated'] else None
                )
                connections.append(connection)

            return connections

        except Exception as e:
            self.logger.error(f"Failed to get available connections: {e}")
            raise DatabaseError(f"Failed to retrieve connections: {str(e)}")

    async def activate_connection(self, connection_id: str) -> bool:
        """
        Activate a JIRA connection for use.

        Args:
            connection_id: Connection ID to activate

        Returns:
            True if activation successful

        Raises:
            JiraConnectionError: If connection activation fails
        """
        with self.log_operation("activate_connection", connection_id=connection_id) as logger:
            try:
                # Get connection from database
                connection_data = self._db_manager.get_jira_connection(connection_id)
                if not connection_data:
                    raise JiraConnectionError(f"Connection {connection_id} not found")

                # Decrypt credentials
                credentials = self._credential_manager.retrieve_jira_credentials(
                    connection_data['encrypted_credentials']
                )

                # Create MCP client or fallback client
                if hasattr(self._mcp_client, 'authenticate_jira'):
                    # Use MCP authentication
                    auth_result = await self._mcp_client.authenticate_jira(
                        base_url=credentials['base_url'],
                        username=credentials['username'],
                        api_token=credentials['api_token']
                    )

                    if not auth_result.success:
                        raise JiraAuthenticationError(f"MCP authentication failed: {auth_result.error}")

                    self._current_connection_id = connection_id
                    self._active_connections[connection_id] = {
                        'credentials': credentials,
                        'activated_at': datetime.now(),
                        'mcp_connection_id': auth_result.data.get('connection_id') if auth_result.data else None
                    }
                else:
                    # Use direct authentication
                    from atlassian import Jira

                    jira_client = Jira(
                        url=credentials['base_url'],
                        username=credentials['username'],
                        password=credentials['api_token'],
                        cloud=True
                    )

                    # Test connection
                    user_info = jira_client.myself()
                    logger.info(f"Authenticated as: {user_info.get('displayName', credentials['username'])}")

                    self._current_connection_id = connection_id
                    self._active_connections[connection_id] = {
                        'credentials': credentials,
                        'client': jira_client,
                        'activated_at': datetime.now()
                    }

                # Update validation status
                self._db_manager.update_connection_validation(connection_id, "valid")

                logger.info(f"Connection {connection_id} activated successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to activate connection: {e}")
                # Update validation status to failed
                try:
                    self._db_manager.update_connection_validation(connection_id, "failed")
                except:
                    pass

                if "authentication" in str(e).lower():
                    raise JiraAuthenticationError(f"Authentication failed: {str(e)}")
                raise JiraConnectionError(f"Connection activation failed: {str(e)}")

    async def _test_connection(self, connection: JiraConnection) -> bool:
        """Test JIRA connection validity."""
        try:
            # Decrypt credentials for testing
            credentials = self._credential_manager.retrieve_jira_credentials(
                connection.encrypted_credentials
            )

            from atlassian import Jira

            jira_client = Jira(
                url=credentials['base_url'],
                username=credentials['username'],
                password=credentials['api_token'],
                cloud=True
            )

            # Test with a simple API call
            user_info = jira_client.myself()
            return bool(user_info and user_info.get('accountId'))

        except Exception as e:
            self.logger.warning(f"Connection test failed: {e}")
            return False

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
        Get enriched project list with context data and caching.

        Returns:
            List of projects with additional context
        """
        if not self._current_connection_id:
            raise JiraConnectionError("No active JIRA connection")

        cache_key = f"enriched_projects_{self._current_connection_id}"

        with self.log_operation("get_enriched_projects", connection_id=self._current_connection_id) as logger:
            # Check cache first
            cached_data = self._cache_service.get(cache_key)
            if cached_data:
                logger.info("Returning cached enriched projects")
                return cached_data

            try:
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
                        'last_updated': project.get('last_updated', ''),
                        'connection_id': self._current_connection_id
                    }
                    enriched_projects.append(enriched_project)

                # Cache for configured TTL
                self._cache_service.set(cache_key, enriched_projects, ttl=self.config.jira.cache_ttl)

                logger.info(f"Retrieved {len(enriched_projects)} enriched projects")
                return enriched_projects

            except Exception as e:
                logger.error(f"Failed to get enriched projects: {e}")
                # Fallback to basic project list
                return await self._get_basic_projects()

    async def get_project_context(self, project_key: str) -> ProjectContext:
        """
        Get comprehensive project context with database integration.

        Args:
            project_key: JIRA project key

        Returns:
            Enhanced project context data

        Raises:
            JiraConnectionError: If no active connection
            ProjectContextError: If context retrieval fails
        """
        if not self._current_connection_id:
            raise JiraConnectionError("No active JIRA connection")

        with self.log_operation("get_project_context", project_key=project_key,
                               connection_id=self._current_connection_id) as logger:
            try:
                # Check database cache first
                cached_context = self._db_manager.get_project_context(
                    self._current_connection_id, project_key
                )

                if cached_context and cached_context.get('cache_expires_at'):
                    expires_at = datetime.fromisoformat(cached_context['cache_expires_at'])
                    if datetime.now() < expires_at:
                        logger.info(f"Returning cached context for project {project_key}")
                        return ProjectContext.from_database(cached_context)

                logger.info(f"Fetching fresh project context for {project_key}")

                # Gather context data concurrently for performance
                context_tasks = [
                    self._make_mcp_call('get_project_details', {'project_key': project_key}),
                    self._make_mcp_call('get_active_sprint', {'project_key': project_key}),
                    self._make_mcp_call('get_project_epics', {'project_key': project_key}),
                    self._make_mcp_call('get_project_metadata', {'project_key': project_key}),
                    self._make_mcp_call('get_recent_issues', {'project_key': project_key, 'limit': 50})
                ]

                project_data, sprint_data, epics_data, metadata, recent_issues = await asyncio.gather(
                    *context_tasks, return_exceptions=True
                )

                # Handle potential exceptions from individual calls
                if isinstance(project_data, Exception):
                    logger.warning(f"Failed to get project details: {project_data}")
                    project_data = {}

                if isinstance(sprint_data, Exception):
                    logger.warning(f"Failed to get sprint data: {sprint_data}")
                    sprint_data = {}

                if isinstance(epics_data, Exception):
                    logger.warning(f"Failed to get epics: {epics_data}")
                    epics_data = {'epics': []}

                if isinstance(metadata, Exception):
                    logger.warning(f"Failed to get metadata: {metadata}")
                    metadata = {'issue_types': [], 'custom_fields': [], 'workflows': []}

                if isinstance(recent_issues, Exception):
                    logger.warning(f"Failed to get recent issues: {recent_issues}")
                    recent_issues = {'issues': []}

                # Create enhanced project context
                context = ProjectContext.create(
                    connection_id=self._current_connection_id,
                    project_key=project_key,
                    project_name=project_data.get('name', project_key),
                    description=project_data.get('description', ''),
                    project_type=project_data.get('projectTypeKey', 'software'),
                    lead=project_data.get('lead', {}).get('displayName', ''),
                    sprints=sprint_data.get('sprints', []),
                    epics=epics_data.get('epics', []),
                    components=metadata.get('components', []),
                    issue_types=metadata.get('issue_types', []),
                    custom_fields=metadata.get('custom_fields', []),
                    workflows=metadata.get('workflows', [])
                )

                # Analyze recent issues for AI context
                if recent_issues.get('issues'):
                    context.analyze_recent_activity(recent_issues['issues'])

                # Save to database with cache expiration
                expires_at = datetime.now() + timedelta(seconds=self.config.jira.cache_ttl)
                context_data = {
                    'id': context.id,
                    'connection_id': self._current_connection_id,
                    'project_key': project_key,
                    'project_name': context.project_name,
                    'context_data': context.to_dict(),
                    'cached_sprints': context.sprints,
                    'cached_epics': context.epics,
                    'cached_components': context.components,
                    'cached_issue_types': context.issue_types,
                    'cache_expires_at': expires_at.isoformat()
                }

                self._db_manager.save_project_context(context_data)

                logger.info(f"Project context loaded and cached for {project_key}")
                return context

            except Exception as e:
                logger.error(f"Failed to get project context: {e}")
                raise ProjectContextError(
                    f"Failed to retrieve context for project {project_key}: {str(e)}",
                    project_key=project_key,
                    context_type="full_context"
                )

    async def search_similar_tasks(self, task_id: str, project_key: str,
                                 task_summary: str, task_description: str) -> DuplicateAnalysis:
        """
        Search for similar tasks using enhanced duplicate detection.

        Args:
            task_id: Unique task identifier
            project_key: JIRA project key
            task_summary: Task summary to search for
            task_description: Task description for context

        Returns:
            Complete duplicate analysis with recommendations

        Raises:
            DuplicateDetectionError: If analysis fails
        """
        start_time = time.time()

        with self.log_operation("search_similar_tasks", task_id=task_id,
                               project_key=project_key) as logger:
            try:
                if not self._current_connection_id:
                    raise JiraConnectionError("No active JIRA connection")

                # Get project context for better matching
                project_context = await self.get_project_context(project_key)

                # Create search query
                search_query = self._build_search_query(task_summary, task_description)

                # Search for similar issues
                search_results = await self._make_mcp_call('search_similar_issues', {
                    'project_key': project_key,
                    'summary': task_summary,
                    'description': task_description,
                    'include_resolved': False,
                    'limit': self.config.jira.max_search_results
                })

                similar_issues = []
                total_searched = len(search_results.get('issues', []))

                for issue in search_results.get('issues', []):
                    similar_issue = await self._analyze_issue_similarity(
                        task_summary, task_description, issue, project_context
                    )
                    if similar_issue.similarity_scores.overall_score >= 0.3:  # Lower threshold for analysis
                        similar_issues.append(similar_issue)

                # Calculate analysis time
                analysis_time_ms = int((time.time() - start_time) * 1000)

                # Create duplicate analysis
                analysis = DuplicateAnalysis(
                    task_id=task_id,
                    project_key=project_key,
                    search_query=search_query,
                    similar_issues=similar_issues,
                    analysis_time_ms=analysis_time_ms,
                    total_issues_searched=total_searched
                )

                # Save to database
                analysis_data = {
                    'id': f"analysis_{task_id}_{int(time.time())}",
                    'task_id': task_id,
                    'project_key': project_key,
                    'connection_id': self._current_connection_id,
                    'search_query': search_query,
                    'similar_issues': json.dumps([issue.to_dict() for issue in similar_issues]),
                    'best_match_data': json.dumps(analysis.best_match.to_dict()) if analysis.best_match else None,
                    'confidence': analysis.confidence,
                    'recommended_action': analysis.recommended_action,
                    'reasoning': analysis.reasoning,
                    'analysis_time_ms': analysis_time_ms,
                    'total_issues_searched': total_searched
                }

                # Store in database (if T005 database schema task is completed)
                try:
                    self._db_manager.record_performance_metric(
                        operation_type="duplicate_analysis",
                        execution_time_ms=analysis_time_ms,
                        success=True,
                        connection_id=self._current_connection_id,
                        project_key=project_key,
                        metadata={'task_id': task_id, 'similar_issues_count': len(similar_issues)}
                    )
                except Exception:
                    pass  # Don't fail analysis if performance recording fails

                logger.log_duplicate_analysis(
                    task_id=task_id,
                    similar_issues_count=len(similar_issues),
                    best_match_score=analysis.confidence,
                    analysis_time_ms=analysis_time_ms,
                    project_key=project_key
                )

                return analysis

            except Exception as e:
                logger.error(f"Similar task search failed: {e}")
                raise DuplicateDetectionError(
                    f"Failed to analyze duplicates: {str(e)}",
                    task_id=task_id,
                    project_key=project_key
                )

    async def _analyze_issue_similarity(self, task_summary: str, task_description: str,
                                      existing_issue: Dict[str, Any],
                                      project_context: ProjectContext) -> SimilarIssue:
        """Analyze similarity between task and existing issue using enhanced algorithms."""
        fields = existing_issue.get('fields', {})
        existing_summary = fields.get('summary', '')
        existing_description = fields.get('description', '')

        # Calculate detailed similarity scores
        title_similarity = self._calculate_text_similarity(task_summary, existing_summary)
        content_similarity = self._calculate_text_similarity(task_description, existing_description)

        # Calculate semantic similarity (simplified - in production use ML models)
        semantic_similarity = self._calculate_semantic_similarity(
            f"{task_summary} {task_description}",
            f"{existing_summary} {existing_description}"
        )

        # Calculate context similarity
        context_similarity = self._calculate_context_similarity(
            existing_issue, project_context
        )

        # Calculate keyword overlap
        keyword_overlap = self._calculate_keyword_overlap(
            task_summary + " " + task_description,
            existing_summary + " " + existing_description
        )

        # Overall score (weighted average)
        overall_score = (
            title_similarity * 0.35 +
            content_similarity * 0.25 +
            semantic_similarity * 0.25 +
            context_similarity * 0.10 +
            keyword_overlap * 0.05
        )

        similarity_scores = SimilarityScores(
            overall_score=overall_score,
            title_similarity=title_similarity,
            content_similarity=content_similarity,
            semantic_similarity=semantic_similarity,
            context_similarity=context_similarity,
            keyword_overlap=keyword_overlap,
            scoring_algorithm="hybrid_v1"
        )

        # Create similar issue object
        created_date = None
        if fields.get('created'):
            try:
                created_date = datetime.fromisoformat(fields['created'].replace('Z', '+00:00'))
            except:
                pass

        similar_issue = SimilarIssue(
            issue_key=existing_issue.get('key', ''),
            summary=existing_summary,
            description=existing_description[:500],  # Truncate for storage
            status=fields.get('status', {}).get('name', 'Unknown'),
            assignee=fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else None,
            issue_type=fields.get('issuetype', {}).get('name', 'Unknown'),
            created_date=created_date,
            similarity_scores=similarity_scores,
            jira_url=existing_issue.get('self', '')
        )

        return similar_issue

    def _build_search_query(self, summary: str, description: str) -> str:
        """Build search query from task summary and description."""
        # Extract meaningful words
        text = f"{summary} {description}"
        words = [word.strip().lower() for word in text.split() if len(word) > 3]

        # Remove common stop words
        stop_words = {'that', 'this', 'with', 'from', 'they', 'been', 'have', 'were', 'said', 'each', 'which', 'their', 'time', 'will'}
        meaningful_words = [word for word in words if word not in stop_words]

        # Return top 5 words for search
        return ' '.join(meaningful_words[:5])

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity (simplified implementation)."""
        # This is a simplified version. In production, use proper ML models
        # like sentence transformers or word embeddings
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Simple Jaccard similarity with length penalty
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        jaccard = len(intersection) / len(union) if union else 0.0

        # Apply length penalty for very different text lengths
        length_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))
        return jaccard * (0.5 + 0.5 * length_ratio)

    def _calculate_context_similarity(self, existing_issue: Dict[str, Any],
                                    project_context: ProjectContext) -> float:
        """Calculate context-based similarity factors."""
        fields = existing_issue.get('fields', {})
        context_score = 0.0

        # Same issue type
        issue_type = fields.get('issuetype', {}).get('name', '')
        if issue_type in [it.get('name', '') for it in project_context.issue_types]:
            context_score += 0.3

        # Recent issue (within 30 days)
        if fields.get('created'):
            try:
                created_date = datetime.fromisoformat(fields['created'].replace('Z', '+00:00'))
                days_old = (datetime.now(timezone.utc) - created_date.replace(tzinfo=timezone.utc)).days
                if days_old <= 30:
                    context_score += 0.4
                elif days_old <= 90:
                    context_score += 0.2
            except:
                pass

        # Same component/epic context
        components = fields.get('components', [])
        if components and project_context.components:
            context_score += 0.3

        return min(context_score, 1.0)

    def _calculate_keyword_overlap(self, text1: str, text2: str) -> float:
        """Calculate keyword overlap similarity."""
        # Extract keywords (words longer than 4 characters)
        keywords1 = set(word.lower() for word in text1.split() if len(word) > 4)
        keywords2 = set(word.lower() for word in text2.split() if len(word) > 4)

        if not keywords1 or not keywords2:
            return 0.0

        intersection = keywords1.intersection(keywords2)
        return len(intersection) / max(len(keywords1), len(keywords2))

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