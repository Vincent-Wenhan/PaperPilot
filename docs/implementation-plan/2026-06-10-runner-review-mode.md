# Runner Review Mode Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Each step is self-contained with complete code.

**Goal:** Add configurable runner modes (`safe` / `review`) with risk assessment and human-in-the-loop confirmation in the Streamlit UI.

**Architecture:**

```
command_runner.py          app.py (Runner section)
    │                           │
    ├─ assess_risk()            ├─ runner_mode toggle (safe/review)
    ├─ plan_command()           ├─ review mode: show plan + confirm button
    ├─ run_command() (unchanged)├─ standard: show CommandResult
    └─ run_command_review()     └─ both: use CommandPlan / CommandResult schemas
         │
         └─ RunnerAgent.run_review()
```

**Files to create/modify:**

| File | Action |
|---|---|
| `tools/command_runner.py` | Add `RUNNER_MODES`, `RiskLevel`, `assess_risk()`, `plan_command()`, `run_command_review()` |
| `schemas/runner_schema.py` | Already exists — verify/update |
| `app.py` | Add runner mode toggle, review mode UI, structured result display |
| `agents/runner_agent.py` | Add `run_review()` method |
| `tests/test_command_runner.py` | Create new test file for risk assessment |

---

### Task 1: Add `assess_risk()` and `plan_command()` to `command_runner.py`

**Files:** `tools/command_runner.py`

**Details:**

- Add constants: `RUNNER_MODES`, `RISK_PATTERNS`
- Add `assess_risk(command: str) -> tuple[str, str]` — returns `(risk_level, reason)`
- Add `plan_command(command: str) -> CommandPlan`
- Keep all existing functions unchanged

**Code to add** (after line 11, before `ALLOWED_COMMANDS`):

```python
RUNNER_MODES = ("safe", "review")
RiskLevel = str  # "low" | "medium" | "high" | "blocked"

RISK_PATTERNS: list[tuple[str, str, str]] = [
    # (risk_level, reason_prefix, regex_pattern)
    ("blocked", "Shell pipeline or download", r"(\bcurl\b.*\||\bwget\b.*\||\|\s*(bash|sh)\b)"),
    ("blocked", "Sudo command", r"\bsudo\b"),
    ("blocked", "Recursive delete or force remove", r"\brm\s+-rf\b"),
    ("blocked", "Permission modification", r"\bchmod\b"),
    ("blocked", "Ownership change", r"\bchown\b"),
    ("blocked", "Filesystem operation", r"\bmkfs\b"),
    ("blocked", "Shutdown or reboot", r"\bshutdown\b|\breboot\b"),
    ("blocked", "Fork bomb", r":\(\)\{"),
    ("high", "Training command", r"\bpython\s+\S*train\S*\.py\b"),
    ("high", "Download external resource", r"\bcurl\b|\bwget\b"),
    ("high", "Evaluate or test execution", r"\bpython\s+\S*eval\S*\.py\s(?!.*--help)"),
    ("medium", "Package installation", r"\bpip\s+install\b"),
    ("medium", "Conda environment operation", r"\bconda\s+(install|create|env)\b"),
    ("medium", "Python script execution (no --help)", r"\bpython\s+\S+\.py\b(?!.*--help)"),
    ("low", "Version check", r"\b(python|pip|conda|git|nvcc)\s+--version\b"),
    ("low", "Help flag", r"\bpython\s+\S+\.py\s+--help\b"),
    ("low", "List directory", r"\bls\b|\bdir\b"),
    ("low", "Read file", r"\bcat\b|\btype\b"),
]
```

**Code to add** after `is_safe_command()` (before `_is_allowed_cwd()`):

```python
import re

def assess_risk(command: str) -> tuple[str, str]:
    """Assess the risk level of a command based on pattern matching.

    Returns:
        Tuple of (risk_level: str, reason: str).
        Risk level is one of: "low", "medium", "high", "blocked".
    """
    if not command or not command.strip():
        return "blocked", "Empty command."
    normalized = " ".join(command.lower().split())
    # Check patterns in priority order (blocked first, then high, medium, low)
    for risk_level, reason_prefix, pattern in RISK_PATTERNS:
        if re.search(pattern, normalized):
            if risk_level == "low":
                return risk_level, f"Version check or help: {reason_prefix}"
            return risk_level, f"{reason_prefix} detected."
    # Default: unknown risk, treat as medium
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
```

