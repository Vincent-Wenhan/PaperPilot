"""Durable run state machine and transition helpers."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.QUEUED: {
        RunStatus.RUNNING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    },
    RunStatus.RUNNING: {
        RunStatus.WAITING_INPUT,
        RunStatus.WAITING_APPROVAL,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING_INPUT: {
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING_APPROVAL: {
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.FAILED: set(),
    RunStatus.SUCCEEDED: set(),
    RunStatus.CANCELLED: set(),
}


class InvalidRunTransition(ValueError):
    """Raised when a run transitions to an invalid state."""


def assert_transition(current: str, target: str) -> None:
    source = RunStatus(current)
    destination = RunStatus(target)
    if destination not in ALLOWED_TRANSITIONS[source]:
        raise InvalidRunTransition(
            f"Invalid transition: {source.value} -> {destination.value}"
        )


def is_terminal(status: str) -> bool:
    return status in {
        RunStatus.SUCCEEDED.value,
        RunStatus.FAILED.value,
        RunStatus.CANCELLED.value,
    }
