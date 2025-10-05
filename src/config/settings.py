"""Configuration management for the JIRA CSV Generator application."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OllamaConfig:
    """Configuration for Ollama AI service."""
    
    model_name: str = "llama3.1:latest"
    base_url: str = "http://localhost:11434"
    timeout: int = 120
    temperature: float = 0.1
    top_p: float = 0.9


@dataclass
class MCPConfig:
    """Configuration for MCP integration."""

    atlassian_server_url: str = "mcp://atlassian"
    connection_timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 300  # 5 minutes


@dataclass
class JiraConfig:
    """Configuration for JIRA integration."""

    base_url: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None
    project_key: Optional[str] = None
    similarity_threshold: float = 0.85
    max_search_results: int = 50


@dataclass
class AppConfig:
    """Main application configuration."""

    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 5000
    secret_key: Optional[str] = None

    # AI Configuration
    ollama: OllamaConfig = None

    # MCP Configuration
    mcp: MCPConfig = None

    # JIRA Configuration
    jira: JiraConfig = None

    # Processing limits
    max_tasks_per_transcript: int = 10
    max_questions_per_transcript: int = 8
    max_transcript_length: int = 50000

    # Legacy JIRA Configuration (for backward compatibility)
    default_reporter: str = "meeting@example.com"
    valid_issue_types: tuple = ("Story", "Task", "Bug", "Epic")
    
    def __post_init__(self):
        """Initialize nested configs and apply environment overrides."""
        if self.ollama is None:
            self.ollama = OllamaConfig()
        if self.mcp is None:
            self.mcp = MCPConfig()
        if self.jira is None:
            self.jira = JiraConfig()

        # Apply environment variable overrides
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", self.host)
        self.port = int(os.getenv("PORT", self.port))
        self.secret_key = os.getenv("SECRET_KEY", self.secret_key)
        
        # Ollama configuration
        self.ollama.model_name = os.getenv("OLLAMA_MODEL", self.ollama.model_name)
        self.ollama.base_url = os.getenv("OLLAMA_URL", self.ollama.base_url)
        self.ollama.timeout = int(os.getenv("OLLAMA_TIMEOUT", self.ollama.timeout))
        
        # Processing limits
        self.max_tasks_per_transcript = int(os.getenv("MAX_TASKS", self.max_tasks_per_transcript))
        self.max_questions_per_transcript = int(os.getenv("MAX_QUESTIONS", self.max_questions_per_transcript))
        self.max_transcript_length = int(os.getenv("MAX_TRANSCRIPT_LENGTH", self.max_transcript_length))

        # MCP configuration
        self.mcp.atlassian_server_url = os.getenv("MCP_ATLASSIAN_URL", self.mcp.atlassian_server_url)
        self.mcp.connection_timeout = int(os.getenv("MCP_TIMEOUT", self.mcp.connection_timeout))
        self.mcp.max_retries = int(os.getenv("MCP_MAX_RETRIES", self.mcp.max_retries))
        self.mcp.cache_ttl = int(os.getenv("MCP_CACHE_TTL", self.mcp.cache_ttl))

        # JIRA configuration
        self.jira.base_url = os.getenv("JIRA_URL", self.jira.base_url)
        self.jira.username = os.getenv("JIRA_USERNAME", self.jira.username)
        self.jira.api_token = os.getenv("JIRA_API_TOKEN", self.jira.api_token)
        self.jira.project_key = os.getenv("JIRA_PROJECT_KEY", self.jira.project_key)
        self.jira.similarity_threshold = float(os.getenv("JIRA_SIMILARITY_THRESHOLD", self.jira.similarity_threshold))
        self.jira.max_search_results = int(os.getenv("JIRA_MAX_SEARCH_RESULTS", self.jira.max_search_results))

        # Legacy JIRA configuration (for backward compatibility)
        self.default_reporter = os.getenv("DEFAULT_REPORTER", self.default_reporter)


def get_config() -> AppConfig:
    """Get the application configuration instance."""
    return AppConfig()