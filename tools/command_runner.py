"""Allowlist-based runner for lightweight repository inspection commands."""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from schemas.runner_schema import CommandPlan, CommandResult
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


RUNNER_MODES = ("safe", "review", "sandbox")

RISK_PATTERNS: list[tuple[str, str, str]] = [
    ("blocked", "Shell pipeline or download", r"(\bcurl\b.*\||\bwget\b.*\||\|\s*(bash|sh)\b)"),
    ("blocked", "Sudo command", r"\bsudo\b"),
    ("blocked", "Recursive delete or force remove", r"\brm\s+-rf\b"),
    ("blocked", "Permission modification", r"\bchmod\b"),
    ("blocked", "Ownership change", r"\bchown\b"),
    ("blocked", "Filesystem operation", r"\bmkfs\b"),
    ("blocked", "Shutdown or reboot", r"\bshutdown\b|\breboot\b"),
    ("blocked", "Fork bomb", r":\(\)\{"),
    ("low", "Version check", r"\b(python|pip|conda|git|nvcc)\s+--version\b"),
    ("low", "Help flag", r"\bpython\s+\S+\.py\s+--help\b"),
    ("high", "Training command", r"\bpython\s+\S*train\S*\.py\b"),
    ("high", "Download external resource", r"\bcurl\b|\bwget\b"),
    ("high", "Evaluate or test execution", r"\bpython\s+\S*eval\S*\.py\s(?!.*--help)"),
    ("medium", "Package installation", r"\bpip\s+install\b"),
    ("medium", "Conda environment operation", r"\bconda\s+(install|create|env)\b"),
    ("medium", "Python script execution (no --help)", r"\bpython\s+\S+\.py\b(?!.*--help)"),
    ("low", "List directory", r"\bls\b|\bdir\b"),
    ("low", "Read file", r"\bcat\b|\btype\b"),
]


def assess_risk(command: str) -> tuple[str, str]:
    """Assess the risk level of a command based on pattern matching.

    Returns:
        Tuple of (risk_level: str, reason: str).
        Risk level is one of: "low", "medium", "high", "blocked".
    """
    if not command or not command.strip():
        return "blocked", "Empty command."
    normalized = " ".join(command.lower().split())
    for risk_level, reason_prefix, pattern in RISK_PATTERNS:
        if re.search(pattern, normalized):
            if risk_level == "low":
                return risk_level, f"Version check or help: {reason_prefix}"
            return risk_level, f"{reason_prefix} detected."
    return "medium", "Command does not match known safe patterns."


def plan_command(command: str) -> CommandPlan:
    """Create a CommandPlan by assessing risk and checking the allowlist."""
    safe, _ = is_safe_command(command)
    risk_level, reason = assess_risk(command)
    return CommandPlan(
        command=command,
        risk_level=risk_level,
        requires_confirmation=risk_level in ("medium", "high"),
        blocked_reason=reason if risk_level == "blocked" else None,
    )


def run_command_review(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
    mode: str = "safe",
) -> CommandResult:
    """Run a command with risk assessment and mode-aware execution.

    In safe mode, only allowlisted commands execute (same as run_command).
    In review mode, blocked commands are rejected; all others execute.
    """
    if mode == "sandbox":
        return run_command_sandbox(command, cwd, timeout)

    if mode not in RUNNER_MODES:
        return CommandResult(
            command=command,
            mode=mode,
            executed=False,
            blocked_reason=f"Unknown runner mode: {mode}. Use one of {RUNNER_MODES}.",
            risk_level="blocked",
        )

    cmd_plan = plan_command(command)

    if cmd_plan.blocked_reason:
        return CommandResult(
            command=command,
            mode=mode,
            executed=False,
            risk_level=cmd_plan.risk_level,
            blocked_reason=cmd_plan.blocked_reason,
        )

    if mode == "safe":
        safe, reason = is_safe_command(command)
        if not safe:
            return CommandResult(
                command=command,
                mode=mode,
                executed=False,
                risk_level=cmd_plan.risk_level,
                blocked_reason=reason,
            )

    raw = run_command(command, cwd, timeout)
    return CommandResult(
        command=raw.get("command", command),
        mode=mode,
        executed=True,
        exit_code=raw.get("returncode"),
        stdout=raw.get("stdout", ""),
        stderr=raw.get("stderr", ""),
        timeout=raw.get("timeout", False),
        risk_level=cmd_plan.risk_level,
    )


def _is_allowed_cwd(path: Path) -> bool:
    allowed_roots = (PROJECT_ROOT.resolve(), WORKSPACE_DIR.resolve())
    return any(path == root or path.is_relative_to(root) for root in allowed_roots)


