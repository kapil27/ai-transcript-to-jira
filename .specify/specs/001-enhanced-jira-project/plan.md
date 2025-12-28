# Implementation Plan: Enhanced JIRA Project Specification and Integration

**Branch**: `001-enhanced-jira-project` | **Date**: 2024-12-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification for dynamic JIRA project selection with MCP-enhanced authentication and context-aware task creation

## Summary

Build a comprehensive JIRA project specification system that allows users to select target JIRA projects, authenticate via MCP (Model Context Protocol), and create context-aware tasks with intelligent duplicate detection. The implementation extends the existing Flask application with new MCP JIRA service, enhanced AI processing with project context, and smart duplicate detection capabilities. This feature bridges the gap between transcript processing and real JIRA integration, enabling end-to-end workflow from meeting transcripts to organized JIRA tasks.

## Technical Context

**Language/Version**: Python 3.11+ (maintaining existing codebase compatibility)
**Primary Dependencies**: Flask, mcp (Model Context Protocol client), asyncio, fuzzywuzzy, existing Ollama AI stack
**Storage**: SQLite for development (with PostgreSQL option), Redis caching (existing), file-based configuration
**Testing**: pytest (existing test framework, expanding from 157+ tests to 180+ tests)
**Target Platform**: Local development server with Docker deployment capability
**Project Type**: Web application (Flask backend + vanilla JS frontend)
**Performance Goals**: <5s project metadata retrieval, <2min end-to-end transcript-to-JIRA workflow, 85% duplicate detection accuracy
**Constraints**: MCP integration complexity, JIRA API rate limits (10 requests/minute typical), secure credential storage requirements
**Scale/Scope**: Single-user deployments with multi-project JIRA access, 50+ projects per instance, 100+ tasks per processing session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Service-Oriented Architecture**: New MCP JIRA service will be standalone with clear boundaries
✅ **API-First Design**: All JIRA functionality exposed via REST endpoints before UI implementation
✅ **AI-Human Collaboration**: Human approval required before JIRA task creation (non-negotiable)
✅ **Context-Aware Processing**: Project context will enhance transcript analysis and task categorization
✅ **Security and Privacy First**: Encrypted credential storage, no sensitive data in logs
⚠️ **Testing Requirements**: Expanding test coverage to meet 80% minimum requirement
⚠️ **Performance Standards**: Must validate <5s metadata retrieval meets constitutional constraints

## Project Structure

### Documentation (this feature)

```text
specs/001-enhanced-jira-project/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (MCP integration research)
├── data-model.md        # Phase 1 output (JIRA entities and relationships)
├── quickstart.md        # Phase 1 output (setup and configuration)
├── contracts/           # Phase 1 output (API specifications)
│   ├── mcp-jira-api.json
│   ├── project-context.schema.json
│   └── duplicate-detection.schema.json
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── jira_connection.py      # NEW: JIRA connection configuration
│   ├── project_context.py      # NEW: Project metadata and context
│   └── duplicate_analysis.py   # NEW: Duplicate detection results
├── services/
│   ├── mcp_jira_service.py     # NEW: Core MCP JIRA integration
│   ├── context_aware_ai_service.py  # NEW: Project-aware AI processing
│   ├── smart_duplicate_service.py   # NEW: Duplicate detection engine
│   └── ai_service.py           # ENHANCED: Add project context support
├── api/
│   ├── mcp_endpoints.py        # NEW: MCP JIRA API routes
│   └── routes.py               # ENHANCED: Add project context parameters
├── config/
│   └── settings.py             # ENHANCED: Add JIRA and MCP configuration
└── utils/
    └── mcp_client.py           # NEW: MCP protocol client utilities

tests/
├── unit/
│   ├── test_mcp_jira_service.py        # NEW: MCP service tests
│   ├── test_context_aware_ai_service.py # NEW: Context AI tests
│   ├── test_smart_duplicate_service.py  # NEW: Duplicate detection tests
│   └── test_project_context.py         # NEW: Project model tests
├── integration/
│   ├── test_jira_workflow.py           # NEW: End-to-end JIRA tests
│   └── test_mcp_integration.py         # NEW: MCP protocol tests
└── contract/
    └── test_api_contracts.py           # NEW: API contract validation
```

