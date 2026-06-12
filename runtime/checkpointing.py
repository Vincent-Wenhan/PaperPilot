"""Optional LangGraph checkpoint configuration."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver


def build_checkpointer(enabled: bool) -> InMemorySaver | None:
    """Return an in-memory checkpointer only when explicitly enabled."""
    return InMemorySaver() if enabled else None


def build_graph_config(thread_id: str | None) -> dict[str, Any]:
    """Build the config required by checkpointed LangGraph executions."""
    if not thread_id:
        return {}
    return {"configurable": {"thread_id": thread_id}}