**Add import** at top of file:

```python
from schemas.runner_schema import CommandPlan
```

**Verify** — after edit, run:

```bash
cd /c/Users/34217/Desktop/Study/2026Spring/Large\ AI\ Models/project/AIGC_PaperPilot && python -c "from tools.command_runner import assess_risk, plan_command, RUNNER_MODES; print('OK:', RUNNER_MODES)"
```

---

### Task 2: Add `run_command_review()` to `command_runner.py`

**Files:** `tools/command_runner.py`

**Details:**

- Add `run_command_review(command, cwd, timeout, mode="safe") -> CommandResult`
- In safe mode: runs only if allowlisted (same as `run_command`), returns CommandResult
- In review mode: runs if risk is not blocked, but always returns the plan alongside so the UI can decide
- Returns a `CommandResult` dict (not a raw dict)

**Code** to add after `run_command()`:

```python
def run_command_review(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
    mode: str = "safe",
) -> CommandResult:
    """Run a command with risk assessment and mode-aware execution.

    In safe mode, only allowlisted commands execute (same as run_command).
    In review mode, blocked commands are rejected; all others return a plan
    for the caller to confirm before execution.

    Returns a CommandResult pydantic model.
    """
    if mode not in RUNNER_MODES:
        return CommandResult(
            command=command,
            mode=mode,
            executed=False,
            blocked_reason=f"Unknown runner mode: {mode}. Use one of {RUNNER_MODES}.",
            risk_level="blocked",
        )

    cmd_plan = plan_command(command)

    # Blocked commands never execute regardless of mode
    if cmd_plan.blocked_reason:
        return CommandResult(
            command=command,
            mode=mode,
            executed=False,
            risk_level=cmd_plan.risk_level,
            blocked_reason=cmd_plan.blocked_reason,
        )

    # Safe mode: only allowlist
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
        # Execute
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

    # Review mode: command is allowed by risk (not blocked) — execute directly
    # Caller is responsible for showing the plan and getting confirmation.
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
```

**Also fix `run_command` return for timeout**: Currently `base_result` does not include `"timeout"` key but `run_command_review` expects it. Update the timeout branch in `run_command`:

In `run_command()`, in the `TimeoutExpired` handler, add `"timeout": True` to the returned dict:

```python
    except subprocess.TimeoutExpired as exc:
        base_result["stderr"] = f"Timeout of {timeout} seconds exceeded."
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        base_result["stdout"] = stdout[-MAX_OUTPUT_CHARS:]
        base_result["timeout"] = True    # <-- add this line
        return base_result
```

**Add import** at top of file:

```python
from schemas.runner_schema import CommandPlan, CommandResult
```

**Verify:**

```bash
cd /c/Users/34217/Desktop/Study/2026Spring/Large\ AI\ Models/project/AIGC_PaperPilot && python -c "
from tools.command_runner import run_command_review, plan_command
r = run_command_review('python --version', '.', mode='safe')
print('Safe mode:', r.model_dump())
r2 = run_command_review('rm -rf /', '.', mode='review')
print('Blocked:', r2.model_dump())
"
```

---

### Task 3: Add `run_review()` to `RunnerAgent`

**Files:** `agents/runner_agent.py`

**Details:**

- Add `run_review()` method that accepts mode parameter and returns a serialized `CommandResult`
- Keep existing `run()` unchanged for backward compat

**Code** to add after `run()` (at the end of the class, before the final except):

```python
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
            if mode not in ("safe", "review"):
                raise ValueError(f"Mode must be 'safe' or 'review', got '{mode}'.")

            from tools.command_runner import plan_command, run_command_review

            # If review mode, return the plan first (caller will confirm in UI)
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
```

