# Data Model: Enhanced JIRA Project Specification

**Feature**: Enhanced JIRA Project Specification and Integration
**Date**: 2024-12-28

## Core Entities

### 1. JIRA Connection
Represents an authenticated connection to a JIRA instance.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

@dataclass
class JiraConnection:
    """Secure connection configuration for JIRA instance"""
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
        """Validate connection configuration"""
        if not self.base_url.startswith('https://'):
            raise ValueError("JIRA URL must use HTTPS")
        if not self.username or not self.api_token_encrypted:
            raise ValueError("Username and API token are required")
```

### 2. Project Context
Rich metadata about a JIRA project including active elements and schemas.

```python
@dataclass
class SprintInfo:
    """Active sprint information"""
    id: int
    name: str
    state: str  # active, future, closed
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    goal: Optional[str]

@dataclass
class EpicInfo:
    """Available epic for task linking"""
    key: str
    summary: str
    description: Optional[str]
    status: str
    assignee: Optional[str]

@dataclass
class IssueTypeInfo:
    """Project-specific issue type configuration"""
    id: str
    name: str
    description: str
    is_subtask: bool
    fields: Dict[str, Any]  # Required and optional fields

@dataclass
class WorkflowInfo:
    """Project workflow configuration"""
    name: str
    statuses: List[str]
    transitions: Dict[str, List[str]]

@dataclass
class ProjectContext:
    """Comprehensive JIRA project context"""
    project_key: str
    project_name: str
    project_description: Optional[str]
    project_lead: Optional[str]

    # Active elements
    active_sprints: List[SprintInfo] = field(default_factory=list)
    available_epics: List[EpicInfo] = field(default_factory=list)
    issue_types: List[IssueTypeInfo] = field(default_factory=list)
    workflows: Dict[str, WorkflowInfo] = field(default_factory=dict)

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    cache_expires: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=30))

    def is_cache_valid(self) -> bool:
        """Check if cached project context is still valid"""
        return datetime.now() < self.cache_expires

    def get_default_issue_type(self) -> Optional[IssueTypeInfo]:
        """Get the most appropriate default issue type for tasks"""
        for issue_type in self.issue_types:
            if issue_type.name.lower() in ['story', 'task'] and not issue_type.is_subtask:
                return issue_type
        return self.issue_types[0] if self.issue_types else None
```

### 3. Enhanced Task
Extended task model with JIRA project context and AI suggestions.

```python
@dataclass
class TaskSuggestion:
    """AI-generated suggestions for JIRA field mapping"""
    issue_type: str
    epic_key: Optional[str]
    sprint_id: Optional[int]
    priority: str
    confidence: float  # 0.0 - 1.0
    reasoning: str

@dataclass
class EnhancedTask:
    """Task enriched with JIRA project context and suggestions"""
    # Base task information (inherited from existing Task model)
    summary: str
    description: str
    issue_type: str
    priority: str
    reporter: str

    # JIRA context enhancements
    project_key: str
    suggestions: TaskSuggestion
    project_context_score: float  # How well task aligns with project

    # Duplicate analysis
    duplicate_analysis: Optional['DuplicateAnalysis'] = None

    # Metadata
    extracted_from: str  # transcript section or document
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_jira_payload(self) -> Dict[str, Any]:
        """Convert to JIRA issue creation payload"""
        return {
            "fields": {
                "project": {"key": self.project_key},
                "summary": self.summary,
                "description": self.description,
                "issuetype": {"name": self.suggestions.issue_type},
                "priority": {"name": self.suggestions.priority},
                "reporter": {"name": self.reporter}
            }
        }
```

### 4. Duplicate Analysis
Results of similarity detection against existing JIRA issues.

```python
class MatchType(Enum):
    """Type of potential duplicate match"""
    IDENTICAL = "identical"      # >95% similarity
    VERY_SIMILAR = "very_similar"  # >85% similarity
    SIMILAR = "similar"          # >70% similarity
    RELATED = "related"          # >50% similarity, different context

@dataclass
class SimilarIssue:
    """Existing JIRA issue that may be related to extracted task"""
    issue_key: str
    summary: str
    description: str
    status: str
    assignee: Optional[str]

    # Similarity metrics
    title_similarity: float
    content_similarity: float
    context_similarity: float  # Same epic, sprint, component
    overall_score: float

    match_type: MatchType

@dataclass
class DuplicateAnalysis:
    """Complete duplicate detection results for a task"""
    task_id: str
    project_key: str

    # Analysis results
    similar_issues: List[SimilarIssue] = field(default_factory=list)
    best_match: Optional[SimilarIssue] = None
    confidence: float = 0.0

    # User resolution
    resolution: Optional[str] = None  # create_new, link_to_existing, skip
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def has_significant_duplicates(self) -> bool:
        """Check if any similar issues warrant user attention"""
        return any(issue.overall_score >= 0.7 for issue in self.similar_issues)

    def get_recommended_action(self) -> str:
        """AI recommendation for handling duplicates"""
        if not self.similar_issues:
            return "create_new"

        best_score = max(issue.overall_score for issue in self.similar_issues)
        if best_score >= 0.95:
            return "likely_duplicate"
        elif best_score >= 0.85:
            return "review_required"
        elif best_score >= 0.70:
            return "consider_linking"
        else:
            return "create_new"
