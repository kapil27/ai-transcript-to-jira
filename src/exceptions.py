"""Custom exceptions for the JIRA CSV Generator application."""


class JiraCSVGeneratorError(Exception):
    """Base exception for all application errors."""
    pass


class TranscriptError(JiraCSVGeneratorError):
    """Errors related to transcript processing."""
    pass


class AIServiceError(JiraCSVGeneratorError):
    """Errors related to AI service communication."""
    pass


class ValidationError(JiraCSVGeneratorError):
    """Errors related to data validation."""
    pass


class ConfigurationError(JiraCSVGeneratorError):
    """Errors related to application configuration."""
    pass


class CSVGenerationError(JiraCSVGeneratorError):
    """Errors related to CSV file generation."""
    pass


class ExportError(JiraCSVGeneratorError):
    """Errors related to data export operations."""
    pass


class JiraIntegrationError(JiraCSVGeneratorError):
    """Base class for JIRA integration errors."""

    def __init__(self, message: str, error_code: str = None, connection_id: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.connection_id = connection_id


class JiraConnectionError(JiraIntegrationError):
    """Errors related to JIRA connection establishment and validation."""
    pass


class JiraAuthenticationError(JiraIntegrationError):
    """Errors related to JIRA authentication and authorization."""
    pass


class JiraAPIError(JiraIntegrationError):
    """Errors from JIRA REST API responses."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_data = response_data or {}


class JiraProjectError(JiraIntegrationError):
    """Errors related to JIRA project context and configuration."""

    def __init__(self, message: str, project_key: str = None, **kwargs):
        super().__init__(message, **kwargs)
        self.project_key = project_key


class JiraRateLimitError(JiraIntegrationError):
    """Errors when JIRA API rate limits are exceeded."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class MCPError(JiraCSVGeneratorError):
    """Base class for Model Context Protocol errors."""

    def __init__(self, message: str, mcp_server_url: str = None, operation: str = None):
        super().__init__(message)
        self.mcp_server_url = mcp_server_url
        self.operation = operation


class MCPConnectionError(MCPError):
    """Errors related to MCP server connection."""
    pass


class MCPTimeoutError(MCPError):
    """Errors when MCP operations timeout."""
    pass


class MCPServerError(MCPError):
    """Errors from MCP server responses."""

    def __init__(self, message: str, status_code: int = None, server_response: dict = None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.server_response = server_response or {}


class DuplicateDetectionError(JiraCSVGeneratorError):
    """Base class for duplicate detection errors."""

    def __init__(self, message: str, task_id: str = None, project_key: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.project_key = project_key


class SimilarityCalculationError(DuplicateDetectionError):
    """Errors during similarity score calculation."""
    pass


class DuplicateAnalysisError(DuplicateDetectionError):
    """Errors during duplicate analysis processing."""
    pass


class EncryptionError(JiraCSVGeneratorError):
    """Errors related to credential encryption/decryption."""

    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.operation = operation


class DatabaseError(JiraCSVGeneratorError):
    """Errors related to database operations."""

    def __init__(self, message: str, table_name: str = None, operation: str = None):
        super().__init__(message)
        self.table_name = table_name
        self.operation = operation


class TaskProcessingError(JiraCSVGeneratorError):
    """Errors during task processing and enhancement."""

    def __init__(self, message: str, task_id: str = None, processing_stage: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.processing_stage = processing_stage


class ProjectContextError(JiraCSVGeneratorError):
    """Errors related to project context retrieval and processing."""

    def __init__(self, message: str, project_key: str = None, context_type: str = None):
        super().__init__(message)
        self.project_key = project_key
        self.context_type = context_type


class WorkflowError(JiraCSVGeneratorError):
    """Errors in the complete transcript-to-JIRA workflow."""

    def __init__(self, message: str, workflow_stage: str = None, task_count: int = 0):
        super().__init__(message)
        self.workflow_stage = workflow_stage
        self.task_count = task_count