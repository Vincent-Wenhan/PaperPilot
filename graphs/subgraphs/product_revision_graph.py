"""Shared helpers for bounded Productize revision loops."""

from __future__ import annotations

from typing import Any


def build_revision_record(
    state: dict[str, Any],
    route: str,
) -> dict[str, Any]:
    """Build one deterministic revision-history update."""
    evaluation = dict(state.get("evaluation") or {})
    revision = int(state.get("revision_count") or 0) + 1
    return {
        "revision": revision,
        "route": route,
        "suggestions": list(evaluation.get("revision_suggestions") or []),
    }
