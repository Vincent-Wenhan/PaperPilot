"""Command-plan classification helpers that never execute commands."""

from __future__ import annotations

from typing import Any

from runtime.routing import route_command_plans
from schemas.runner_schema import CommandPlan, CommandResult
from tools.command_runner import plan_command


def classify_command_plans(
    command_plans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reassess commands with the deterministic runner policy."""
    classified: list[dict[str, Any]] = []
    for raw_plan in command_plans:
        source = CommandPlan.model_validate(raw_plan)
        assessed = plan_command(source.command)
        assessed.purpose = source.purpose
        classified.append(assessed.model_dump(mode="json"))
    return classified


def summarize_unexecuted_commands(
    command_plans: list[dict[str, Any]],
    route: str,
) -> list[dict[str, Any]]:
    """Represent planned commands as explicit not-executed results."""
    return [
        CommandResult(
            command=str(plan.get("command") or ""),
            mode=route,
            executed=False,
            risk_level=str(plan.get("risk_level") or "unknown"),
            blocked_reason=(
                str(plan.get("blocked_reason") or "")
                if plan.get("blocked_reason")
                else None
            ),
        ).model_dump(mode="json")
        for plan in command_plans
    ]


def build_pending_review(
    command_plans: list[dict[str, Any]],
    cwd: str,
) -> dict[str, Any] | None:
    """Build review metadata for the highest-risk planned command."""
    route = route_command_plans(command_plans)
    if route == "safe":
        return None
    candidates = [
        plan
        for plan in command_plans
        if (
            route == "blocked"
            and str(plan.get("risk_level") or "").lower() == "blocked"
        )
        or (
            route == "review"
            and str(plan.get("risk_level") or "").lower()
            in {"medium", "high", "review", "sandbox"}
        )
    ]
    selected = candidates[0] if candidates else command_plans[0]
    return {
        "command": str(selected.get("command") or ""),
        "purpose": str(selected.get("purpose") or ""),
        "risk_level": str(selected.get("risk_level") or "unknown"),
        "cwd": cwd,
        "blocked_reason": selected.get("blocked_reason"),
        "commands": list(command_plans),
    }
