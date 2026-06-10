"""Allowlist-based runner for lightweight repository inspection commands."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT, WORKSPACE_DIR


ALLOWED_COMMANDS = [
    ["python", "--version"],
    ["pip", "--version"],
    ["python", "train.py", "--help"],
    ["python", "main.py", "--help"],
    ["python", "eval.py", "--help"],
    ["python", "test.py", "--help"],
    ["python", "demo.py", "--help"],
    ["python", "examples/demo.py", "--help"],
]
FORBIDDEN_TOKENS = ("|", ";", ">", "<", "&&", "||")
FORBIDDEN_PATTERNS = (
    "sudo",
    "rm -rf",
    "mkfs",
    "shutdown",
    "reboot",
    "curl",
    "wget",
    "chmod 777",
    ":(){:|:&};:",
)
MAX_OUTPUT_CHARS = 4000


def is_safe_command(command: str) -> tuple[bool, str]:
    """Validate a command against shell controls and the exact allowlist."""
    if not command or not command.strip():
        return False, "Command cannot be empty."
    normalized = " ".join(command.lower().split())
    if any(pattern in normalized for pattern in FORBIDDEN_PATTERNS):
        return False, "Command contains explicitly prohibited dangerous operations."
    if any(token in command for token in FORBIDDEN_TOKENS):
        return False, "Command contains prohibited shell control characters."
    try:
        parts = shlex.split(command, posix=True)
    except ValueError as exc:
        return False, f"Command parsing failed: {exc}"
    if parts not in ALLOWED_COMMANDS:
        return False, "Command is not in the safety allowlist."
    return True, "Command passed safety check."


def _is_allowed_cwd(path: Path) -> bool:
    allowed_roots = (PROJECT_ROOT.resolve(), WORKSPACE_DIR.resolve())
    return any(path == root or path.is_relative_to(root) for root in allowed_roots)


def run_command(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
) -> dict[str, Any]:
    """Run one allowlisted command with a timeout and captured output."""
    safe, reason = is_safe_command(command)
    resolved_cwd = Path(cwd).expanduser().resolve()
    base_result: dict[str, Any] = {
        "command": command,
        "cwd": str(resolved_cwd),
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "success": False,
    }

    if not safe:
        base_result["stderr"] = reason
        return base_result
    if timeout <= 0:
        base_result["stderr"] = "timeout must be a positive integer."
        return base_result
    if not resolved_cwd.is_dir():
        base_result["stderr"] = f"Working directory does not exist: {resolved_cwd}"
        return base_result
    if not _is_allowed_cwd(resolved_cwd):
        base_result["stderr"] = "Working directory must be under the project root or workspace."
        return base_result

    try:
        result = subprocess.run(
            shlex.split(command, posix=True),
            cwd=resolved_cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        base_result["stderr"] = f"Timeout of {timeout} seconds exceeded."
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        base_result["stdout"] = stdout[-MAX_OUTPUT_CHARS:]
        return base_result
    except OSError as exc:
        base_result["stderr"] = f"Failed to start command: {exc}"
        return base_result

    return {
        **base_result,
        "returncode": result.returncode,
        "stdout": result.stdout[-MAX_OUTPUT_CHARS:],
        "stderr": result.stderr[-MAX_OUTPUT_CHARS:],
        "success": result.returncode == 0,
    }
