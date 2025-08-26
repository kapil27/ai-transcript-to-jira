"""Configuration management for the JIRA CSV Generator application."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OllamaConfig:
    """Configuration for Ollama AI service."""
    
    model_name: str = "llama3.1:latest"
    base_url: str = "http://localhost:11434"
    timeout: int = 60
    temperature: float = 0.1
    top_p: float = 0.9


@dataclass
class AppConfig:
    """Main application configuration."""
    
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 5000
    secret_key: Optional[str] = None
    
    # AI Configuration
    ollama: OllamaConfig = None
    
    # Processing limits
    max_tasks_per_transcript: int = 10
    max_questions_per_transcript: int = 8
    max_transcript_length: int = 50000
    
    # JIRA Configuration
    default_reporter: str = "meeting@example.com"
    valid_issue_types: tuple = ("Story", "Task", "Bug", "Epic")
    
    def __post_init__(self):
        """Initialize nested configs and apply environment overrides."""
        if self.ollama is None:
            self.ollama = OllamaConfig()
        
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
        
        # JIRA configuration
        self.default_reporter = os.getenv("DEFAULT_REPORTER", self.default_reporter)


def get_config() -> AppConfig:
    """Get the application configuration instance."""
    return AppConfig()