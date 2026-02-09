"""Shared context store for cross-agent and cross-session state management."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class TaskContext:
    """Context for a specific task, shared between agents."""
    task_id: str
    agent: str
    timestamp: str
    description: str
    files_changed: list[str]
    decisions: list[str]
    findings: list[str]
    session_id: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed, blocked

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskContext":
        return cls(**data)


class ContextStore:
    """
    Persistent storage for agent context.

    Supports:
    - Task results for cross-agent handoffs
    - Session IDs for resuming conversations
    - Decision logs for audit trails
    """

    def __init__(self, store_path: str = "./context_store"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)

    # --- Task Context Management ---

    def save_task(self, context: TaskContext) -> None:
        """Save task context for cross-agent sharing."""
        path = self.store_path / f"task_{context.task_id}.json"
        path.write_text(json.dumps(context.to_dict(), indent=2))

        # Also update the task index
        self._update_task_index(context.task_id, context.status)

    def get_task(self, task_id: str) -> Optional[TaskContext]:
        """Retrieve task context by ID."""
        path = self.store_path / f"task_{task_id}.json"
        if path.exists():
            data = json.loads(path.read_text())
            return TaskContext.from_dict(data)
        return None

    def get_latest_task(self, agent: Optional[str] = None) -> Optional[TaskContext]:
        """Get the most recent task, optionally filtered by agent."""
        index = self._get_task_index()

        for task_id in reversed(list(index.keys())):
            task = self.get_task(task_id)
            if task and (agent is None or task.agent == agent):
                return task
        return None

    def _update_task_index(self, task_id: str, status: str) -> None:
        """Maintain an index of all tasks."""
        index_path = self.store_path / "task_index.json"
        index = self._get_task_index()
        index[task_id] = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        index_path.write_text(json.dumps(index, indent=2))

    def _get_task_index(self) -> dict:
        """Load the task index."""
        index_path = self.store_path / "task_index.json"
        if index_path.exists():
            return json.loads(index_path.read_text())
        return {}

    # --- Session Management ---

    def save_session(self, agent: str, session_id: str, task_id: Optional[str] = None) -> None:
        """Save session ID for resumption."""
        sessions_path = self.store_path / "sessions.json"
        sessions = self._get_sessions()

        sessions[agent] = {
            "session_id": session_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }

        sessions_path.write_text(json.dumps(sessions, indent=2))

    def get_session(self, agent: str) -> Optional[dict]:
        """Get session info for an agent."""
        sessions = self._get_sessions()
        return sessions.get(agent)

    def _get_sessions(self) -> dict:
        """Load all sessions."""
        sessions_path = self.store_path / "sessions.json"
        if sessions_path.exists():
            return json.loads(sessions_path.read_text())
        return {}

    # --- Decision Log ---

    def log_decision(self, agent: str, task_id: str, decision: str, reasoning: str) -> None:
        """Log a decision for audit trail."""
        log_path = self.store_path / "decisions.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "task_id": task_id,
            "decision": decision,
            "reasoning": reasoning
        }

        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_decisions(self, task_id: Optional[str] = None) -> list[dict]:
        """Retrieve decisions, optionally filtered by task."""
        log_path = self.store_path / "decisions.jsonl"

        if not log_path.exists():
            return []

        decisions = []
        with open(log_path, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if task_id is None or entry.get("task_id") == task_id:
                        decisions.append(entry)

        return decisions

    # --- Shared State ---

    def set_shared(self, key: str, value: Any) -> None:
        """Set a shared value accessible by all agents."""
        shared_path = self.store_path / "shared.json"
        shared = self._get_shared()
        shared[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        shared_path.write_text(json.dumps(shared, indent=2))

    def get_shared(self, key: str) -> Optional[Any]:
        """Get a shared value."""
        shared = self._get_shared()
        entry = shared.get(key)
        return entry.get("value") if entry else None

    def _get_shared(self) -> dict:
        """Load shared state."""
        shared_path = self.store_path / "shared.json"
        if shared_path.exists():
            return json.loads(shared_path.read_text())
        return {}

    # --- Utilities ---

    def clear(self) -> None:
        """Clear all stored context (use with caution)."""
        for path in self.store_path.glob("*.json"):
            path.unlink()
        for path in self.store_path.glob("*.jsonl"):
            path.unlink()
