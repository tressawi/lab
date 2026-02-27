---
name: test
description: Invoke the Test Agent for test generation, execution, and coverage verification
---

# Test Agent

You are invoking the Test Agent for a testing task.

## Task Routing

Based on the user's request, determine the task type:

| Keywords | Task Type | Action |
|----------|-----------|--------|
| "generate tests", "write tests", "create tests" | Generate | Create test cases for code |
| "run tests", "execute tests" | Run | Execute test suite |
| "coverage", "verify coverage" | Coverage | Check and report coverage |
| "test this project", "test codebase" | Explore & Test | Full project test generation |

## Instructions

1. **Identify Task Type** from the user's request

2. **Query Standards** before starting:
   - Use the architecture-standards MCP server to get testing guidelines
   - "What are our testing standards?"
   - "What are our coverage requirements?"

3. **Check for Dev Context**:
   - If tests are for recent changes, gather context from dev work
   - Review files that were modified
   - Understand what was implemented

4. **Execute Task** using the test subagent:
   - Generate comprehensive tests (unit, integration, edge cases)
   - Aim for >80% coverage on new code
   - Follow existing test patterns

5. **Report Results**:
   - Test files created
   - Coverage summary
   - Key test cases
   - Untested scenarios

## User Request

$ARGUMENTS

## Invoke the Test Subagent

Launch the `test` subagent to handle this task.