**Add import** at top:

```python
from schemas.runner_schema import CommandResult
```

**Verify:**

```bash
cd /c/Users/34217/Desktop/Study/2026Spring/Large\ AI\ Models/project/AIGC_PaperPilot && python -c "
from agents.runner_agent import RunnerAgent
agent = RunnerAgent()
print(agent.run_review('python --version', mode='safe'))
print('---')
print(agent.run_review('rm -rf /', mode='review'))
"
```

---

### Task 4: Update `app.py` — Add runner mode toggle and review UI

**Files:** `app.py`

**Details:**

- In `_show_runner_section()`, add a `st.radio` or `st.selectbox` for runner mode (safe/review) at the top
- Store mode in `st.session_state["runner_mode"]`
- In review mode: when a command button is clicked, first show the CommandPlan (risk level, purpose, requires_confirmation), then a "Confirm & Run" button
- In safe mode: keep existing behavior exactly
- Refactor result display to use structured `CommandResult` format

**Changes to `_show_runner_section()`:**

Replace the current `_show_runner_section()` function with:

```python
def _show_runner_section(result: dict[str, Any] | None) -> None:
    st.header("Runner")

    # Runner mode toggle
    runner_mode = st.selectbox(
        "Runner Mode",
        options=["safe", "review"],
        index=0,
        key="runner_mode_select",
        help="Safe: only allowlisted commands execute. Review: you confirm before non-allowlisted commands run.",
    )
    st.session_state["runner_mode"] = runner_mode

    mode_info = {
        "safe": "Only allowlisted commands (version checks, --help) are allowed.",
        "review": "Commands are assessed for risk. Blocked commands never execute. Other commands require your confirmation.",
    }
    st.info(mode_info[runner_mode])

    repo_path = str((result or {}).get("repo_path") or "")
    commands: list[tuple[str, str, Path]] = [
        ("Run python --version", "python --version", PROJECT_ROOT),
        ("Run pip --version", "pip --version", PROJECT_ROOT),
    ]
    commands.extend(
        (f"Run {command}", command, Path(repo_path))
        for command in _candidate_help_commands(repo_path)
    )

    # Custom command input (for review mode especially)
    if runner_mode == "review":
        custom_command = st.text_input(
            "Custom command",
            placeholder="e.g. python demo.py --help",
            key="custom_runner_command",
        )
        if custom_command:
            commands.append(
                (f"Run: {custom_command}", custom_command, Path(repo_path) if repo_path else PROJECT_ROOT)
            )

    for index, (label, command, cwd) in enumerate(commands):
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(label, key=f"runner_command_{index}"):
                if runner_mode == "review":
                    # Plan first, show risk, wait for confirmation
                    from tools.command_runner import plan_command
                    cmd_plan = plan_command(command)
                    st.session_state["pending_plan"] = cmd_plan
                    st.session_state["pending_command"] = command
                    st.session_state["pending_cwd"] = str(cwd)
                    st.session_state["pending_key"] = f"confirm_{index}"
                else:
                    # Safe mode: execute directly
                    with st.spinner(f"Running safely: {command}"):
                        command_result, diagnosis = execute_runner_command(
                            command,
                            cwd,
                        )
                    st.session_state["runner_result"] = command_result
                    st.session_state["runner_debug_result"] = diagnosis

    # Review mode confirmation dialog
    pending_plan = st.session_state.get("pending_plan")
    if pending_plan and runner_mode == "review":
        st.divider()
        st.subheader("Command Review")
        _show_command_plan(pending_plan)
        col_confirm, col_cancel = st.columns([1, 1])
        with col_confirm:
            if st.button("Confirm & Run", key="confirm_run_review"):
                pending_cmd = st.session_state.get("pending_command", "")
                pending_cwd = st.session_state.get("pending_cwd", str(PROJECT_ROOT))
                with st.spinner(f"Running: {pending_cmd}"):
                    command_result, diagnosis = execute_runner_command(
                        pending_cmd,
                        pending_cwd,
                    )
                st.session_state["runner_result"] = command_result
                st.session_state["runner_debug_result"] = diagnosis
                st.session_state.pop("pending_plan", None)
                st.session_state.pop("pending_command", None)
                st.session_state.pop("pending_cwd", None)
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key="cancel_run_review"):
                st.session_state.pop("pending_plan", None)
                st.session_state.pop("pending_command", None)
                st.session_state.pop("pending_cwd", None)
                st.rerun()

    if repo_path and not _candidate_help_commands(repo_path):
        st.caption("No candidate entry points found for `--help` in this repository.")
    elif not repo_path:
        st.caption("After code generation or repository analysis completes, available `--help` buttons will appear here.")

    command_result = st.session_state.get("runner_result")
    if command_result:
        _show_command_result_structured(command_result)
        if command_result.get("success"):
            st.success("Command executed successfully.")
        else:
            st.error("Command failed or was rejected by the security policy.")

    diagnosis = st.session_state.get("runner_debug_result")
    if diagnosis:
        st.subheader("Automatic Debug Result")
        st.markdown(diagnosis)
```

