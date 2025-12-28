"""Duplicate analysis data models for smart JIRA task duplicate detection."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class MatchType(Enum):
    """Type of potential duplicate match."""
    IDENTICAL = "identical"      # >95% similarity
    VERY_SIMILAR = "very_similar"  # >85% similarity
    SIMILAR = "similar"          # >70% similarity
    RELATED = "related"          # >50% similarity, different context
    WEAK = "weak"               # <50% similarity


class ResolutionAction(Enum):
    """User resolution actions for duplicate handling."""
    CREATE_NEW = "create_new"
    LINK_TO_EXISTING = "link_to_existing"
    MERGE_WITH_EXISTING = "merge_with_existing"
    SKIP_CREATION = "skip_creation"


@dataclass
class SimilarityScores:
    """Detailed similarity scoring breakdown."""
    overall_score: float
    title_similarity: float = 0.0
    content_similarity: float = 0.0
    semantic_similarity: float = 0.0
    context_similarity: float = 0.0
    keyword_overlap: float = 0.0
    scoring_algorithm: str = "hybrid"

    def __post_init__(self):
        """Validate similarity scores."""
        scores = [self.overall_score, self.title_similarity, self.content_similarity,
                 self.semantic_similarity, self.context_similarity, self.keyword_overlap]

        for score in scores:
            if score < 0.0 or score > 1.0:
                raise ValueError("All similarity scores must be between 0.0 and 1.0")

    def get_primary_match_reason(self) -> str:
        """Get the primary reason for the similarity match."""
        max_score = max([
            (self.title_similarity, "title similarity"),
            (self.content_similarity, "content similarity"),
            (self.semantic_similarity, "semantic meaning"),
            (self.context_similarity, "project context"),
            (self.keyword_overlap, "keyword overlap")
        ])
        return max_score[1]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_score': self.overall_score,
            'title_similarity': self.title_similarity,
            'content_similarity': self.content_similarity,
            'semantic_similarity': self.semantic_similarity,
            'context_similarity': self.context_similarity,
            'keyword_overlap': self.keyword_overlap,
            'scoring_algorithm': self.scoring_algorithm,
            'primary_match_reason': self.get_primary_match_reason()
        }


@dataclass
class ContextFactors:
    """Context factors that influence duplicate detection."""
    same_epic: bool = False
    same_component: bool = False
    same_sprint: bool = False
    same_assignee: bool = False
    same_issue_type: bool = False
    temporal_proximity: float = 0.0  # 1.0 = same day, 0.0 = >30 days apart
    reporter_relationship: str = "unknown"  # same, team_member, different_team, external

    def get_context_boost(self) -> float:
        """Calculate context similarity boost factor."""
        boost = 0.0

        if self.same_epic:
            boost += 0.2
        if self.same_component:
            boost += 0.1
        if self.same_sprint:
            boost += 0.15
        if self.same_assignee:
            boost += 0.1
        if self.same_issue_type:
            boost += 0.05

        # Temporal proximity boost (max 0.1)
        boost += self.temporal_proximity * 0.1

        return min(boost, 0.5)  # Cap at 50% boost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'same_epic': self.same_epic,
            'same_component': self.same_component,
            'same_sprint': self.same_sprint,
            'same_assignee': self.same_assignee,
            'same_issue_type': self.same_issue_type,
            'temporal_proximity': self.temporal_proximity,
            'reporter_relationship': self.reporter_relationship,
            'context_boost': self.get_context_boost()
        }


@dataclass
class SimilarIssue:
    """Existing JIRA issue that may be related to extracted task."""
    issue_key: str
    summary: str
    description: str = ""
    status: str = "Open"
    assignee: Optional[str] = None
    priority: str = "Medium"
    issue_type: str = "Task"
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None

    # Similarity analysis
    similarity_scores: SimilarityScores = field(default_factory=lambda: SimilarityScores(0.0))
    match_type: MatchType = MatchType.WEAK
    context_factors: ContextFactors = field(default_factory=ContextFactors)
    jira_url: Optional[str] = None

    def __post_init__(self):
        """Validate similar issue data."""
        if not self.issue_key or not self.summary:
            raise ValueError("Issue key and summary are required")

        # Determine match type based on overall similarity score
        score = self.similarity_scores.overall_score
        if score >= 0.95:
            self.match_type = MatchType.IDENTICAL
        elif score >= 0.85:
            self.match_type = MatchType.VERY_SIMILAR
        elif score >= 0.70:
            self.match_type = MatchType.SIMILAR
        elif score >= 0.50:
            self.match_type = MatchType.RELATED
        else:
            self.match_type = MatchType.WEAK

    def is_actionable_duplicate(self) -> bool:
        """Check if this similarity warrants user attention."""
        return self.match_type in [MatchType.IDENTICAL, MatchType.VERY_SIMILAR]

    def get_recommendation(self) -> str:
        """Get AI recommendation for how to handle this potential duplicate."""
        if self.match_type == MatchType.IDENTICAL:
            return "likely_duplicate"
        elif self.match_type == MatchType.VERY_SIMILAR:
            return "review_required"
        elif self.match_type == MatchType.SIMILAR:
            return "consider_linking"
        else:
            return "create_new"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'issue_key': self.issue_key,
            'summary': self.summary,
            'description': self.description,
            'status': self.status,
            'assignee': self.assignee,
            'priority': self.priority,
            'issue_type': self.issue_type,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'similarity_scores': self.similarity_scores.to_dict(),
            'match_type': self.match_type.value,
            'context_factors': self.context_factors.to_dict(),
            'jira_url': self.jira_url,
            'is_actionable_duplicate': self.is_actionable_duplicate(),
            'recommendation': self.get_recommendation()
        }


@dataclass
class UserResolution:
    """User's decision on how to handle duplicate suggestions."""
    action_taken: ResolutionAction
    selected_issue: Optional[str] = None
    user_reasoning: str = ""
    resolved_by: Optional[str] = None
    resolved_at: datetime = field(default_factory=datetime.now)
    confidence_in_decision: int = 3  # 1-5 scale

    def __post_init__(self):
        """Validate user resolution data."""
        if self.confidence_in_decision < 1 or self.confidence_in_decision > 5:
            raise ValueError("Confidence in decision must be between 1 and 5")

        if (self.action_taken in [ResolutionAction.LINK_TO_EXISTING, ResolutionAction.MERGE_WITH_EXISTING]
            and not self.selected_issue):
            raise ValueError("Selected issue required for link/merge actions")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'action_taken': self.action_taken.value,
            'selected_issue': self.selected_issue,
            'user_reasoning': self.user_reasoning,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat(),
            'confidence_in_decision': self.confidence_in_decision
        }


