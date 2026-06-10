"""Deterministic agent wrapper for allowlisted command execution."""

from __future__ import annotations

import json
from pathlib import Path

from config import PROJECT_ROOT
from schemas.runner_schema import CommandResult
from tools.command_runner import RUNNER_MODES, run_command


class RunnerAgent:
    """Run only commands accepted by the deterministic command runner."""

    name = "Runner Agent"

    def run(
        self,
        input_data: dict[str, object] | str,
        cwd: str | Path | None = None,
        timeout: int = 120,
    ) -> str:
        """Execute a safe command and return a printable JSON result."""
        try:
            command: str
            selected_cwd = Path(cwd) if cwd is not None else PROJECT_ROOT
            selected_timeout = timeout

            if isinstance(input_data, str):
                command = input_data.strip()
            elif isinstance(input_data, dict):
                command = str(input_data.get("command") or "").strip()
                if input_data.get("cwd") is not None:
                    selected_cwd = Path(str(input_data["cwd"]))
                if input_data.get("timeout") is not None:
                    selected_timeout = int(input_data["timeout"])
            else:
                raise TypeError("Input must be a command string or a dict.")
            if not command:
                raise ValueError("No command provided.")

            result = run_command(
                command=command,
                cwd=selected_cwd,
                timeout=selected_timeout,
            )
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"{self.name} failed: {exc}"

    def run_review(
        self,
        input_data: dict[str, object] | str,
        cwd: str | Path | None = None,
        timeout: int = 120,
        mode: str = "safe",
    ) -> str:
        """Execute a command with risk assessment and return a CommandResult JSON."""
        try:
            command: str
            selected_cwd = Path(cwd) if cwd is not None else PROJECT_ROOT
            selected_timeout = timeout

            if isinstance(input_data, str):
                command = input_data.strip()
            elif isinstance(input_data, dict):
                command = str(input_data.get("command") or "").strip()
                if input_data.get("cwd") is not None:
                    selected_cwd = Path(str(input_data["cwd"]))
                if input_data.get("timeout") is not None:
                    selected_timeout = int(input_data["timeout"])
                if input_data.get("mode") is not None:
                    mode = str(input_data["mode"])
            else:
                raise TypeError("Input must be a command string or a dict.")
            if not command:
                raise ValueError("No command provided.")
            if mode not in RUNNER_MODES:
                raise ValueError(f"Mode must be one of {RUNNER_MODES}, got '{mode}'.")

            from tools.command_runner import plan_command, run_command_review

            if mode == "review":
                cmd_plan = plan_command(command)
                if cmd_plan.blocked_reason:
                    result = CommandResult(
                        command=command,
                        mode=mode,
                        executed=False,
                        risk_level=cmd_plan.risk_level,
                        blocked_reason=cmd_plan.blocked_reason,
                    )
                    return result.model_dump_json(indent=2)

            result = run_command_review(
                command=command,
                cwd=selected_cwd,
                timeout=selected_timeout,
                mode=mode,
            )
            return result.model_dump_json(indent=2)
        except Exception as exc:
            return json.dumps({"error": f"{self.name} failed: {exc}"})

    def run_sandbox(
        self,
        input_data: dict[str, object] | str,
        cwd: str | Path | None = None,
        timeout: int = 300,
    ) -> str:
        """Execute a command in sandbox mode with filesystem isolation."""
        try:
            command: str
            selected_cwd = Path(cwd) if cwd is not None else PROJECT_ROOT
            selected_timeout = timeout

            if isinstance(input_data, str):
                command = input_data.strip()
            elif isinstance(input_data, dict):
                command = str(input_data.get("command") or "").strip()
                if input_data.get("cwd") is not None:
                    selected_cwd = Path(str(input_data["cwd"]))
                if input_data.get("timeout") is not None:
                    selected_timeout = int(input_data["timeout"])
            else:
                raise TypeError("Input must be a command string or a dict.")
            if not command:
                raise ValueError("No command provided.")

            from tools.command_runner import run_command_sandbox

            result = run_command_sandbox(
                command=command,
                cwd=selected_cwd,
                timeout=selected_timeout,
            )
            return result.model_dump_json(indent=2)
        except Exception as exc:
            return json.dumps({"error": f"{self.name} failed: {exc}"})
