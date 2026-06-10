"""Streamlit user interface for PaperPilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

import streamlit as st

from agents import DebugAgent, RunnerAgent
from config import MAIN_GOAL_DEBUG, OUTPUTS_DIR, PROJECT_ROOT
from main import run_paperpilot
from tools.llm_client import LLMClient


UPLOADS_DIR = PROJECT_ROOT / "uploads"
OUTPUT_FILES = (
    ("reproduction_plan.md", "Download reproduction_plan.md", "text/markdown"),
    ("run.sh", "Download run.sh", "text/x-shellscript"),
    ("report.md", "Download report.md", "text/markdown"),
)
RUNNER_ENTRYPOINTS = (
    "train.py",
    "main.py",
    "eval.py",
    "test.py",
    "demo.py",
    "examples/demo.py",
)


def save_uploaded_pdf(uploaded_file: BinaryIO) -> Path:
    """Save one uploaded PDF under the project-local uploads directory."""
    original_name = Path(getattr(uploaded_file, "name", "paper.pdf")).name
    if Path(original_name).suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    data = uploaded_file.getvalue()
    if not data:
        raise ValueError("Uploaded PDF file is empty.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = "".join(
        character
        for character in Path(original_name).stem
        if character.isalnum() or character in {"-", "_"}
    )[:80]
    safe_stem = safe_stem or "paper"
    destination = UPLOADS_DIR / f"{uuid4().hex}_{safe_stem}.pdf"
    destination.write_bytes(data)
    return destination


def _show_pipeline_errors(errors: list[str]) -> None:
    if not errors:
        st.success("Analysis complete. No errors recorded.")
        return
    st.warning("Analysis completed, but some steps encountered issues:")
    for error in errors:
        st.error(error)


def _show_outputs(result: dict[str, Any]) -> None:
    st.header("Output")
    tabs = st.tabs(
        [
            "Paper Summary",
            "Method Breakdown",
            "Repository Analysis",
            "Environment Setup",
            "Experiment Plan",
            "run.sh",
            "report.md",
        ]
    )
    with tabs[0]:
        st.markdown(result.get("paper_info") or "Paper summary not yet generated.")
    with tabs[1]:
        st.markdown(result.get("method_info") or "Method breakdown not yet generated.")
    with tabs[2]:
        repo_path = result.get("repo_path")
        if repo_path:
            st.caption(f"Local repository: {repo_path}")
        st.markdown(result.get("repo_info") or "Repository analysis not yet generated.")
    with tabs[3]:
        st.markdown(result.get("env_plan") or "Environment setup not yet generated.")
    with tabs[4]:
        st.markdown(result.get("experiment_plan") or "Experiment plan not yet generated.")
    with tabs[5]:
        st.code(result.get("run_sh") or "run.sh not yet generated.", language="bash")
    with tabs[6]:
        st.markdown(result.get("report") or "report.md not yet generated.")


def _show_downloads() -> None:
    st.subheader("Download Output Files")
    columns = st.columns(len(OUTPUT_FILES))
    for column, (filename, label, mime) in zip(
        columns,
        OUTPUT_FILES,
        strict=True,
    ):
        path = OUTPUTS_DIR / filename
        with column:
            if path.is_file():
                st.download_button(
                    label=label,
                    data=path.read_bytes(),
                    file_name=filename,
                    mime=mime,
                    key=f"download_{filename}",
                )
            else:
                st.info(f"{filename} not yet generated.")


def _get_llm_client() -> LLMClient:
    """Build an LLMClient from sidebar session state (falling back to env vars)."""
    return LLMClient(
        api_key=st.session_state.get("llm_api_key"),
        base_url=st.session_state.get("llm_base_url"),
        model=st.session_state.get("llm_model"),
        mock_mode=st.session_state.get("llm_mock_mode", True),
    )


def _debug_command_failure(command_result: dict[str, Any]) -> str:
    """Ask Debug Agent to diagnose one failed deterministic command."""
    try:
        return DebugAgent(_get_llm_client()).run(
            {
                "command": command_result.get("command", ""),
                "cwd": command_result.get("cwd", ""),
                "returncode": command_result.get("returncode"),
                "stdout": command_result.get("stdout", ""),
                "stderr": command_result.get("stderr", ""),
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
    except Exception as exc:
        return f"Debug Agent execution failed: {exc}"


def execute_runner_command(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
) -> tuple[dict[str, Any], str]:
    """Run an allowlisted command and automatically debug failures."""
    raw_result = RunnerAgent().run(
        {
            "command": command,
            "cwd": str(cwd),
            "timeout": timeout,
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
        }
    diagnosis = ""
    if not command_result.get("success", False):
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


def _show_runner_section(result: dict[str, Any] | None) -> None:
    st.header("Runner")
    st.info(
        "The runner only executes lightweight safe commands. "
        "It will not run full training, download large datasets, "
        "or execute unknown shell scripts by default."
    )

    repo_path = str((result or {}).get("repo_path") or "")
    commands: list[tuple[str, str, Path]] = [
        ("Run python --version", "python --version", PROJECT_ROOT),
        ("Run pip --version", "pip --version", PROJECT_ROOT),
    ]
    commands.extend(
        (f"Run {command}", command, Path(repo_path))
        for command in _candidate_help_commands(repo_path)
    )

    for index, (label, command, cwd) in enumerate(commands):
        if st.button(label, key=f"runner_command_{index}"):
            with st.spinner(f"Running safely: {command}"):
                command_result, diagnosis = execute_runner_command(
                    command,
                    cwd,
                )
            st.session_state["runner_result"] = command_result
            st.session_state["runner_debug_result"] = diagnosis

    if repo_path and not _candidate_help_commands(repo_path):
        st.caption("No candidate entry points found for `--help` in this repository.")
    elif not repo_path:
        st.caption("After the paper and repository analysis complete, available `--help` buttons will appear here.")

    command_result = st.session_state.get("runner_result")
    if command_result:
        _show_command_result(command_result)
        if command_result.get("success"):
            st.success("Command executed successfully.")
        else:
            st.error("Command failed or was rejected by the security policy.")

    diagnosis = st.session_state.get("runner_debug_result")
    if diagnosis:
        st.subheader("Automatic Debug Result")
        st.markdown(diagnosis)


def _show_debug_section() -> None:
    st.header("Debug")
    debug_log = st.text_area(
        "Paste error logs",
        height=220,
        placeholder="Paste commands, stdout, stderr, and environment information here.",
    )
    if st.button("Analyze errors", key="analyze_debug"):
        if not debug_log.strip():
            st.error("Please paste error logs first.")
            return
        with st.spinner("Debug Agent is analyzing the error"):
            try:
                diagnosis = DebugAgent(_get_llm_client()).run(
                    {
                        "error_log": debug_log,
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
            except Exception as exc:
                diagnosis = f"Debug Agent execution failed: {exc}"
        st.session_state["debug_result"] = diagnosis

    diagnosis = st.session_state.get("debug_result")
    if diagnosis:
        st.subheader("Debug Agent Diagnosis")
        st.markdown(diagnosis)


def main() -> None:
    """Render the PaperPilot Streamlit application."""
    st.set_page_config(
        page_title="PaperPilot: Multi-Agent Paper Reproduction Assistant",
        layout="wide",
    )

    # ------------------------------------------------------------------
    # Sidebar: LLM API configuration
    # ------------------------------------------------------------------
    with st.sidebar:
        st.header("LLM Configuration")
        st.session_state.setdefault("llm_api_key", "")
        st.session_state.setdefault("llm_base_url", "https://api.openai.com/v1")
        st.session_state.setdefault("llm_model", "gpt-4o-mini")
        st.session_state.setdefault("llm_mock_mode", True)

        st.session_state["llm_api_key"] = st.text_input(
            "API Key",
            value=st.session_state["llm_api_key"],
            type="password",
            help="Leave empty to use the LLM_API_KEY environment variable.",
        )
        st.session_state["llm_base_url"] = st.text_input(
            "Base URL",
            value=st.session_state["llm_base_url"],
            help="OpenAI-compatible endpoint URL.",
        )
        st.session_state["llm_model"] = st.text_input(
            "Model",
            value=st.session_state["llm_model"],
        )
        st.session_state["llm_mock_mode"] = st.toggle(
            "Mock Mode",
            value=st.session_state["llm_mock_mode"],
            help="When enabled, LLM calls return fixed text (no API key needed).",
        )

    st.title("PaperPilot: Multi-Agent Paper Reproduction Assistant")
    st.caption("Generate executable, inspectable reproduction plans from paper PDFs and GitHub repositories.")

    st.header("Input")
    uploaded_pdf = st.file_uploader("Upload paper PDF", type=["pdf"])
    github_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/owner/repository",
    )

    hardware_column, gpu_column, goal_column = st.columns(3)
    with hardware_column:
        hardware = st.selectbox(
            "Hardware",
            ["CPU only", "Single GPU", "Multi GPU"],
        )
    with gpu_column:
        gpu_info = st.text_input("GPU model", placeholder="e.g. RTX 4090")
    with goal_column:
        goal = st.selectbox(
            "Goal",
            [
                "understand paper",
                "run official demo",
                "minimal training experiment",
                "reproduce main experiments",
                MAIN_GOAL_DEBUG,
            ],
        )

    st.session_state["selected_hardware"] = hardware
    st.session_state["selected_gpu_info"] = gpu_info

    if st.button("Analyze", type="primary", key="analyze_pipeline"):
        # --- Debug goal: skip pipeline, go straight to Debug section ---
        if goal == MAIN_GOAL_DEBUG:
            st.info(
                "Debug goal selected. Scroll to the Debug section at the bottom to paste logs for analysis."
            )
            st.session_state["debug_goal_selected"] = True
            st.session_state.pop("paperpilot_result", None)
        else:
            validation_errors: list[str] = []
            if uploaded_pdf is None:
                validation_errors.append("Please upload a paper PDF.")
            if not github_url.strip():
                validation_errors.append("GitHub URL cannot be empty.")

            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                try:
                    saved_pdf = save_uploaded_pdf(uploaded_pdf)
                except Exception as exc:
                    st.error(f"Failed to save PDF: {exc}")
                else:
                    st.session_state["uploaded_pdf_path"] = str(saved_pdf)
                    st.session_state.pop("debug_goal_selected", None)

                    # --- Real-time progress log ---
                    progress_container = st.container()
                    progress_log = progress_container.empty()
                    progress_lines: list[str] = []

                    def _on_progress(agent_name: str) -> None:
                        progress_lines.append(f"- {agent_name}...")
                        progress_log.markdown(
                            "**Agent Progress**\n" + "\n".join(progress_lines)
                        )

                    with st.status("Agent Status", expanded=True) as status:
                        _on_progress("Initializing pipeline")
                        try:
                            result = run_paperpilot(
                                pdf_path=str(saved_pdf),
                                github_url=github_url.strip(),
                                hardware=hardware,
                                gpu_info=gpu_info.strip(),
                                goal=goal,
                                llm_client=_get_llm_client(),
                                progress_callback=_on_progress,
                            )
                        except Exception as exc:
                            st.error(f"Pipeline execution failed: {exc}")
                            status.update(label="Analysis failed", state="error")
                        else:
                            st.session_state["paperpilot_result"] = result
                            _on_progress("Analysis complete")
                            status.update(label="Pipeline complete", state="complete")

    result = st.session_state.get("paperpilot_result")
    if result:
        _show_pipeline_errors(result.get("errors", []))
        _show_outputs(result)
    elif st.session_state.get("debug_goal_selected"):
        st.info(
            "Debug mode does not run the main analysis pipeline. Please use the Debug section below."
        )
    else:
        st.info("Submit inputs and click Analyze to see results here.")

    _show_downloads()
    _show_runner_section(result)
    _show_debug_section()


if __name__ == "__main__":
    main()