**Add new helper functions** in `app.py` (after `_show_command_result` or replace it):

```python
def _show_command_plan(plan: Any) -> None:
    """Display a CommandPlan in a structured format."""
    risk_colors = {
        "low": "green",
        "medium": "orange",
        "high": "red",
        "blocked": "red",
    }
    color = risk_colors.get(plan.risk_level, "gray")
    st.markdown(f"**Command:** `{plan.command}`")
    st.markdown(f"**Risk Level:** :{color}[{plan.risk_level.upper()}]")
    if plan.purpose:
        st.markdown(f"**Purpose:** {plan.purpose}")
    if plan.requires_confirmation:
        st.warning("This command requires your confirmation before execution.")
    if plan.blocked_reason:
        st.error(f"**Blocked:** {plan.blocked_reason}")


def _show_command_result_structured(command_result: dict[str, Any]) -> None:
    """Display a command result dict in structured format (like CommandResult)."""
    risk_colors = {
        "low": "green",
        "medium": "orange",
        "high": "red",
        "blocked": "red",
        "unknown": "gray",
    }
    risk_level = command_result.get("risk_level", "unknown")
    color = risk_colors.get(risk_level, "gray")
    blocked = command_result.get("blocked_reason")

    st.markdown(f"**Command:** `{command_result.get('command', '')}`")
    st.markdown(f"**CWD:** `{command_result.get('cwd', '')}`")
    st.markdown(f"**Risk Level:** :{color}[{risk_level.upper()}]")
    st.markdown(f"**Exit Code:** `{command_result.get('returncode')}`")

    if blocked:
        st.error(f"**Blocked:** {blocked}")
    else:
        st.text_area(
            "stdout",
            value=command_result.get("stdout", ""),
            height=140,
            disabled=True,
            key="runner_stdout_structured",
        )
        st.text_area(
            "stderr",
            value=command_result.get("stderr", ""),
            height=140,
            disabled=True,
            key="runner_stderr_structured",
        )
```

**Update `execute_runner_command()`** to pass the runner mode through:

```python
def execute_runner_command(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
) -> tuple[dict[str, Any], str]:
    """Run a command and automatically debug failures.

    Uses the runner mode from session state (safe/review).
    """
    runner_mode = st.session_state.get("runner_mode", "safe")
    raw_result = RunnerAgent().run_review(
        {
            "command": command,
            "cwd": str(cwd),
            "timeout": timeout,
            "mode": runner_mode,
        }
    )
    try:
        command_result = json.loads(raw_result)
    except (TypeError, ValueError):
        command_result = {
            "command": command,
            "cwd": str(Path(cwd).resolve()),
            "returncode": None,
            "stdout": "",
            "stderr": raw_result,
            "success": False,
            "risk_level": "unknown",
        }

    # Only debug if the command actually executed (not blocked)
    diagnosis = ""
    if command_result.get("executed", True) and not command_result.get("success", False):
        if command_result.get("returncode") is not None:
            diagnosis = _debug_command_failure(command_result)
    return command_result, diagnosis
```

