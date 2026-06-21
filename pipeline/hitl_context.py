"""Human-in-the-Loop context for pipeline confirmation stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class HITLStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    RETRY = "retry"


@dataclass
class HITLState:
    status: HITLStatus = HITLStatus.PENDING
    rejection_reason: str = ""
    correction: str = ""


@dataclass
class PipelineHITL:
    """Context object for human-in-the-loop confirmation points.

    Stores per-stage state and delegates the actual UI interaction to
    a callback (``on_confirm``), so the same class works with web UI, CLI, or tests.

    When ``None`` is passed instead of an instance, all confirmation points
    are skipped (backward-compatible).

  ``sync_mode`` enables LangGraph interrupt/resume so downstream agents do not
    run until the user confirms the paused stage.
    """

    stages: dict[str, HITLState] = field(default_factory=dict)
    on_confirm: Callable[[str, str, str], str | None] | None = None
    sync_mode: bool = False

    def request_confirmation(self, key: str, title: str, content: str) -> str:
        """Request user confirmation for a pipeline stage.

        Returns one of ``"confirm"``, ``"reject"``, ``"retry"``.

        If the stage was already confirmed/rejected in a previous call,
        returns the cached result immediately without invoking the callback.

        When ``on_confirm`` returns ``None`` (deferred mode), the stage
        stays PENDING and the default fallback ``"confirm"`` is returned
        so the caller can continue for now. The deferred result is resolved
        later via ``resolve_deferred()``.
        """
        state = self.stages.get(key)
        if state is not None and state.status != HITLStatus.PENDING:
            return state.status.value

        if state is None:
            state = HITLState()
            self.stages[key] = state

        if self.on_confirm is None:
            state.status = HITLStatus.CONFIRMED
            return "confirm"

        result = self.on_confirm(key, title, content)
        if result is not None:
            state.status = HITLStatus(result)
            return result
        # Deferred mode — on_confirm will resolve later
        return "confirm"

    def is_pending(self, key: str) -> bool:
        """Return whether a stage is still awaiting user action."""
        state = self.stages.get(key)
        return state is not None and state.status == HITLStatus.PENDING

    def record_rejection(self, key: str, reason: str = "") -> None:
        """Mark a stage as rejected."""
        state = self.stages.setdefault(key, HITLState())
        state.status = HITLStatus.REJECTED
        state.rejection_reason = reason

    def set_correction(self, key: str, text: str) -> None:
        """Store user-provided correction text for a retry."""
        state = self.stages.setdefault(key, HITLState())
        state.correction = text

    def get_correction(self, key: str) -> str:
        """Retrieve stored correction text for a stage."""
        state = self.stages.get(key)
        return state.correction if state else ""

    def get_rejection_reason(self, key: str) -> str:
        """Retrieve stored rejection reason for a stage."""
        state = self.stages.get(key)
        return state.rejection_reason if state else ""

    def resolve_all(self) -> None:
        """Resolve all pending deferred confirmations with user choices.

        After the UI has shown dialogs and collected button clicks,
        call this to update all stage statuses from session state.
        Web UI integrations can call this after collecting button clicks.
        """
        # No-op in base class; subclasses handle resolution
        pass

    def get_rejected_keys(self) -> list[str]:
        """Return keys of all stages that were rejected."""
        return [k for k, s in self.stages.items() if s.status == HITLStatus.REJECTED]

    def get_retry_keys(self) -> list[str]:
        """Return keys of all stages marked for retry."""
        return [k for k, s in self.stages.items() if s.status == HITLStatus.RETRY]
