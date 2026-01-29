"""Dev Agent - Code generation, refactoring, and maintenance."""
from __future__ import annotations

from typing import Optional

from .base import BaseAgent, AgentResult
from ..prompts.system import DEV_SYSTEM_PROMPT
from ..prompts.tasks import build_task_prompt, build_design_prompt
from ..library import ComponentLibrary


class DevAgent(BaseAgent):
    """
    Dev Agent for code development tasks.

    Capabilities:
    - Create designs for approval before implementation
    - Check component library for reusable code
    - Implement new features
    - Fix bugs
    - Refactor code
    - Explore codebases
    - Custom development tasks
    """

    # Tools available to the Dev Agent
    DEFAULT_TOOLS = [
        "Read",      # Read files
        "Write",     # Create/overwrite files
        "Edit",      # Edit existing files
        "Bash",      # Run shell commands
        "Glob",      # Find files by pattern
        "Grep",      # Search file contents
    ]

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        store_path: str = "./context_store",
        component_library: Optional[ComponentLibrary] = None
    ):
        super().__init__(
            name="dev",
            system_prompt=system_prompt or DEV_SYSTEM_PROMPT,
            allowed_tools=allowed_tools or self.DEFAULT_TOOLS,
            store_path=store_path
        )
        self.component_library = component_library or ComponentLibrary()

    async def create_design(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Create a design document for approval before implementation.

        This is the first step in the design-first workflow. The design
        must be approved before implementation begins.

        Args:
            description: What feature/change to design
            working_dir: Directory to analyze
            task_id: Optional task ID for tracking

        Returns:
            AgentResult with design document
        """
        # Search component library for relevant components
        library_components = self.component_library.search(description)
        library_context = self.component_library.format_for_prompt(library_components[:5])

        task = build_design_prompt(description, library_context)
        return await self.run(task, working_dir, task_id)

    async def implement_feature(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        approved_design: Optional[str] = None
    ) -> AgentResult:
        """
        Implement a new feature.

        Args:
            description: What feature to implement
            working_dir: Directory to work in
            task_id: Optional task ID for tracking
            approved_design: Optional approved design document to follow

        Returns:
            AgentResult with implementation details
        """
        # Search component library for relevant components
        library_components = self.component_library.search(description)
        library_context = self.component_library.format_for_prompt(library_components[:5])

        task = build_task_prompt("feature", description, library_context, approved_design)
        return await self.run(task, working_dir, task_id)

    async def fix_bug(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Fix a bug.

        Args:
            description: Description of the bug
            working_dir: Directory to work in
            task_id: Optional task ID for tracking

        Returns:
            AgentResult with fix details
        """
        task = build_task_prompt("bugfix", description)
        return await self.run(task, working_dir, task_id)

    async def refactor(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Refactor code.

        Args:
            description: What to refactor and why
            working_dir: Directory to work in
            task_id: Optional task ID for tracking

        Returns:
            AgentResult with refactoring details
        """
        task = build_task_prompt("refactor", description)
        return await self.run(task, working_dir, task_id)

    async def review_code(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Review code for issues.

        Args:
            description: What to review
            working_dir: Directory to work in
            task_id: Optional task ID for tracking

        Returns:
            AgentResult with review findings
        """
        task = build_task_prompt("review", description)
        return await self.run(task, working_dir, task_id)

    async def explore(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Explore and understand a codebase.

        Args:
            description: What to explore/understand
            working_dir: Directory to work in
            task_id: Optional task ID for tracking

        Returns:
            AgentResult with exploration findings
        """
        task = build_task_prompt("explore", description)
        return await self.run(task, working_dir, task_id)

    async def custom_task(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        resume: bool = False
    ) -> AgentResult:
        """
        Run a custom task.

        Args:
            description: The task to perform
            working_dir: Directory to work in
            task_id: Optional task ID for tracking
            resume: Whether to resume the last session

        Returns:
            AgentResult with task outcome
        """
        task = build_task_prompt("custom", description)
        return await self.run(task, working_dir, task_id, resume_session=resume)
