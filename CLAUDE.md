# AI Transcript to JIRA - Development Context

Last updated: 2024-12-28 | Active Feature: Enhanced JIRA Project Specification

## Current Development State

**Status**: Sprint 2 Implementation - Enhanced JIRA Project Specification feature
**Branch**: `001-enhanced-jira-project`
**Priority**: P1 (Critical for Sprint 2 completion)

## Active Feature: Enhanced JIRA Project Specification

### Summary
Implementing dynamic JIRA project selection with MCP-enhanced authentication and context-aware task creation. This bridges the gap between existing transcript processing (Sprint 1 completed) and real JIRA integration.

### Key Components Being Built
- **MCP JIRA Service**: Advanced JIRA integration with project context awareness
- **Context-Aware AI**: Project-specific task enhancement and classification
- **Smart Duplicate Detection**: Similarity-based duplicate prevention
- **Enhanced Web Interface**: Project selection and JIRA workflow management

## Technology Stack

**Language**: Python 3.11+
**Framework**: Flask (existing), MCP Protocol (new)
**AI**: Ollama with llama3.1 (existing)
**Storage**: SQLite/PostgreSQL, Redis caching
**Frontend**: Vanilla JavaScript (existing)
**New Dependencies**: atlassian-python-api, aiohttp, fuzzywuzzy, cryptography

## Project Structure

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
└── utils/
    └── mcp_client.py           # NEW: MCP protocol client utilities

tests/
├── unit/
│   ├── test_mcp_jira_service.py        # NEW: 25+ tests
│   ├── test_context_aware_ai_service.py # NEW: 20+ tests
│   ├── test_smart_duplicate_service.py  # NEW: 15+ tests
└── integration/
    ├── test_jira_workflow.py           # NEW: End-to-end tests
    └── test_mcp_integration.py         # NEW: MCP protocol tests
```

## Implementation Roadmap (Sprint 2)

### Phase 1: Foundation (P1 - Critical)
1. **MCP JIRA Service** - Core JIRA integration with authentication
2. **Project Selection Interface** - Dropdown and context loading
3. **Basic Project Context** - Fetch sprints, epics, issue types

### Phase 2: Intelligence (P2 - Value Add)
1. **Context-Aware AI Enhancement** - Project-specific task suggestions
2. **Smart Duplicate Detection** - Similarity analysis against existing issues
3. **Enhanced Task Creation** - JIRA workflow integration

### Phase 3: Analytics (P3 - Future)
1. **Project Dashboard** - Metrics and impact analysis
2. **Advanced Reporting** - Team productivity insights

## Constitution Compliance

✅ **Service-Oriented Architecture**: Each new component is a standalone service
✅ **API-First Design**: All JIRA functionality exposed via REST endpoints
✅ **AI-Human Collaboration**: Human approval required for JIRA task creation
✅ **Context-Aware Processing**: Project context enhances all AI operations
✅ **Security First**: Encrypted credential storage, secure MCP integration

## Key Implementation Guidelines

### Authentication & Security
- Encrypt JIRA API tokens using Fernet encryption
- Store encryption keys in environment variables
- Never log sensitive credentials or tokens
- Implement proper error handling for auth failures

### Performance Standards
- Project context loading: < 5 seconds
- Duplicate analysis: < 10 seconds for 50 issues
- End-to-end workflow: < 2 minutes total
- Cache project metadata with 30-minute TTL

### Error Handling
- Graceful degradation when JIRA is unavailable
- Clear error messages for authentication failures
- Retry logic for transient network issues
- User-friendly conflict resolution for duplicates

### Testing Requirements
- Unit tests for all new services (80%+ coverage)
- Integration tests for JIRA API interactions
- Mock JIRA responses for consistent testing
- End-to-end workflow validation

## Current Development Commands

```bash
# Start development environment
python app.py

# Run comprehensive test suite (expanding from 157+ to 180+ tests)
pytest tests/ -v

# Test JIRA connectivity
python -c "from src.services.mcp_jira_service import MCPJiraService; service = MCPJiraService(); print(service.test_connection())"

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Run with debug logging
DEBUG=true python app.py
```

## Architecture Decisions

### MCP vs Direct JIRA API
**Decision**: Start with enhanced JIRA REST API, upgrade to MCP later
**Reasoning**: MCP protocol still maturing, REST API provides immediate functionality

### Async Integration
**Decision**: Use asyncio.run() within Flask routes for JIRA calls
**Reasoning**: Maintains Flask simplicity while enabling async JIRA operations

### Duplicate Detection Algorithm
**Decision**: Hybrid approach using JQL search + fuzzywuzzy similarity
**Reasoning**: Balances accuracy with performance, leverages JIRA's search capabilities

## Success Criteria

### Functional Metrics
- JIRA connection success rate > 95%
- Project context loading < 5 seconds
- Task classification accuracy improvement ≥ 40%
- Duplicate detection accuracy ≥ 85%
- End-to-end workflow completion < 2 minutes

### Technical Metrics
- All 180+ tests passing
- Zero critical security vulnerabilities
- API response times < 500ms (non-AI operations)
- Memory usage < 2GB during processing

## Next Development Session Focus

1. **Implement MCP JIRA Service** - Core authentication and project listing
2. **Build Project Selection UI** - Dropdown and context display
3. **Create Enhanced Task Model** - Project-aware task structure
4. **Test End-to-End Workflow** - Verify complete integration

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