**Also update the Streamlit `info` text** at the top of `_show_runner_section` to be dynamic — already handled in the code above.

**Verify:** (syntax check only — Streamlit requires a browser)

```bash
cd /c/Users/34217/Desktop/Study/2026Spring/Large\ AI\ Models/project/AIGC_PaperPilot && python -c "
import ast
with open('app.py', 'r', encoding='utf-8') as f:
    source = f.read()
ast.parse(source)
print('app.py syntax OK')
"
```

---

### Task 5: Create `tests/test_command_runner.py`

**Files:** `tests/test_command_runner.py` (new file)

**Details:**

- Test `assess_risk()` for all risk levels
- Test `plan_command()` returns correct `CommandPlan`
- Test `run_command_review()` in both modes
- Test edge cases (empty, None, blocked patterns)

**Code:**

```python
"""Tests for the command runner risk assessment and review mode."""

from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

import pytest

from tools.command_runner import (
    RUNNER_MODES,
    assess_risk,
    is_safe_command,
    plan_command,
    run_command,
    run_command_review,
)


class TestAssessRisk:
    """Test risk level classification."""

    def test_low_version_check(self):
        level, reason = assess_risk("python --version")
        assert level == "low"
        assert "version" in reason.lower()

    def test_low_help_flag(self):
        level, reason = assess_risk("python train.py --help")
        assert level == "low"

    def test_medium_pip_install(self):
        level, reason = assess_risk("pip install torch")
        assert level == "medium"

    def test_medium_conda_create(self):
        level, reason = assess_risk("conda create -n test python=3.10")
        assert level == "medium"

    def test_medium_python_script(self):
        level, reason = assess_risk("python demo.py")
        assert level == "medium"

    def test_high_training(self):
        level, reason = assess_risk("python train.py --epochs 100")
        assert level == "high"

    def test_high_curl(self):
        level, reason = assess_risk("curl -O https://example.com/weights.pt")
        assert level == "high"

    def test_high_wget(self):
        level, reason = assess_risk("wget https://example.com/data.zip")
        assert level == "high"

    def test_blocked_sudo(self):
        level, reason = assess_risk("sudo apt-get install python")
        assert level == "blocked"

    def test_blocked_rm_rf(self):
        level, reason = assess_risk("rm -rf /some/path")
        assert level == "blocked"

    def test_blocked_curl_pipe_bash(self):
        level, reason = assess_risk("curl https://example.com/script.sh | bash")
        assert level == "blocked"

    def test_blocked_chmod(self):
        level, reason = assess_risk("chmod 777 /etc/passwd")
        assert level == "blocked"

    def test_blocked_chown(self):
        level, reason = assess_risk("chown root:root /etc/hosts")
        assert level == "blocked"

    def test_empty_command(self):
        level, reason = assess_risk("")
        assert level == "blocked"

    def test_whitespace_command(self):
        level, reason = assess_risk("   ")
        assert level == "blocked"

    def test_unknown_default_medium(self):
        level, reason = assess_risk("echo hello")
        assert level == "medium"


class TestPlanCommand:
    """Test CommandPlan generation."""

    def test_safe_low_risk(self):
        plan = plan_command("python --version")
        assert plan.risk_level == "low"
        assert plan.requires_confirmation is False
        assert plan.blocked_reason is None

    def test_blocked_has_reason(self):
        plan = plan_command("sudo rm -rf /")
        assert plan.risk_level == "blocked"
        assert plan.blocked_reason is not None

    def test_medium_requires_confirmation(self):
        plan = plan_command("pip install torch")
        assert plan.risk_level == "medium"
        assert plan.requires_confirmation is True

    def test_high_requires_confirmation(self):
        plan = plan_command("python train.py")
        assert plan.risk_level == "high"
        assert plan.requires_confirmation is True


class TestRunCommandReview:
    """Test the review-mode command runner."""

    @pytest.fixture
    def temp_dir(self):
        d = Path(mkdtemp(prefix="test_runner_"))
        yield d
        rmtree(d, ignore_errors=True)

    def test_invalid_mode(self, temp_dir):
        result = run_command_review("python --version", temp_dir, mode="invalid")
        assert result.executed is False
        assert "Unknown runner mode" in (result.blocked_reason or "")

    def test_safe_mode_allowlist(self, temp_dir):
        result = run_command_review("python --version", temp_dir, mode="safe")
        assert result.executed is True
        assert result.risk_level == "low"

    def test_safe_mode_rejects_non_allowlist(self, temp_dir):
        result = run_command_review("echo hello", temp_dir, mode="safe")
        assert result.executed is False
        assert result.blocked_reason is not None

    def test_review_mode_accepts_medium(self, temp_dir):
        # "echo hello" is medium risk (unknown pattern)
        result = run_command_review("echo hello", temp_dir, mode="review")
        # The command might fail (echo not a real program on Windows via shlex)
        # But it should be allowed to execute, not blocked
        assert result.executed is True or result.blocked_reason is None

    def test_review_mode_blocks_sudo(self, temp_dir):
        result = run_command_review("sudo rm -rf /", temp_dir, mode="review")
        assert result.executed is False
        assert result.blocked_reason is not None
        assert result.risk_level == "blocked"

    def test_runner_modes_constant(self):
        assert "safe" in RUNNER_MODES
        assert "review" in RUNNER_MODES
        assert len(RUNNER_MODES) == 2


class TestRunCommandBackwardCompat:
    """Verify existing run_command still works unchanged."""

    @pytest.fixture
    def temp_dir(self):
        d = Path(mkdtemp(prefix="test_runner_"))
        yield d
        rmtree(d, ignore_errors=True)

    def test_version_command(self, temp_dir):
        result = run_command("python --version", temp_dir)
        assert result["returncode"] == 0
        assert "Python" in result["stdout"]

    def test_is_safe_command_still_works(self):
        safe, _ = is_safe_command("python --version")
        assert safe is True
        safe, _ = is_safe_command("sudo rm -rf /")
        assert safe is False
```

