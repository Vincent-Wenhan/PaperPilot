"""Bridge planned reproduction commands into the Runner UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from schemas.runner_schema import CommandPlan
from tools.command_runner import is_safe_command, plan_command


def extract_runner_safe_commands(
    command_plans: list[dict[str, Any]],
    *,
    repo_path: str = "",
) -> list[dict[str, str]]:
    """Return safe, allowlisted commands from the reproduction plan."""
    cwd = Path(repo_path).expanduser().resolve() if repo_path else Path.cwd()
    safe_commands: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_plan in command_plans:
        command = str(raw_plan.get("command") or "").strip()
        if not command or command in seen:
            continue
        assessed = plan_command(command)
        allowed, _ = is_safe_command(command)
        if allowed and str(assessed.risk_level).lower() in {"low", "safe"}:
            seen.add(command)
            safe_commands.append(
                {
                    "command": command,
                    "purpose": str(raw_plan.get("purpose") or assessed.purpose or ""),
                    "cwd": str(cwd if repo_path else Path.cwd()),
                }
            )
    return safe_commands


def summarize_planned_commands(command_plans: list[dict[str, Any]]) -> dict[str, int]:
    """Count planned commands by risk level."""
    counts: dict[str, int] = {}
    for raw_plan in command_plans:
        plan = CommandPlan.model_validate(raw_plan)
        level = str(plan.risk_level or "unknown").lower()
        counts[level] = counts.get(level, 0) + 1
    return counts
