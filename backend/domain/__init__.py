"""Domain primitives shared across the workbench API."""

from backend.domain.run_state_machine import (
    ALLOWED_TRANSITIONS,
    InvalidRunTransition,
    RunStatus,
    assert_transition,
    is_terminal,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "InvalidRunTransition",
    "RunStatus",
    "assert_transition",
    "is_terminal",
]
