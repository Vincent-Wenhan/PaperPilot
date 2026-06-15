"""Shared in-memory LangGraph checkpointer for HITL resume."""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

_SHARED_CHECKPOINTER = InMemorySaver()


def get_shared_checkpointer() -> InMemorySaver:
    """Return the process-wide checkpointer used for sync HITL resumes."""
    return _SHARED_CHECKPOINTER