```

### 5. Processing Session
Tracks a complete transcript processing session with project context.

```python
@dataclass
class ProcessingSession:
    """Complete session for transcript processing with JIRA integration"""
    session_id: str
    user_id: str
    project_key: str

    # Input
    transcript_content: str
    context_provided: Optional[str] = None

    # Processing results
    extracted_tasks: List[EnhancedTask] = field(default_factory=list)
    qa_items: List[Any] = field(default_factory=list)  # Using existing QAItem model

    # JIRA integration results
    created_issues: List[str] = field(default_factory=list)  # JIRA issue keys
    skipped_duplicates: List[str] = field(default_factory=list)
    failed_creations: List[Dict[str, str]] = field(default_factory=list)

    # Session metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "processing"  # processing, completed, failed, cancelled

    def get_success_rate(self) -> float:
        """Calculate percentage of successfully created tasks"""
        total = len(self.extracted_tasks)
        if total == 0:
            return 0.0
        successful = len(self.created_issues)
        return successful / total
```

## Data Relationships

### Entity Relationship Diagram
```
JiraConnection (1) ←→ (N) ProjectContext
    ↓
ProcessingSession (1) ←→ (N) EnhancedTask
    ↓                          ↓
EnhancedTask (1) ←→ (1) DuplicateAnalysis
    ↓
SimilarIssue (N) ← DuplicateAnalysis
```

### Key Relationships
- **One-to-Many**: JiraConnection → ProjectContext (one connection can access multiple projects)
- **One-to-Many**: ProcessingSession → EnhancedTask (one session produces multiple tasks)
- **One-to-One**: EnhancedTask → DuplicateAnalysis (each task gets duplicate analysis)
- **One-to-Many**: DuplicateAnalysis → SimilarIssue (analysis may find multiple similar issues)

## Storage Strategy

### SQLite Schema (Development)
```sql
-- JIRA Connections
CREATE TABLE jira_connections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    username TEXT NOT NULL,
    api_token_encrypted BLOB NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    last_tested TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config JSON  -- timeout, retries, etc.
);

-- Project Contexts (cached)
CREATE TABLE project_contexts (
    project_key TEXT PRIMARY KEY,
    connection_id TEXT REFERENCES jira_connections(id),
    project_data JSON NOT NULL,  -- Serialized ProjectContext
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_expires TIMESTAMP
);

-- Processing Sessions
CREATE TABLE processing_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_key TEXT NOT NULL,
    transcript_content TEXT NOT NULL,
    context_provided TEXT,
    results JSON,  -- Serialized session results
    status TEXT DEFAULT 'processing',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Task Creation History
CREATE TABLE task_history (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES processing_sessions(session_id),
    task_data JSON NOT NULL,  -- Serialized EnhancedTask
    jira_issue_key TEXT,
    duplicate_analysis JSON,
    status TEXT NOT NULL,  -- created, skipped, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Redis Caching Strategy
```python
# Cache keys pattern
CACHE_PATTERNS = {
    "project_context": "jira:project:{project_key}:context",
    "connection_health": "jira:connection:{connection_id}:health",
    "duplicate_search": "jira:duplicates:{project_key}:{content_hash}",
    "user_session": "session:{session_id}:data"
}

# TTL values
CACHE_TTL = {
    "project_context": 1800,      # 30 minutes
    "connection_health": 300,      # 5 minutes
    "duplicate_search": 3600,      # 1 hour
    "user_session": 7200           # 2 hours
}
```

## Validation Rules

### Data Validation
```python
class JiraConnectionValidator:
    @staticmethod
    def validate_url(url: str) -> bool:
        """Ensure JIRA URL is properly formatted and uses HTTPS"""
        return url.startswith('https://') and '.atlassian.net' in url

    @staticmethod
    def validate_credentials(username: str, token: str) -> bool:
        """Validate username format and token structure"""
        return '@' in username and len(token) >= 24

class TaskValidator:
    @staticmethod
    def validate_for_jira(task: EnhancedTask, project_context: ProjectContext) -> List[str]:
        """Validate task against JIRA project requirements"""
        errors = []

        # Check required fields
        if not task.summary or len(task.summary) < 3:
            errors.append("Summary must be at least 3 characters")

        # Validate issue type
        valid_types = [it.name for it in project_context.issue_types]
        if task.suggestions.issue_type not in valid_types:
            errors.append(f"Issue type must be one of: {valid_types}")

        return errors
```

## Migration Strategy

### From Existing Models
```python
class TaskMigration:
    @staticmethod
    def enhance_existing_task(task: Task, project_context: ProjectContext) -> EnhancedTask:
        """Convert existing Task to EnhancedTask with project context"""
        suggestions = TaskSuggestion(
            issue_type=task.issue_type,
            epic_key=None,  # Will be determined by AI
            sprint_id=None,
            priority=task.priority,
            confidence=0.5,
            reasoning="Migrated from existing task"
        )

        return EnhancedTask(
            summary=task.summary,
            description=task.description,
            issue_type=task.issue_type,
            priority=task.priority,
            reporter=task.reporter,
            project_key=project_context.project_key,
            suggestions=suggestions,
            project_context_score=0.5,
            extracted_from="migration"
        )
```

This data model provides a robust foundation for the Enhanced JIRA Project Specification feature, maintaining compatibility with existing models while adding the rich context and intelligence needed for advanced JIRA integration.