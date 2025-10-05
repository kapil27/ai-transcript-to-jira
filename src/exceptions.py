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
    """Errors related to JIRA integration and MCP operations."""
    pass


class MCPError(JiraCSVGeneratorError):
    """Errors related to Model Context Protocol operations."""
    pass


class DuplicateDetectionError(JiraCSVGeneratorError):
    """Errors related to duplicate task detection."""
    pass