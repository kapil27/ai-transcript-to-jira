"""Task data models for JIRA integration."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import re


@dataclass
class JiraTask:
    """Represents a JIRA task with all required and optional fields."""
    
    summary: str
    description: str = ""
    issue_type: str = "Task"
    reporter: str = "meeting@example.com"
    due_date: Optional[str] = None
    
    def __post_init__(self):
        """Validate task data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate task data according to JIRA requirements."""
        if not self.summary or not self.summary.strip():
            raise ValueError("Task summary is required and cannot be empty")
        
        if len(self.summary) > 255:
            raise ValueError("Task summary cannot exceed 255 characters")
        
        valid_issue_types = {"Story", "Task", "Bug", "Epic"}
        if self.issue_type not in valid_issue_types:
            raise ValueError(f"Issue type must be one of: {valid_issue_types}")
        
        if self.reporter and "@" not in self.reporter:
            raise ValueError("Reporter must be a valid email address")
        
        if self.due_date and not self._is_valid_date_format(self.due_date):
            raise ValueError("Due date must be in YYYY-MM-DD format")
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string is in valid YYYY-MM-DD format."""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization."""
        return {
            'summary': self.summary,
            'description': self.description,
            'issue_type': self.issue_type,
            'reporter': self.reporter,
            'due_date': self.due_date or ""
        }