def _copytree(src: Path, dst: Path) -> None:
    """Copy a directory tree skipping .git, __pycache__, and venv dirs."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in (".git", "__pycache__", ".venv", "venv", "node_modules"):
            continue
        target = dst / item.name
        if item.is_dir():
            try:
                _copytree(item, target)
            except OSError:
                pass
        else:
            try:
                shutil.copy2(item, target)
            except OSError:
                # Fallback to basic copy if metadata copy fails
                shutil.copy(item, target)


def run_command_sandbox(
    command: str,
    cwd: str | Path,
    timeout: int = 300,
) -> CommandResult:
    """Run a command in a temporary sandbox directory.

    Copies the content of *cwd* into a temp directory under ``workspace/sandboxes/``,
    executes the command there, and does NOT auto-delete the sandbox.
    """
    resolved_cwd = Path(cwd).expanduser().resolve()
    if not resolved_cwd.is_dir():
        return CommandResult(
            command=command,
            mode="sandbox",
            executed=False,
            risk_level="blocked",
            blocked_reason=f"Source directory does not exist: {resolved_cwd}",
        )

    risk_level, reason = assess_risk(command)
    if risk_level == "blocked":
        return CommandResult(
            command=command,
            mode="sandbox",
            executed=False,
            risk_level=risk_level,
            blocked_reason=reason,
        )

    sandbox_root = WORKSPACE_DIR / "sandboxes"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    sandbox_dir = Path(tempfile.mkdtemp(prefix="sandbox_", dir=str(sandbox_root)))

    try:
        _copytree(resolved_cwd, sandbox_dir)

        result = subprocess.run(
            shlex.split(command, posix=True),
            cwd=str(sandbox_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            command=command,
            mode="sandbox",
            executed=True,
            exit_code=result.returncode,
            stdout=result.stdout[-MAX_OUTPUT_CHARS:],
            stderr=result.stderr[-MAX_OUTPUT_CHARS:],
            timeout=False,
            risk_level=risk_level,
            sandbox_dir=str(sandbox_dir),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        return CommandResult(
            command=command,
            mode="sandbox",
            executed=True,
            exit_code=None,
            stdout=stdout[-MAX_OUTPUT_CHARS:],
            stderr="Timeout exceeded.",
            timeout=True,
            risk_level=risk_level,
            sandbox_dir=str(sandbox_dir),
        )
    except OSError as exc:
        return CommandResult(
            command=command,
            mode="sandbox",
            executed=False,
            risk_level=risk_level,
            blocked_reason=f"Sandbox execution failed: {exc}",
            sandbox_dir=str(sandbox_dir),
        )


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
        base_result["timeout"] = True
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


def run_sandbox_verification(
    repo_path: str,
    smoke_test_command: str = "python main.py --smoke-test",
) -> dict[str, Any]:
    """Run generated code through a series of verification checks.

    Copies the repo into a sandbox temp directory and runs:
    1. pip install -r requirements.txt
    2. python import check for each .py file
    3. python main.py --help (safe gate)
    4. smoke test command

    Returns a dict with ``passed``, ``results`` list, and ``sandbox_dir``.
    """
    from pathlib import Path

    resolved = Path(repo_path).expanduser().resolve()
    if not resolved.is_dir():
        return {
            "passed": False,
            "results": [],
            "sandbox_dir": "",
            "error": f"Repo path does not exist: {repo_path}",
        }

    sandbox_root = WORKSPACE_DIR / "sandboxes"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    sandbox_dir = Path(tempfile.mkdtemp(prefix="verify_", dir=str(sandbox_root)))

    try:
        _copytree(resolved, sandbox_dir)
    except OSError as exc:
        return {
            "passed": False,
            "results": [],
            "sandbox_dir": str(sandbox_dir),
            "error": f"Failed to copy repo to sandbox: {exc}",
        }

    results: list[dict[str, Any]] = []

    # 1. pip install
    pip_result = run_command_sandbox("pip install -r requirements.txt", str(sandbox_dir), timeout=300)
    results.append({
        "step": "pip install",
        "command": "pip install -r requirements.txt",
        "exit_code": pip_result.exit_code,
        "stdout": pip_result.stdout,
        "stderr": pip_result.stderr,
        "passed": pip_result.executed and pip_result.exit_code == 0,
    })

    # 2. import check for each .py file
    py_files = sorted(resolved.rglob("*.py"))
    for py_file in py_files:
        rel = py_file.relative_to(resolved)
        module = str(rel.with_suffix("")).replace("\\", "/").replace("/", ".")
        # Skip __init__ and test files for import check
        if module.endswith("__init__") or "test" in module.lower():
            continue
        check_cmd = f"python -c \"import {module}\""
        try:
            check_result = subprocess.run(
                ["python", "-c", f"import {module}"],
                cwd=str(sandbox_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            results.append({
                "step": "import_check",
                "command": check_cmd,
                "exit_code": check_result.returncode,
                "stdout": check_result.stdout[-MAX_OUTPUT_CHARS:],
                "stderr": check_result.stderr[-MAX_OUTPUT_CHARS:],
                "passed": check_result.returncode == 0,
            })
        except subprocess.TimeoutExpired:
            results.append({
                "step": "import_check",
                "command": check_cmd,
                "exit_code": None,
                "stdout": "",
                "stderr": "Timeout exceeded.",
                "timeout": True,
                "passed": False,
            })

    # 3. python main.py --help
    help_cmd = "python main.py --help"
    help_result = run_command_sandbox(help_cmd, str(sandbox_dir), timeout=60)
    results.append({
        "step": "help_check",
        "command": help_cmd,
        "exit_code": help_result.exit_code,
        "stdout": help_result.stdout,
        "stderr": help_result.stderr,
        "passed": help_result.executed and help_result.exit_code == 0,
    })

    # 4. smoke test
    smoke_result = run_command_sandbox(smoke_test_command, str(sandbox_dir), timeout=120)
    results.append({
        "step": "smoke_test",
        "command": smoke_test_command,
        "exit_code": smoke_result.exit_code,
        "stdout": smoke_result.stdout,
        "stderr": smoke_result.stderr,
        "passed": smoke_result.executed and smoke_result.exit_code == 0,
    })

    all_passed = all(r.get("passed", False) for r in results)
    return {
        "passed": all_passed,
        "results": results,
        "sandbox_dir": str(sandbox_dir),
    }