**Structure Decision**: Extending existing web application structure with new services following established patterns. MCP integration adds complexity but maintains service boundaries and constitutional compliance.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| MCP Protocol Integration | Provides enhanced JIRA capabilities vs direct REST API | Direct JIRA REST API lacks project context intelligence and real-time data access |
| Async/Await in Flask App | MCP client requires async operations | Synchronous HTTP requests to JIRA too slow and less reliable |

## Phase 0: Research & Dependencies

### MCP Integration Research
- **MCP Protocol**: Investigate Model Context Protocol implementation for JIRA integration
- **Atlassian MCP Server**: Research available MCP servers for Atlassian products
- **Async Integration**: Determine how to integrate async MCP calls within Flask request cycle
- **Authentication Flow**: Research secure credential management for MCP connections

### Performance Analysis
- **JIRA API Limits**: Research rate limiting, pagination, and bulk operations
- **Caching Strategy**: Design project metadata and duplicate detection caching
- **Concurrent Operations**: Plan for multiple project contexts and parallel processing

### Security Research
- **Credential Storage**: Research encryption methods for JIRA API tokens
- **MCP Security**: Investigate MCP protocol security implications
- **Audit Requirements**: Research logging and audit trail requirements

## Phase 1: Core Architecture & Data Models

### Data Models Design

#### JIRA Connection Model
```python
@dataclass
class JiraConnection:
    id: str
    name: str
    base_url: str
    username: str
    api_token: str  # Encrypted
    mcp_config: Optional[Dict]
    is_active: bool
    last_tested: datetime
    created_at: datetime
```

#### Project Context Model
```python
@dataclass
class ProjectContext:
    project_key: str
    project_name: str
    active_sprints: List[SprintInfo]
    available_epics: List[EpicInfo]
    issue_types: List[IssueTypeInfo]
    custom_fields: Dict[str, FieldSchema]
    workflows: Dict[str, WorkflowInfo]
    last_updated: datetime
```

#### Enhanced Task Model
```python
@dataclass
class EnhancedTask(Task):
    suggested_issue_type: str
    suggested_epic: Optional[str]
    suggested_sprint: Optional[str]
    project_context_score: float
    duplicate_analysis: Optional[DuplicateAnalysis]
```

### Service Architecture

#### MCP JIRA Service
- **Connection Management**: Establish and maintain MCP connections
- **Project Data Fetching**: Retrieve live project metadata via MCP
- **Task Creation**: Create JIRA tasks with project context
- **Search Integration**: Query existing issues for duplicate detection

#### Context-Aware AI Service
- **Prompt Enhancement**: Inject project context into AI prompts
- **Classification Suggestions**: AI-powered issue type and epic suggestions
- **Field Mapping**: Map transcript content to JIRA field requirements

#### Smart Duplicate Service
- **Similarity Engine**: Content-based similarity scoring
- **Context Weighting**: Project-aware duplicate detection
- **Resolution Workflow**: User interface for duplicate handling

### API Contract Design

#### MCP JIRA Endpoints
```
POST /api/mcp/jira/connect
GET  /api/mcp/jira/projects
GET  /api/mcp/jira/projects/{key}/context
POST /api/mcp/jira/tasks/create
POST /api/mcp/jira/search/duplicates
```

#### Enhanced Processing Endpoints
```
POST /api/process/enhanced           # With project context
POST /api/ai/suggest-classifications # Project-aware suggestions
POST /api/duplicates/analyze         # Smart duplicate detection
```

## Phase 2: Implementation Roadmap

### Sprint 1: MCP Foundation (P1 - Critical)
1. **MCP Client Integration** (4 hours)
   - Implement MCP protocol client
   - Research and select MCP JIRA server
   - Basic connection and authentication

2. **JIRA Connection Management** (4 hours)
   - Connection configuration UI
   - Credential encryption and storage
   - Connection testing and validation

