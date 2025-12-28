"""Project context data models for JIRA project metadata and context awareness."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum


class SprintState(Enum):
    """Sprint state enumeration."""
    FUTURE = "future"
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class SprintInfo:
    """Active sprint information."""
    id: int
    name: str
    state: SprintState
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goal: Optional[str] = None
    board_id: Optional[int] = None

    def __post_init__(self):
        """Convert string state to enum if necessary."""
        if isinstance(self.state, str):
            self.state = SprintState(self.state.lower())

    def is_active(self) -> bool:
        """Check if sprint is currently active."""
        return self.state == SprintState.ACTIVE

    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining in sprint."""
        if not self.end_date or self.state != SprintState.ACTIVE:
            return None

        remaining = (self.end_date - datetime.now()).days
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'goal': self.goal,
            'board_id': self.board_id,
            'days_remaining': self.days_remaining()
        }


@dataclass
class EpicInfo:
    """Available epic for task linking."""
    key: str
    summary: str
    description: Optional[str] = None
    status: str = "Open"
    assignee: Optional[str] = None
    epic_color: Optional[str] = None
    story_points_total: Optional[float] = None
    story_points_completed: Optional[float] = None

    def __post_init__(self):
        """Validate epic data after initialization."""
        if not self.key or not self.summary:
            raise ValueError("Epic key and summary are required")

    def completion_percentage(self) -> Optional[float]:
        """Calculate completion percentage based on story points."""
        if self.story_points_total and self.story_points_completed:
            return (self.story_points_completed / self.story_points_total) * 100
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'key': self.key,
            'summary': self.summary,
            'description': self.description,
            'status': self.status,
            'assignee': self.assignee,
            'epic_color': self.epic_color,
            'story_points_total': self.story_points_total,
            'story_points_completed': self.story_points_completed,
            'completion_percentage': self.completion_percentage()
        }


@dataclass
class IssueTypeInfo:
    """Project-specific issue type configuration."""
    id: str
    name: str
    description: str
    is_subtask: bool
    fields: Dict[str, Any] = field(default_factory=dict)
    icon_url: Optional[str] = None

    def __post_init__(self):
        """Validate issue type data after initialization."""
        if not self.id or not self.name:
            raise ValueError("Issue type ID and name are required")

    def is_story_like(self) -> bool:
        """Check if this issue type represents a user story or feature."""
        return self.name.lower() in ['story', 'user story', 'feature', 'new feature']

    def is_task_like(self) -> bool:
        """Check if this issue type represents a task or technical work."""
        return self.name.lower() in ['task', 'sub-task', 'technical task', 'improvement']

    def is_bug_like(self) -> bool:
        """Check if this issue type represents a bug or defect."""
        return self.name.lower() in ['bug', 'defect', 'issue', 'problem']

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_subtask': self.is_subtask,
            'fields': self.fields,
            'icon_url': self.icon_url,
            'categories': {
                'is_story_like': self.is_story_like(),
                'is_task_like': self.is_task_like(),
                'is_bug_like': self.is_bug_like()
            }
        }


@dataclass
class ComponentInfo:
    """Project component information."""
    id: str
    name: str
    description: Optional[str] = None
    lead: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'lead': self.lead
        }


@dataclass
class ProjectContext:
    """Comprehensive JIRA project context for AI-enhanced task creation."""

    project_key: str
    project_name: str
    project_description: Optional[str] = None
    project_lead: Optional[str] = None

    # Active elements
    active_sprints: List[SprintInfo] = field(default_factory=list)
    available_epics: List[EpicInfo] = field(default_factory=list)
    issue_types: List[IssueTypeInfo] = field(default_factory=list)
    components: List[ComponentInfo] = field(default_factory=list)

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    cache_expires: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=30))

    def __post_init__(self):
        """Validate project context after initialization."""
        if not self.project_key or not self.project_name:
            raise ValueError("Project key and name are required")

    def is_cache_valid(self) -> bool:
        """Check if cached project context is still valid."""
        return datetime.now() < self.cache_expires

    def get_active_sprint(self) -> Optional[SprintInfo]:
        """Get the currently active sprint."""
        for sprint in self.active_sprints:
            if sprint.is_active():
                return sprint
        return None

    def get_default_issue_type(self) -> Optional[IssueTypeInfo]:
        """Get the most appropriate default issue type for tasks."""
        # Prefer Story for user-facing features
        for issue_type in self.issue_types:
            if issue_type.is_story_like() and not issue_type.is_subtask:
                return issue_type

        # Fall back to Task for technical work
        for issue_type in self.issue_types:
            if issue_type.is_task_like() and not issue_type.is_subtask:
                return issue_type

        # Return first non-subtask type as last resort
        for issue_type in self.issue_types:
            if not issue_type.is_subtask:
                return issue_type

        return self.issue_types[0] if self.issue_types else None

    def find_epic_by_keyword(self, keyword: str) -> List[EpicInfo]:
        """Find epics that match a keyword in summary or description."""
        keyword_lower = keyword.lower()
        matches = []

        for epic in self.available_epics:
            if (keyword_lower in epic.summary.lower() or
                (epic.description and keyword_lower in epic.description.lower())):
                matches.append(epic)

        return matches

    def get_issue_type_by_name(self, name: str) -> Optional[IssueTypeInfo]:
        """Get issue type by name (case-insensitive)."""
        name_lower = name.lower()
        for issue_type in self.issue_types:
            if issue_type.name.lower() == name_lower:
                return issue_type
        return None

    def refresh_cache(self) -> None:
        """Refresh cache expiration time."""
        self.last_updated = datetime.now()
        self.cache_expires = datetime.now() + timedelta(minutes=30)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the project context."""
        return {
            'project_key': self.project_key,
            'project_name': self.project_name,
            'active_sprints_count': len([s for s in self.active_sprints if s.is_active()]),
            'available_epics_count': len(self.available_epics),
            'issue_types_count': len(self.issue_types),
            'components_count': len(self.components),
            'cache_valid': self.is_cache_valid(),
            'last_updated': self.last_updated.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert project context to dictionary for JSON serialization."""
        return {
            'project_key': self.project_key,
            'project_name': self.project_name,
            'project_description': self.project_description,
            'project_lead': self.project_lead,
            'active_sprints': [sprint.to_dict() for sprint in self.active_sprints],
            'available_epics': [epic.to_dict() for epic in self.available_epics],
            'issue_types': [it.to_dict() for it in self.issue_types],
            'components': [comp.to_dict() for comp in self.components],
            'last_updated': self.last_updated.isoformat(),
            'cache_expires': self.cache_expires.isoformat(),
            'summary_stats': self.get_summary_stats()
        }

    def __str__(self) -> str:
        """String representation for logging."""
        active_sprint = self.get_active_sprint()
        sprint_info = f" (Active: {active_sprint.name})" if active_sprint else ""
        return f"{self.project_key}: {self.project_name}{sprint_info}"