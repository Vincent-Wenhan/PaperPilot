"""Runner and command review UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from agents import ExecutionDiagnosisAgent
from config import PROJECT_ROOT
from pipeline.runner_bridge import extract_runner_safe_commands, summarize_planned_commands
from pipeline.reproduce_renderers import render_execution_diagnosis
from tools.command_runner import plan_command, run_command_review
from ui.llm_config import get_llm_client
from ui.shared import RUNNER_ENTRYPOINTS

def _debug_command_failure(command_result: dict[str, Any]) -> str:
    """Ask Execution & Diagnosis Agent to interpret a command failure."""
    try:
        diagnosis = ExecutionDiagnosisAgent(get_llm_client()).run_structured(
            {
                "command_results": [command_result],
                "hardware": st.session_state.get(
                    "selected_hardware",
                    "Not provided",
                ),
                "gpu_info": st.session_state.get(
                    "selected_gpu_info",
                    "Not provided",
                ),
            }
        )
        return render_execution_diagnosis(diagnosis)
    except Exception as exc:
        return f"Execution & Diagnosis Agent failed: {exc}"


def execute_runner_command(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
) -> tuple[dict[str, Any], str]:
    """Run a command and automatically debug failures.

    Uses the runner mode from session state (safe/review).
    """
    runner_mode = st.session_state.get("runner_mode", "safe")
    model = run_command_review(
        command=command,
        cwd=cwd,
        timeout=timeout,
        mode=runner_mode,
    )
    command_result = model.model_dump(mode="json")
    command_result["cwd"] = str(Path(cwd).expanduser().resolve())
    command_result["returncode"] = command_result.get("exit_code")
    command_result["success"] = bool(
        command_result.get("executed")
        and command_result.get("exit_code") == 0
        and not command_result.get("blocked_reason")
    )

    # Only debug if the command actually executed (not blocked)
    diagnosis = ""
    if command_result.get("executed") and not command_result.get("success", False):
        diagnosis = _debug_command_failure(command_result)
    return command_result, diagnosis


def _candidate_help_commands(repo_path: str) -> list[str]:
    """Return allowlisted help commands whose entrypoints actually exist."""
    if not repo_path:
        return []
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return []
    return [
        f"python {relative_path} --help"
        for relative_path in RUNNER_ENTRYPOINTS
        if (root / relative_path).is_file()
    ]


def _show_command_result(command_result: dict[str, Any]) -> None:
    st.write(f"Command: `{command_result.get('command', '')}`")
    st.write(f"CWD: `{command_result.get('cwd', '')}`")
    st.write(f"Return code: `{command_result.get('returncode')}`")
    st.text_area(
        "stdout",
        value=command_result.get("stdout", ""),
        height=140,
        disabled=True,
        key="runner_stdout",
    )
    st.text_area(
        "stderr",
        value=command_result.get("stderr", ""),
        height=140,
        disabled=True,
        key="runner_stderr",
    )


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

    sandbox_dir = command_result.get("sandbox_dir")
    if sandbox_dir:
        st.markdown(f"**Sandbox Directory:** `{sandbox_dir}`")

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


def show_runner_section(result: dict[str, Any] | None) -> None:
    st.header("Runner")

    command_plans = list((result or {}).get("command_plans") or [])
    repo_path = str((result or {}).get("repo_path") or "")
    if command_plans:
        counts = summarize_planned_commands(command_plans)
        summary = ", ".join(f"{level}: {count}" for level, count in sorted(counts.items()))
        st.caption(f"Planned commands from reproduction plan — {summary}")
        safe_planned = extract_runner_safe_commands(command_plans, repo_path=repo_path)
        if safe_planned:
            st.subheader("Run Planned Safe Commands")
            st.caption(
                "These commands were classified as low-risk and match the Runner allowlist."
            )
            for index, planned in enumerate(safe_planned):
                label = planned["purpose"] or f"Run: {planned['command']}"
                if st.button(label, key=f"planned_safe_command_{index}"):
                    with st.spinner(f"Running safely: {planned['command']}"):
                        command_result, diagnosis = execute_runner_command(
                            planned["command"],
                            planned["cwd"],
                        )
                    st.session_state["runner_result"] = command_result
                    st.session_state["runner_debug_result"] = diagnosis
                    st.rerun()
        else:
            st.info(
                "No planned commands are both safe and allowlisted. "
                "Use Review mode for medium-risk commands or run help checks below."
            )

    runner_mode = st.selectbox(
        "Runner Mode",
        options=["safe", "review", "sandbox"],
        index=0,
        key="runner_mode_select",
        help="Safe: only allowlisted commands. Review: confirm before running. Sandbox: isolated temp directory.",
    )
    st.session_state["runner_mode"] = runner_mode

    mode_info = {
        "safe": "Only allowlisted commands (version checks, --help) are allowed.",
        "review": "Commands are assessed for risk. Blocked commands never execute. Other commands require your confirmation.",
        "sandbox": "Runs command in an isolated temp directory copy. Not auto-deleted. Useful for real experiment testing.",
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
        if st.button(label, key=f"runner_command_{index}"):
            if runner_mode == "review":
                cmd_plan = plan_command(command)
                st.session_state["pending_plan"] = cmd_plan
                st.session_state["pending_command"] = command
                st.session_state["pending_cwd"] = str(cwd)
                st.session_state["pending_key"] = f"confirm_{index}"
            else:
                with st.spinner(f"Running safely: {command}"):
                    command_result, diagnosis = execute_runner_command(
                        command,
                        cwd,
                    )
                st.session_state["runner_result"] = command_result
                st.session_state["runner_debug_result"] = diagnosis

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

