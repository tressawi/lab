"""Audit hooks for logging agent activity."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


async def log_tool_use(
    tool_name: str,
    tool_input: dict,
    tool_result: Any,
    context: dict
) -> None:
    """
    Log tool usage for audit trail.

    This hook is called after each tool execution to maintain
    a complete record of agent actions.
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": context.get("agent_name", "unknown"),
        "task_id": context.get("task_id"),
        "tool": tool_name,
        "input": _sanitize_for_log(tool_input),
        "success": not isinstance(tool_result, Exception),
    }

    # Don't log full file contents to avoid huge logs
    if tool_name in ("Read", "Write", "Edit"):
        if "content" in log_entry["input"]:
            content = log_entry["input"]["content"]
            log_entry["input"]["content"] = f"<{len(content)} chars>"

    log_file = Path(context.get("store_path", "./context_store")) / "audit.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


async def log_agent_start(
    agent_name: str,
    task: str,
    context: dict
) -> None:
    """Log when an agent starts a task."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "agent_start",
        "agent": agent_name,
        "task_id": context.get("task_id"),
        "task_summary": task[:200] + "..." if len(task) > 200 else task,
    }

    log_file = Path(context.get("store_path", "./context_store")) / "audit.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


async def log_agent_complete(
    agent_name: str,
    result: str,
    context: dict
) -> None:
    """Log when an agent completes a task."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "agent_complete",
        "agent": agent_name,
        "task_id": context.get("task_id"),
        "result_summary": result[:200] + "..." if len(result) > 200 else result,
    }

    log_file = Path(context.get("store_path", "./context_store")) / "audit.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _sanitize_for_log(data: Any) -> Any:
    """Remove sensitive data from log entries."""
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = {"password", "secret", "token", "key", "credential", "auth"}

        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "<redacted>"
            else:
                sanitized[k] = _sanitize_for_log(v)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_for_log(item) for item in data]
    else:
        return data


def get_audit_hooks() -> dict[str, list[Callable]]:
    """
    Get hooks configuration for the agent.

    Returns a dict mapping hook points to handler functions.
    """
    return {
        "on_tool_use": [log_tool_use],
        "on_start": [log_agent_start],
        "on_complete": [log_agent_complete],
    }


def read_audit_log(
    store_path: str = "./context_store",
    task_id: str | None = None,
    agent: str | None = None,
    limit: int | None = None
) -> list[dict]:
    """
    Read and filter audit log entries.

    Args:
        store_path: Path to the context store
        task_id: Filter by task ID
        agent: Filter by agent name
        limit: Maximum number of entries to return

    Returns:
        List of audit log entries (most recent first)
    """
    log_file = Path(store_path) / "audit.jsonl"

    if not log_file.exists():
        return []

    entries = []
    with open(log_file, "r") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)

                # Apply filters
                if task_id and entry.get("task_id") != task_id:
                    continue
                if agent and entry.get("agent") != agent:
                    continue

                entries.append(entry)

    # Most recent first
    entries.reverse()

    if limit:
        entries = entries[:limit]

    return entries
