---
name: dev
description: Invoke the Dev Agent for code development tasks - features, bugfixes, refactoring, design documents, and code reviews
---

# Dev Agent

You are invoking the Dev Agent for a development task.

## Task Routing

Based on the user's request, determine the task type:

| Keywords | Task Type | Action |
|----------|-----------|--------|
| "design", "plan", "propose" | Design | Create design document (NO code) |
| "implement", "build", "create", "add feature" | Feature | Implement following design-first |
| "fix", "bug", "broken", "error" | Bugfix | Find root cause and fix |
| "refactor", "improve", "clean up" | Refactor | Improve without changing behavior |
| "review", "check", "audit code" | Review | Code quality review |
| "explore", "understand", "how does" | Explore | Codebase exploration |

## Instructions

1. **Identify Task Type** from the user's request using the table above

2. **Query Standards** before starting:
   - Use the architecture-standards MCP server to get relevant guidelines
   - Check for reusable components in the library

3. **Execute Task** using the dev subagent:
   - For design tasks: Create design document, do NOT write code
   - For features: Check if design exists, follow it if approved
   - For all tasks: Follow organizational standards

4. **Report Results**:
   - Files created/modified
   - Components reused
   - Key decisions
   - Confidence level

## User Request

$ARGUMENTS

## Invoke the Dev Subagent

Launch the `dev` subagent to handle this task. Pass the full context including:
- The task type identified
- The user's original request
- Any relevant standards retrieved from MCP