@dataclass
class DuplicateAnalysis:
    """Complete duplicate detection results for a task."""
    task_id: str
    project_key: str
    search_query: Optional[str] = None

    # Analysis results
    similar_issues: List[SimilarIssue] = field(default_factory=list)
    best_match: Optional[SimilarIssue] = None
    confidence: float = 0.0
    recommended_action: str = "create_new"
    reasoning: str = ""

    # Processing metadata
    analysis_time_ms: int = 0
    total_issues_searched: int = 0
    algorithm_version: str = "1.0.0"

    # User resolution
    resolution: Optional[UserResolution] = None
    analyzed_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Process analysis results after initialization."""
        if self.similar_issues:
            # Find best match
            self.best_match = max(self.similar_issues,
                                key=lambda issue: issue.similarity_scores.overall_score)

            # Update confidence based on best match
            self.confidence = self.best_match.similarity_scores.overall_score

            # Generate recommendation
            self.recommended_action = self._generate_recommendation()
            self.reasoning = self._generate_reasoning()

    def has_significant_duplicates(self) -> bool:
        """Check if any similar issues warrant user attention."""
        return any(issue.similarity_scores.overall_score >= 0.7 for issue in self.similar_issues)

    def get_actionable_duplicates(self) -> List[SimilarIssue]:
        """Get list of duplicates that require user decision."""
        return [issue for issue in self.similar_issues if issue.is_actionable_duplicate()]

    def _generate_recommendation(self) -> str:
        """Generate AI recommendation based on analysis results."""
        if not self.best_match:
            return "create_new"

        return self.best_match.get_recommendation()

    def _generate_reasoning(self) -> str:
        """Generate human-readable reasoning for the recommendation."""
        if not self.best_match:
            return "No similar issues found in project"

        score = self.best_match.similarity_scores.overall_score
        reason = self.best_match.similarity_scores.get_primary_match_reason()

        if score >= 0.95:
            return f"Very high similarity ({score:.0%}) based on {reason}"
        elif score >= 0.85:
            return f"High similarity ({score:.0%}) based on {reason} - review recommended"
        elif score >= 0.70:
            return f"Moderate similarity ({score:.0%}) based on {reason} - consider linking"
        else:
            return f"Low similarity ({score:.0%}) - safe to create new issue"

    def add_user_resolution(self, resolution: UserResolution) -> None:
        """Add user resolution to the analysis."""
        self.resolution = resolution

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the duplicate analysis."""
        return {
            'total_issues_searched': self.total_issues_searched,
            'similar_issues_found': len(self.similar_issues),
            'actionable_duplicates': len(self.get_actionable_duplicates()),
            'best_match_score': self.best_match.similarity_scores.overall_score if self.best_match else 0.0,
            'analysis_time_ms': self.analysis_time_ms,
            'has_resolution': self.resolution is not None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'task_id': self.task_id,
            'project_key': self.project_key,
            'search_query': self.search_query,
            'similar_issues': [issue.to_dict() for issue in self.similar_issues],
            'best_match': self.best_match.to_dict() if self.best_match else None,
            'confidence': self.confidence,
            'recommended_action': self.recommended_action,
            'reasoning': self.reasoning,
            'analysis_time_ms': self.analysis_time_ms,
            'total_issues_searched': self.total_issues_searched,
            'algorithm_version': self.algorithm_version,
            'resolution': self.resolution.to_dict() if self.resolution else None,
            'analyzed_at': self.analyzed_at.isoformat(),
            'summary_stats': self.get_summary_stats(),
            'quality_metrics': {
                'has_significant_duplicates': self.has_significant_duplicates(),
                'actionable_duplicates_count': len(self.get_actionable_duplicates())
            }
        }

    def __str__(self) -> str:
        """String representation for logging."""
        if self.best_match:
            score = self.best_match.similarity_scores.overall_score
            return f"Duplicate Analysis: {self.task_id} -> {self.best_match.issue_key} ({score:.0%})"
        else:
            return f"Duplicate Analysis: {self.task_id} -> No matches found"