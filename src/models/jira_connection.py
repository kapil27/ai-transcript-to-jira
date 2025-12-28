"""JIRA connection data models for secure authentication and connection management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import re


@dataclass
class JiraConnection:
    """Secure connection configuration for JIRA instance."""

    id: str
    name: str
    base_url: str
    username: str
    api_token_encrypted: bytes

    # Connection metadata
    is_active: bool = True
    last_tested: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Configuration
    timeout: int = 30
    max_retries: int = 3
    requests_per_minute: int = 50

    def __post_init__(self):
        """Validate connection configuration after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate connection configuration."""
        if not self.base_url.startswith('https://'):
            raise ValueError("JIRA URL must use HTTPS")

        if not self.username or not self.api_token_encrypted:
            raise ValueError("Username and API token are required")

        # Validate URL format for Atlassian Cloud
        url_pattern = r'https://[a-zA-Z0-9\-]+\.atlassian\.net/?$'
        if not re.match(url_pattern, self.base_url):
            raise ValueError("Invalid JIRA URL format. Expected: https://company.atlassian.net")

        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', self.username):
            raise ValueError("Username must be a valid email address")

        if self.timeout < 5 or self.timeout > 300:
            raise ValueError("Timeout must be between 5 and 300 seconds")

        if self.max_retries < 0 or self.max_retries > 5:
            raise ValueError("Max retries must be between 0 and 5")

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert connection to dictionary for JSON serialization."""
        data = {
            'id': self.id,
            'name': self.name,
            'base_url': self.base_url,
            'username': self.username,
            'is_active': self.is_active,
            'last_tested': self.last_tested.isoformat() if self.last_tested else None,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat(),
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'requests_per_minute': self.requests_per_minute
        }

        if include_sensitive:
            # Only include encrypted token in secure contexts
            data['api_token_encrypted'] = self.api_token_encrypted

        return data

    def update_test_result(self, success: bool, error_message: Optional[str] = None) -> None:
        """Update connection test results."""
        self.last_tested = datetime.now()
        if success:
            self.last_error = None
            self.is_active = True
        else:
            self.last_error = error_message
            self.is_active = False

    def get_api_base_url(self) -> str:
        """Get the base URL for JIRA REST API calls."""
        return f"{self.base_url.rstrip('/')}/rest/api/3"

    def is_healthy(self) -> bool:
        """Check if connection is considered healthy."""
        if not self.is_active:
            return False

        if self.last_error:
            return False

        # Consider connection healthy if tested within last hour
        if self.last_tested:
            time_since_test = datetime.now() - self.last_tested
            return time_since_test.total_seconds() < 3600

        # Never tested connections are not healthy
        return False

    def __str__(self) -> str:
        """String representation for logging (no sensitive data)."""
        status = "✓" if self.is_healthy() else "✗"
        return f"{status} {self.name} ({self.username}@{self.base_url})"