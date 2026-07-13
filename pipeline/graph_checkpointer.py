"""Shared LangGraph checkpointer for HITL resume.

Uses a SQLite-backed checkpointer so that graph state survives across
process restarts.  Falls back to ``InMemorySaver`` if the sqlite saver
cannot be initialised (e.g. on a read-only filesystem).
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock

from config import WORKSPACE_DIR
from langgraph.checkpoint.memory import InMemorySaver

_CHECKPOINT_PATH = WORKSPACE_DIR / "state" / "langgraph.sqlite"
_LOCK = RLock()
_CACHED: object | None = None


def get_shared_checkpointer() -> object:
    """Return the process-wide checkpointer.

    Returns a SqliteSaver when possible so that run state can be resumed
    after a restart.  Otherwise falls back to an in-memory saver so that
    HITL still works within a single process.
    """

    global _CACHED
    with _LOCK:
        if _CACHED is not None:
            return _CACHED
        _CACHED = _build_checkpointer()
        return _CACHED


def _build_checkpointer() -> object:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        _CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        saver = SqliteSaver.from_conn_string(str(_CHECKPOINT_PATH))
        saver.setup()
        return saver
    except Exception:
        return InMemorySaver()
