# Using AI Agent Personas in Cursor

This guide shows you how to leverage the Ambient Code Platform's agent personas directly in Cursor - no API credits needed!

## Quick Start Examples

Copy-paste these prompts into Cursor chat:

### Example 1: Code Review with Amber

```
Act as Amber from the Ambient Code Platform. You are the "Codebase Illuminati" - 
an expert pair programmer focused on high signal, low noise feedback.

Review src/services/ai_service.py and:
1. Identify any code quality issues
2. Check for proper error handling
3. Suggest improvements with specific code examples
4. Rate confidence level (High/Medium/Low) for each suggestion

Remember: Show code, not concepts. Be specific with file:line references.
```

### Example 2: Architecture Review with Stella

```
Act as Stella, a Staff Engineer from the Ambient Code Platform. You focus on 
technical leadership and bridging architecture to implementation.

Analyze the overall structure of this project and answer:
1. What are the key architectural strengths?
2. Where are potential scalability bottlenecks?
3. What refactoring would you prioritize for maintainability?
4. How would you structure tests for better coverage?

Provide concrete recommendations with trade-offs explained.
```

### Example 3: Documentation with Terry

```
Act as Terry, a Technical Writer from the Ambient Code Platform.

Review the README.md and suggest improvements:
1. Is the quick start clear for new developers?
2. Are the API endpoints well documented?
3. What sections are missing?
4. Write an improved "Getting Started" section.
```

### Example 4: Feature Planning with Parker

```
Act as Parker, a Product Manager from the Ambient Code Platform.

I want to add a feature to export Jira tickets to different formats (PDF, Word).
Help me:
1. Define user stories with acceptance criteria
2. Identify edge cases and error scenarios
3. Prioritize the implementation phases
4. Suggest MVP scope vs future enhancements
```

---

## Pro Tips

### 1. Load Full Persona (For Complex Tasks)

For deep work, load the entire agent persona:

```
Read the file at /Users/knema/Project/personal-ai-tools/platform/agents/amber.md 
and adopt that persona completely. Then help me refactor the transcript_parser.py 
to be more maintainable.
```

### 2. Combine Personas

```
First, act as Parker (PM) to define what this feature should do.
Then switch to Stella (Staff Engineer) to design how to implement it.
Finally, act as Terry to document it.
```

### 3. Use Context Files for Domain Knowledge

```
Read /Users/knema/Project/personal-ai-tools/platform/.claude/patterns/error-handling.md
then review my error handling in src/services/ and suggest improvements following 
those patterns.
```

### 4. Create Custom Prompts for Repeated Tasks

Save this as a snippet for quick code reviews:

```
Act as Amber. Review this file for:
- [ ] Type hints on all functions
- [ ] Docstrings for public methods  
- [ ] Proper exception handling
- [ ] No hardcoded values (use config)
- [ ] Unit test coverage suggestions

Be specific with line numbers. Show fixed code examples.
```

---

## Agent Persona Quick Reference

| Agent | Specialty | Best For |
|-------|-----------|----------|
| **Amber** | Codebase Intelligence | Code review, debugging, refactoring |
| **Stella** | Staff Engineer | Architecture, system design, mentoring |
| **Parker** | Product Manager | Requirements, user stories, prioritization |
| **Terry** | Technical Writer | Docs, READMEs, API documentation |
| **Ryan** | UX Researcher | User research, feedback analysis |
| **Steve** | UX Designer | UI patterns, design systems |

---

## File Locations

```
Agent Personas:
  /Users/knema/Project/personal-ai-tools/platform/agents/
  ├── amber.md              # Codebase intelligence
  ├── stella-staff_engineer.md
  ├── parker-product_manager.md
  ├── terry-technical_writer.md
  ├── ryan-ux_researcher.md
  └── steve-ux_designer.md

Context Files:
  /Users/knema/Project/personal-ai-tools/platform/.claude/context/
  ├── backend-development.md
  ├── frontend-development.md
  └── security-standards.md

Code Patterns:
  /Users/knema/Project/personal-ai-tools/platform/.claude/patterns/
  ├── error-handling.md
  ├── k8s-client-usage.md
  └── react-query-usage.md
```

---

## Try It Now!

Open any Python file in this project and paste this in Cursor chat:

```
Act as Amber, the codebase expert. You give high-signal feedback and show 
concrete code examples. Review the currently open file and:

1. Rate the overall code quality (1-10)
2. List the top 3 improvements needed
3. Show the improved code for each issue
4. Suggest one test case that's missing

Be direct and specific. Reference line numbers.
```

---

## Why This Works

Cursor uses the same Claude models as the Ambient Code Platform. By providing 
the agent persona as context, you get:

- Consistent behavior and tone
- Domain expertise baked in
- Best practices automatically applied
- Structured, actionable output

The agent personas are essentially "prompt engineering" packaged as reusable 
characters that know your project's standards.

