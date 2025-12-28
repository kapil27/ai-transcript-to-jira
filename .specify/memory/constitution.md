# AI Transcript to JIRA Constitution

## Core Principles

### I. Service-Oriented Architecture
Every feature must be implemented as a standalone service with clear boundaries and responsibilities. Services must be self-contained, independently testable, and documented with explicit contracts. No monolithic implementations that couple unrelated concerns. All services must expose their functionality through well-defined interfaces and maintain backward compatibility.

### II. API-First Design
Every service must expose functionality via REST API endpoints before implementing other interfaces. APIs must follow consistent patterns: JSON request/response, proper HTTP status codes, comprehensive error handling, and OpenAPI documentation. Web UI and CLI tools are built on top of these APIs, never as separate implementations.

### III. AI-Human Collaboration (NON-NEGOTIABLE)
AI-generated content must be validated by humans before creation in external systems like JIRA. No automated ticket creation without explicit human approval. AI suggestions must be clearly marked, editable, and overridable. Context and reasoning behind AI decisions must be preserved and auditable.

### IV. Context-Aware Processing
All transcript analysis must consider project context, team dynamics, and organizational requirements. Context templates must be maintained and versioned. Processing must adapt to different meeting types (standup, planning, retrospective) and project methodologies (Agile, Kanban, etc.).

### V. Security and Privacy First
No credentials or sensitive data in logs or cache. All API tokens and passwords must use environment variables or secure configuration. User consent required for data processing and storage. Transcript data must be handled with appropriate privacy controls and retention policies.

## Quality Standards

### Testing Requirements
- Unit tests mandatory for all services (minimum 80% coverage)
- Integration tests required for API endpoints and external service connections
- End-to-end tests for critical user workflows (transcript upload → task generation → JIRA export)
- Performance tests for AI processing pipelines and large transcript handling

### Code Quality Gates
- All code must pass linting (flake8, black formatting)
- Type hints required for all Python functions and methods
- Documentation strings mandatory for all public APIs
- Error handling must be explicit with custom exception classes
- Logging must use structured format with correlation IDs

### Performance Standards
- AI processing must complete within 2 minutes for transcripts up to 50k characters
- API responses must be under 500ms for non-AI operations
- Cache hit ratios must exceed 70% for repeat operations
- Memory usage must not exceed 2GB during normal operations

## Technology Constraints

### Core Technology Stack
- **Backend**: Python 3.11+, Flask for API layer
- **AI Integration**: Ollama for local AI, with fallback options
- **Data Storage**: SQLite for development, PostgreSQL for production
- **Caching**: Redis for session and AI response caching
- **External Integration**: MCP protocol for JIRA connectivity

### Architecture Patterns
- Repository pattern for data access layers
- Factory pattern for AI service selection
- Observer pattern for real-time updates
- Circuit breaker pattern for external service calls

### Dependency Management
- Minimize external dependencies (prefer standard library)
- Pin dependency versions in requirements.txt
- Regular security audits of all dependencies
- No GPL-licensed dependencies (MIT/Apache preferred)

## Development Workflow

### Feature Development Process
1. Create feature branch following naming convention: `feature/issue-description`
2. Update or create specifications in `.specify/specs/`
3. Implement with test-first approach
4. Validate against constitution compliance
5. Create pull request with comprehensive description
6. Code review by maintainer required
7. Automated testing must pass before merge

### Release Management
- Semantic versioning (MAJOR.MINOR.PATCH)
- Release notes must document breaking changes
- Database migrations must be backwards compatible
- Configuration changes require migration guides
- All releases must include updated API documentation

### Quality Assurance
- Manual testing required for UI changes
- AI accuracy validation on sample transcripts
- Performance regression testing before releases
- Security scanning for vulnerabilities
- Documentation review and updates

## Governance

This constitution supersedes all other development practices and guidelines. Any amendments require:
1. Documented justification for changes
2. Impact assessment on existing features
3. Migration plan for affected components
4. Approval from project maintainers

All pull requests and code reviews must verify constitutional compliance. Technical complexity must be justified against business value. When in doubt, prefer simplicity and maintainability over performance optimization.

Use the existing project documentation (README.md, API.md) for runtime development guidance and implementation details.

**Version**: 1.0.0 | **Ratified**: 2024-12-28 | **Last Amended**: 2024-12-28
