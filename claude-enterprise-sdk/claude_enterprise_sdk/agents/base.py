"""Base agent wrapper for Claude Agent SDK."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator
from pathlib import Path

from ..shared_context.store import ContextStore, TaskContext
from .utilities.audit import log_agent_start, log_agent_complete


@dataclass
class AgentResult:
    """Result from an agent task execution."""
    task_id: str
    session_id: Optional[str]
    content: str
    files_changed: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    """
    Base wrapper for Claude Agent SDK.

    Provides:
    - Context management (load/save shared state)
    - Session tracking (for resumption)
    - Audit logging hooks
    - Structured result handling
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        allowed_tools: list[str],
        store_path: str = "./context_store"
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools
        self.store_path = store_path
        self.context_store = ContextStore(store_path)

    async def run(
        self,
        task: str,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        resume_session: bool = False
    ) -> AgentResult:
        """
        Run the agent on a task.

        Args:
            task: The task description/prompt
            working_dir: Directory to work in
            task_id: Optional task ID (generated if not provided)
            resume_session: Whether to resume the last session

        Returns:
            AgentResult with the outcome
        """
        # Generate task ID if not provided
        if task_id is None:
            task_id = f"{self.name}-{uuid.uuid4().hex[:8]}"

        # Build context for hooks
        hook_context = {
            "agent_name": self.name,
            "task_id": task_id,
            "store_path": self.store_path,
        }

        # Log start
        await log_agent_start(self.name, task, hook_context)

        # Get session ID if resuming
        session_id = None
        if resume_session:
            session_info = self.context_store.get_session(self.name)
            if session_info:
                session_id = session_info.get("session_id")

        # Load any prior context for this task
        prior_context = self._load_prior_context(task_id)

        # Build the full prompt with context
        full_prompt = self._build_prompt(task, prior_context)

        try:
            # Import here to avoid issues if SDK not installed
            from claude_code_sdk import query, ClaudeCodeOptions

            # Run the agent via SDK
            result_content = []
            new_session_id = None

            options = ClaudeCodeOptions(
                system_prompt=self.system_prompt,
                allowed_tools=self.allowed_tools,
                cwd=working_dir,
                permission_mode="bypassPermissions",  # Auto-approve tool uses
            )

            # Add resume if we have a session to continue
            if session_id:
                options.resume = session_id

            async for message in query(prompt=full_prompt, options=options):
                # Capture session ID from response
                if hasattr(message, "session_id") and message.session_id:
                    new_session_id = message.session_id

                # Capture content - handle different message types
                if hasattr(message, "content"):
                    if isinstance(message.content, str):
                        result_content.append(message.content)
                    elif isinstance(message.content, list):
                        for block in message.content:
                            if hasattr(block, "text"):
                                result_content.append(block.text)
                            elif isinstance(block, str):
                                result_content.append(block)

            final_content = "\n".join(filter(None, result_content))

            # Save session for future resumption
            if new_session_id:
                self.context_store.save_session(self.name, new_session_id, task_id)

            # Create result
            result = AgentResult(
                task_id=task_id,
                session_id=new_session_id,
                content=final_content,
                success=True
            )

            # Save task context
            self._save_task_context(task_id, task, result)

            # Log completion
            await log_agent_complete(self.name, final_content, hook_context)

            return result

        except ImportError:
            # SDK not installed - provide helpful error
            return AgentResult(
                task_id=task_id,
                session_id=None,
                content="",
                success=False,
                error="Claude Code SDK not installed. Run: pip install claude-code-sdk"
            )

        except Exception as e:
            # Handle other errors
            return AgentResult(
                task_id=task_id,
                session_id=session_id,
                content="",
                success=False,
                error=str(e)
            )

    def _build_prompt(self, task: str, prior_context: Optional[TaskContext]) -> str:
        """Build the full prompt including any prior context."""
        parts = []

        # Add prior context if available
        if prior_context:
            parts.append("## Prior Context")
            parts.append(f"Task ID: {prior_context.task_id}")
            parts.append(f"Status: {prior_context.status}")

            if prior_context.files_changed:
                parts.append(f"Files previously changed: {', '.join(prior_context.files_changed)}")

            if prior_context.decisions:
                parts.append("Previous decisions:")
                for decision in prior_context.decisions:
                    parts.append(f"  - {decision}")

            parts.append("")  # Blank line

        # Add the actual task
        parts.append(task)

        return "\n".join(parts)

    def _load_prior_context(self, task_id: str) -> Optional[TaskContext]:
        """Load prior context for a task if it exists."""
        return self.context_store.get_task(task_id)

    def _save_task_context(
        self,
        task_id: str,
        description: str,
        result: AgentResult
    ) -> None:
        """Save task context for cross-agent sharing."""
        from datetime import datetime

        context = TaskContext(
            task_id=task_id,
            agent=self.name,
            timestamp=datetime.now().isoformat(),
            description=description[:500],  # Truncate long descriptions
            files_changed=result.files_changed,
            decisions=result.decisions,
            findings=[],
            session_id=result.session_id,
            status="completed" if result.success else "failed"
        )

        self.context_store.save_task(context)

    async def handoff_to(
        self,
        target_agent: "BaseAgent",
        task: str,
        task_id: str
    ) -> AgentResult:
        """
        Hand off a task to another agent with shared context.

        The target agent will receive context from this agent's work.
        """
        # The target agent will automatically load context via task_id
        return await target_agent.run(
            task=task,
            task_id=task_id,
            resume_session=False  # Don't resume - this is a handoff
        )