### Sprint 2: Project Context (P1 - Critical)
1. **Project Selection Interface** (3 hours)
   - Project dropdown in web UI
   - Project metadata caching
   - Session context management

2. **Context-Aware AI Enhancement** (5 hours)
   - Enhance AI service with project context
   - Implement suggestion algorithms
   - Update transcript processing pipeline

### Sprint 3: Smart Features (P2 - Value Add)
1. **Duplicate Detection Engine** (4 hours)
   - Similarity scoring implementation
   - JIRA search integration
   - User resolution interface

2. **Task Creation Workflow** (4 hours)
   - Review interface for extracted tasks
   - JIRA task creation with validation
   - Error handling and retry logic

### Sprint 4: Analytics & Polish (P3 - Enhancement)
1. **Project Dashboard** (3 hours)
   - Metrics collection and display
   - Project impact analytics
   - Export and reporting features

2. **Production Readiness** (3 hours)
   - Performance optimization
   - Comprehensive testing
   - Documentation completion

## Implementation Dependencies

### New Python Packages
```
mcp==0.1.0                    # Model Context Protocol client
asyncio-compat==0.8.0         # Async/sync bridge for Flask
python-jose==3.3.0           # JWT handling for MCP auth
cryptography==41.0.7         # Credential encryption
fuzzywuzzy==0.18.0           # String similarity matching
python-levenshtein==0.23.0   # Fast string distance
```

### Configuration Extensions
```python
class JiraConfig:
    mcp_server_url: str = "mcp://atlassian"
    connection_timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 300
    similarity_threshold: float = 0.85
    max_search_results: int = 50
```

### Database Schema (SQLite/PostgreSQL)
```sql
-- JIRA Connections
CREATE TABLE jira_connections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    username TEXT NOT NULL,
    api_token_encrypted BLOB NOT NULL,
    mcp_config JSON,
    is_active BOOLEAN DEFAULT true,
    last_tested TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project Contexts (cached)
CREATE TABLE project_contexts (
    project_key TEXT PRIMARY KEY,
    connection_id TEXT REFERENCES jira_connections(id),
    metadata JSON NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task Creation History
CREATE TABLE task_history (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    jira_task_key TEXT,
    original_content TEXT NOT NULL,
    project_key TEXT NOT NULL,
    status TEXT NOT NULL, -- created/failed/duplicate/skipped
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Success Validation

### Functional Tests
- ✅ MCP connection establishment < 10 seconds
- ✅ Project metadata retrieval < 5 seconds
- ✅ Context-aware task extraction accuracy improvement ≥ 40%
- ✅ Duplicate detection accuracy ≥ 85%
- ✅ End-to-end workflow completion < 2 minutes

### Performance Benchmarks
- Project list loading: < 3 seconds
- Duplicate analysis for 50 existing issues: < 10 seconds
- Concurrent project context for 3 projects: < 15 seconds
- Cache hit ratio for project data: > 80%

### Security Validation
- ✅ Encrypted credential storage verification
- ✅ No sensitive data in application logs
- ✅ Secure MCP protocol implementation
- ✅ JIRA API token rotation capability

## Risk Mitigation

### Technical Risks
- **MCP Integration Complexity**: Fallback to direct JIRA REST API if MCP proves unstable
- **JIRA API Rate Limits**: Implement intelligent caching and request queuing
- **Async/Flask Integration**: Use asyncio compatibility layer for smooth integration

### User Experience Risks
- **Complex Configuration**: Provide guided setup wizard and validation feedback
- **Duplicate Decision Fatigue**: Smart defaults and bulk resolution options
- **Performance Degradation**: Implement progressive loading and background processing

### Security Risks
- **Credential Exposure**: Multi-layer encryption with secure key management
- **JIRA Access Scope**: Principle of least privilege for API token permissions
- **Audit Trail**: Comprehensive logging for all JIRA operations

This implementation plan provides a structured approach to building the Enhanced JIRA Project Specification feature while maintaining architectural integrity and constitutional compliance.