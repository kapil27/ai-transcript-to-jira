"""Task data models for JIRA integration."""

from dataclasses import dataclass


@dataclass
class JiraTask:
    """Represents a simplified JIRA task with core fields only."""

    summary: str
    description: str = ""
    issue_type: str = "Task"

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

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization."""
        return {
            'summary': self.summary,
            'description': self.description,
            'issue_type': self.issue_type
        }