"""Enhanced task data models with JIRA project context and AI suggestions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from .task import JiraTask


@dataclass
class TaskSuggestion:
    """AI-generated suggestions for JIRA field mapping."""
    issue_type: str
    epic_key: Optional[str] = None
    sprint_id: Optional[int] = None
    priority: str = "Medium"
    confidence: float = 0.0
    reasoning: str = ""
    component: Optional[str] = None

    def __post_init__(self):
        """Validate suggestion data after initialization."""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence suggestion."""
        return self.confidence >= 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'issue_type': self.issue_type,
            'epic_key': self.epic_key,
            'sprint_id': self.sprint_id,
            'priority': self.priority,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'component': self.component,
            'is_high_confidence': self.is_high_confidence()
        }


@dataclass
class EnhancedTask(JiraTask):
    """Task enriched with JIRA project context and AI suggestions."""

    # JIRA context enhancements
    project_key: str = ""
    suggestions: Optional[TaskSuggestion] = None
    project_context_score: float = 0.0

    # Duplicate analysis
    duplicate_analysis: Optional['DuplicateAnalysis'] = None

    # Metadata
    extracted_from: str = ""
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    id: Optional[str] = None

    def __post_init__(self):
        """Enhanced validation including project context."""
        # Call parent validation first
        super().__post_init__()

        # Additional validation for enhanced features
        if self.project_context_score < 0.0 or self.project_context_score > 1.0:
            raise ValueError("Project context score must be between 0.0 and 1.0")

        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")

        # Generate ID if not provided
        if not self.id:
            self.id = f"task_{self.created_at.strftime('%Y%m%d_%H%M%S')}_{hash(self.summary) % 10000:04d}"

    def has_project_context(self) -> bool:
        """Check if task has meaningful project context."""
        return bool(self.project_key and self.suggestions)

    def is_high_quality(self) -> bool:
        """Check if this is a high-quality extracted task."""
        return (self.confidence_score >= 0.7 and
                self.project_context_score >= 0.6 and
                len(self.summary.split()) >= 3)

    def get_suggested_issue_type(self) -> str:
        """Get the AI-suggested issue type or fall back to default."""
        if self.suggestions and self.suggestions.issue_type:
            return self.suggestions.issue_type
        return self.issue_type

    def get_suggested_priority(self) -> str:
        """Get the AI-suggested priority."""
        if self.suggestions and self.suggestions.priority:
            return self.suggestions.priority
        return "Medium"

    def has_potential_duplicates(self) -> bool:
        """Check if duplicate analysis found potential duplicates."""
        return (self.duplicate_analysis and
                self.duplicate_analysis.has_significant_duplicates())

    def to_jira_payload(self) -> Dict[str, Any]:
        """Convert to JIRA issue creation payload."""
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": self.summary,
                "description": self.description,
                "issuetype": {"name": self.get_suggested_issue_type()},
                "priority": {"name": self.get_suggested_priority()}
            }
        }

        # Add optional fields if available
        if self.suggestions:
            if self.suggestions.epic_key:
                payload["fields"]["parent"] = {"key": self.suggestions.epic_key}

            if self.suggestions.component:
                payload["fields"]["components"] = [{"name": self.suggestions.component}]

            if self.suggestions.sprint_id:
                # Note: Sprint assignment typically done via separate API call
                payload["sprint_id"] = self.suggestions.sprint_id

        return payload

    def to_enhanced_dict(self) -> Dict[str, Any]:
        """Convert to enhanced dictionary including all context and suggestions."""
        base_dict = self.to_dict()

        enhanced_dict = {
            **base_dict,
            'id': self.id,
            'project_key': self.project_key,
            'project_context_score': self.project_context_score,
            'confidence_score': self.confidence_score,
            'extracted_from': self.extracted_from,
            'created_at': self.created_at.isoformat(),
            'suggestions': self.suggestions.to_dict() if self.suggestions else None,
            'duplicate_analysis': (self.duplicate_analysis.to_dict()
                                 if self.duplicate_analysis else None),
            'quality_metrics': {
                'has_project_context': self.has_project_context(),
                'is_high_quality': self.is_high_quality(),
                'has_potential_duplicates': self.has_potential_duplicates()
            },
            'jira_payload': self.to_jira_payload()
        }

        return enhanced_dict

    def apply_suggestions(self) -> None:
        """Apply AI suggestions to base task properties."""
        if not self.suggestions:
            return

        if self.suggestions.issue_type:
            self.issue_type = self.suggestions.issue_type

        # Note: priority and other fields are handled in to_jira_payload
        # since they're not part of the base JiraTask model

    def update_from_jira_response(self, jira_response: Dict[str, Any]) -> None:
        """Update task with information from JIRA creation response."""
        if 'key' in jira_response:
            self.id = jira_response['key']

        if 'self' in jira_response:
            # Store JIRA URL for reference
            self.jira_url = jira_response['self']

    def calculate_overall_score(self) -> float:
        """Calculate overall task quality score combining multiple factors."""
        scores = [
            self.confidence_score * 0.4,  # AI confidence in extraction
            self.project_context_score * 0.3,  # Project context relevance
            (self.suggestions.confidence if self.suggestions else 0.5) * 0.2,  # Suggestion confidence
            (1.0 if len(self.summary.split()) >= 4 else 0.5) * 0.1  # Summary completeness
        ]

        return sum(scores)

    def __str__(self) -> str:
        """String representation for logging and debugging."""
        project_info = f"[{self.project_key}]" if self.project_key else "[No Project]"
        quality_score = f"{self.calculate_overall_score():.2f}"
        return f"{project_info} {self.summary[:50]}... (Quality: {quality_score})"