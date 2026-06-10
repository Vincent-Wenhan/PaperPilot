"""Deterministic agent wrapper for allowlisted command execution."""

from __future__ import annotations

import json
from pathlib import Path

from config import PROJECT_ROOT
from tools.command_runner import run_command


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