**Verify:**

```bash
cd /c/Users/34217/Desktop/Study/2026Spring/Large\ AI\ Models/project/AIGC_PaperPilot && python -m pytest tests/test_command_runner.py -v
```

---

### Task 6: Verify `schemas/runner_schema.py` is up to date

**Files:** `schemas/runner_schema.py`

**Details:**

- Check the existing schema matches what the plan expects
- Currently has: `CommandPlan` (command, purpose, risk_level, requires_confirmation, blocked_reason) and `CommandResult` (command, mode, executed, exit_code, stdout, stderr, timeout, risk_level, blocked_reason)
- This matches the improvement plan spec exactly
- No changes needed

**Verify:**

```bash
cd /c/Users/34217/Desktop/Study/2026Spring/Large\ AI\ Models/project/AIGC_PaperPilot && python -c "
from schemas.runner_schema import CommandPlan, CommandResult
import json
p = CommandPlan(command='test', risk_level='low')
print('CommandPlan OK:', p.model_dump_json())
r = CommandResult(command='test', mode='safe')
print('CommandResult OK:', r.model_dump_json())
"
```

---

### Summary of All Changes

| Task | File | What |
|---|---|---|
| 1 | `tools/command_runner.py` | Add `RUNNER_MODES`, `assess_risk()`, `plan_command()`, risk patterns |
| 2 | `tools/command_runner.py` | Add `run_command_review()`, fix timeout key in `run_command()` |
| 3 | `agents/runner_agent.py` | Add `run_review()` method |
| 4 | `app.py` | Add runner mode toggle, review UI, structured result display, update `execute_runner_command()` |
| 5 | `tests/test_command_runner.py` | New file with tests for risk assessment, planning, review execution |
| 6 | `schemas/runner_schema.py` | Verify — no changes needed |

### Rollback Instructions

If any step fails, revert the changed file:

```bash
git checkout -- tools/command_runner.py agents/runner_agent.py app.py
rm tests/test_command_runner.py  # if created
```
