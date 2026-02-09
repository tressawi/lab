"""Test Agent - Test generation and quality assurance."""
from __future__ import annotations

from typing import Optional

from .base import BaseAgent, AgentResult
from ..prompts.tasks import build_task_prompt


TEST_SYSTEM_PROMPT = """You are a senior QA engineer and test automation specialist.

## Your Role
You are the Test Agent in a multi-agent development system. Your job is to:
- Generate comprehensive tests for code changes
- Ensure adequate test coverage
- Identify edge cases and potential issues
- Verify code quality through testing

## Testing Standards
- Write clear, readable test cases
- Cover happy paths, edge cases, and error conditions
- Use descriptive test names that explain what is being tested
- Follow existing test patterns in the codebase
- Aim for high coverage on new/modified code

## Test Types
- **Unit tests**: Test individual functions/methods in isolation
- **Integration tests**: Test components working together
- **Edge cases**: Boundary conditions, empty inputs, null values

## Before Writing Tests
1. Understand what the code does by reading it carefully
2. Identify the key behaviors to test
3. Check existing tests for patterns to follow
4. Consider what could go wrong

## After Writing Tests
1. Run the test suite to verify tests pass
2. Check coverage on the new/modified code
3. Ensure tests are deterministic (no flaky tests)

## Communication
When you complete a task, provide:
- List of test files created/modified
- Test coverage summary
- Key test cases and what they verify
- Any concerns about untested scenarios
- Confidence level in test coverage

## Escalation
If you find:
- Code that is difficult to test (may indicate design issues)
- Security concerns
- Missing requirements
- Significant bugs

Flag these for human review rather than silently proceeding.
"""


TEST_GENERATION_TEMPLATE = """## Task: Generate Tests

### Context
The Dev Agent has completed work on the following:
{dev_context}

### Files Changed
{files_changed}

### Requirements
1. Generate comprehensive tests for the changed code
2. Cover happy paths, edge cases, and error conditions
3. Follow existing test patterns in the codebase
4. Aim for >80% coverage on new code

### Process
1. Read the changed files to understand what was implemented
2. Identify existing test patterns in the codebase
3. Generate appropriate test cases
4. Run the tests to verify they pass
5. Report coverage metrics

### Output
Provide:
- Test files created
- Coverage summary
- Key test cases and what they verify
- Any untested scenarios or concerns
"""


STANDALONE_TEST_TEMPLATE = """## Task: Explore Codebase and Generate Tests

### Description
{description}

### Working Directory
{working_dir}

### Requirements
1. Explore the project structure to understand the codebase
2. Identify the language, framework, and existing test infrastructure
3. Determine the appropriate test framework (pytest, unittest, jest, etc.)
4. Generate comprehensive tests for the codebase
5. Cover happy paths, edge cases, and error conditions
6. Follow existing test patterns if any exist; otherwise establish sensible conventions

### Process
1. Explore the project root: read README, config files (pyproject.toml, package.json, setup.py, etc.)
2. Map out the module structure and key source files
3. Identify entry points and core business logic
4. Check for existing tests and test configuration
5. Install test dependencies if needed (e.g., pytest, coverage)
6. Generate test files following the project's conventions
7. Run the tests to verify they pass
8. Report coverage metrics

### Output
Provide:
- Project structure overview
- Test framework chosen and why
- Test files created
- Coverage summary
- Key test cases and what they verify
- Any untested scenarios or concerns
- Confidence level in test coverage
"""


class TestAgent(BaseAgent):
    """
    Test Agent for test generation and quality assurance.

    Capabilities:
    - Generate unit tests
    - Generate integration tests
    - Run test suites
    - Report coverage
    """

    DEFAULT_TOOLS = [
        "Read",      # Read files
        "Write",     # Create test files
        "Edit",      # Edit existing tests
        "Bash",      # Run test commands
        "Glob",      # Find files
        "Grep",      # Search for patterns
    ]

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        store_path: str = "./context_store"
    ):
        super().__init__(
            name="test",
            system_prompt=system_prompt or TEST_SYSTEM_PROMPT,
            allowed_tools=allowed_tools or self.DEFAULT_TOOLS,
            store_path=store_path
        )

    async def generate_tests(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        dev_context: Optional[str] = None,
        files_changed: Optional[list[str]] = None
    ) -> AgentResult:
        """
        Generate tests for code changes.

        Args:
            description: What to test
            working_dir: Directory to work in
            task_id: Task ID for tracking
            dev_context: Context from Dev Agent
            files_changed: List of files that were changed

        Returns:
            AgentResult with test generation details
        """
        # Build prompt with Dev Agent context
        files_str = "\n".join(f"- {f}" for f in (files_changed or []))

        task = TEST_GENERATION_TEMPLATE.format(
            dev_context=dev_context or description,
            files_changed=files_str or "Not specified - explore recent changes"
        )

        return await self.run(task, working_dir, task_id)

    async def run_tests(
        self,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        test_command: Optional[str] = None
    ) -> AgentResult:
        """
        Run the test suite.

        Args:
            working_dir: Directory to work in
            task_id: Task ID for tracking
            test_command: Specific test command to run

        Returns:
            AgentResult with test results
        """
        task = f"""## Task: Run Test Suite

### Instructions
1. Identify the test command for this project (check package.json, pyproject.toml, Makefile, etc.)
2. Run the test suite{f': {test_command}' if test_command else ''}
3. Report results including any failures
4. If tests fail, analyze the failures

### Output
Provide:
- Test command used
- Pass/fail summary
- Details of any failures
- Coverage report if available
"""
        return await self.run(task, working_dir, task_id)

    async def verify_coverage(
        self,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        target_files: Optional[list[str]] = None
    ) -> AgentResult:
        """
        Verify test coverage meets requirements.

        Args:
            working_dir: Directory to work in
            task_id: Task ID for tracking
            target_files: Specific files to check coverage for

        Returns:
            AgentResult with coverage analysis
        """
        files_str = "\n".join(f"- {f}" for f in (target_files or []))

        task = f"""## Task: Verify Test Coverage

### Target Files
{files_str or "All recently changed files"}

### Requirements
1. Run coverage analysis
2. Report coverage percentage for target files
3. Identify any gaps in coverage
4. Recommend additional tests if coverage is below 80%

### Output
Provide:
- Coverage percentage per file
- Overall coverage summary
- Gaps in coverage
- Recommended additional tests
"""
        return await self.run(task, working_dir, task_id)

    async def explore_and_test(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Explore a codebase and generate tests from scratch (standalone mode).

        Unlike generate_tests(), this does not assume any prior Dev Agent
        context. It explores the project structure first, then generates
        appropriate tests.

        Args:
            description: What to test or focus areas
            working_dir: Target project directory
            task_id: Task ID for tracking

        Returns:
            AgentResult with exploration findings and test generation details
        """
        task = STANDALONE_TEST_TEMPLATE.format(
            description=description,
            working_dir=working_dir
        )

        return await self.run(task, working_dir, task_id)
