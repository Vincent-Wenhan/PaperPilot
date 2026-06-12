"""Streamlit user interface for PaperPilot."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from agents import ExecutionDiagnosisAgent
from config import (
    LLM_BASE_URL,
    LLM_MOCK_MODE,
    LLM_MODEL,
    MAIN_GOAL_DEBUG,
    OUTPUTS_DIR,
    PROJECT_ROOT,
)
from main import run_paperpilot
from pipeline.productize_pipeline import run_productize_pipeline
from pipeline.reproduce_renderers import render_execution_diagnosis
from tools.command_runner import run_command_review
from tools.llm_client import LLMClient, LLMClientError


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


def _show_pipeline_errors(
    errors: list[str],
    pipeline_status: str = "complete",
) -> None:
    if not errors:
        st.success("Analysis complete. No errors recorded.")
        return
    if pipeline_status == "failed":
        st.error(
            "LLM analysis failed. The visible outputs are fallback placeholders, "
            "not a real reading of the paper."
        )
    else:
        st.warning("Analysis completed, but some steps encountered issues:")
    for error in errors:
        st.error(error)


def _build_generated_code_zip(repo_path: str, files: list[str]) -> bytes:
    """Build an in-memory ZIP from the validated generated-file manifest."""
    root = Path(repo_path).expanduser().resolve()
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for filename in files:
            path = (root / filename).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"Generated file is outside repository: {filename}") from exc
            if path.is_file():
                archive.write(path, arcname=filename)
        manifest = root / "CODE_AGENT_MANIFEST.json"
        if manifest.is_file():
            archive.write(manifest, arcname=manifest.name)
    return buffer.getvalue()


def _show_outputs(result: dict[str, Any]) -> None:
    st.header("Output")
    tabs = st.tabs(
        [
            "Paper Summary",
            "Method Breakdown",
            "Code / Repository",
            "Environment Setup",
            "Experiment Plan",
            "run.sh",
            "report.md",
        ]
    )
    with tabs[0]:
        paper_context = result.get("paper_context") or {}
        if paper_context:
            st.caption(
                "PDF context sent to Research Understanding Agent: "
                f"{paper_context.get('characters', 0):,} characters across "
                f"{paper_context.get('pages', 0)} page(s); "
                f"truncated: {paper_context.get('truncated', False)}"
            )
        st.markdown(result.get("paper_info") or "Paper summary not yet generated.")
    with tabs[1]:
        st.markdown(result.get("method_info") or "Method breakdown not yet generated.")
    with tabs[2]:
        repo_path = result.get("repo_path")
        repo_source = result.get("repo_source")
        generated_repo_path = result.get("generated_repo_path")
        if repo_source:
            st.caption(f"Code source: {repo_source}")
        if repo_path:
            st.caption(f"Local repository: {repo_path}")
        if generated_repo_path:
            st.caption(f"Generated reproduction repository: {generated_repo_path}")
        implementation_model = result.get("implementation_model")
        if implementation_model:
            st.caption(f"Implementation model: {implementation_model}")
        code_info = result.get("code_info")
        if code_info:
            st.subheader("Additional Code Context")
            st.markdown(code_info)
        generated_files = result.get("generated_files") or []
        if generated_repo_path and generated_files:
            st.subheader("Generated Code")
            st.download_button(
                label="Download generated reproduction code",
                data=_build_generated_code_zip(generated_repo_path, generated_files),
                file_name="paperpilot_generated_reproduction.zip",
                mime="application/zip",
                key="download_generated_reproduction",
            )
            generated_root = Path(generated_repo_path)
            for filename in generated_files:
                path = generated_root / filename
                if path.is_file():
                    with st.expander(filename):
                        language = "python" if path.suffix == ".py" else "text"
                        st.code(path.read_text(encoding="utf-8"), language=language)
        st.subheader("Repository Analysis")
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
    api_key = str(st.session_state.get("llm_api_key") or "").strip() or None
    base_url = str(st.session_state.get("llm_base_url") or "").strip() or None
    model = str(st.session_state.get("llm_model") or "").strip() or None
    return LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        mock_mode=st.session_state.get("llm_mock_mode", LLM_MOCK_MODE),
    )


def _get_implementation_llm_client() -> LLMClient:
    """Build the optional code-generation client from sidebar session state."""
    client = _get_llm_client()
    implementation_model = str(
        st.session_state.get("llm_implementation_model") or ""
    ).strip()
    if not implementation_model or implementation_model == client.model:
        return client
    return LLMClient(
        api_key=client.api_key,
        base_url=client.base_url,
        model=implementation_model,
        mock_mode=client.mock_mode,
    )


def _debug_command_failure(command_result: dict[str, Any]) -> str:
    """Ask Execution & Diagnosis Agent to interpret a command failure."""
    try:
        diagnosis = ExecutionDiagnosisAgent(_get_llm_client()).run_structured(
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


def _show_runner_section(result: dict[str, Any] | None) -> None:
    st.header("Runner")

    # Runner mode toggle
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
        with st.spinner("Execution & Diagnosis Agent is analyzing the error"):
            try:
                structured = ExecutionDiagnosisAgent(_get_llm_client()).run_structured(
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
                diagnosis = render_execution_diagnosis(structured)
            except Exception as exc:
                diagnosis = f"Execution & Diagnosis Agent failed: {exc}"
        st.session_state["debug_result"] = diagnosis

    diagnosis = st.session_state.get("debug_result")
    if diagnosis:
        st.subheader("Execution & Diagnosis")
        st.markdown(diagnosis)


def _has_productize_context(result: dict[str, Any] | None) -> bool:
    """Return whether a reproduction result can feed Productize Mode."""
    required = ("paper_info", "method_info")
    return bool(
        result
        and all(str(result.get(key) or "").strip() for key in required)
    )


def _assign_repo_urls(repo_text: str, paper_count: int) -> list[str]:
    """Map zero, one shared, or one-per-paper repository URLs."""
    if paper_count <= 0:
        return []
    urls = [line.strip() for line in repo_text.splitlines() if line.strip()]
    if not urls:
        return [""] * paper_count
    if len(urls) == 1:
        return urls * paper_count
    if len(urls) != paper_count:
        raise ValueError(
            "Provide one shared GitHub URL or exactly one URL per uploaded paper."
        )
    return urls


def _analysis_to_productize_paper(
    analysis: dict[str, Any],
    *,
    index: int,
    title: str = "",
) -> dict[str, Any]:
    """Normalize one reproduction result for multi-paper productization."""
    return {
        "paper_id": f"paper-{index}",
        "title": title or f"Paper {index}",
        "paper_info": analysis.get("paper_info", ""),
        "method_info": analysis.get("method_info", ""),
        "repo_info": analysis.get("repo_info", ""),
        "repo_path": analysis.get("repo_path", ""),
        "repo_source": analysis.get("repo_source", ""),
        "errors": analysis.get("errors", []),
    }


def _run_analysis_for_productize(
    pdf_path: str,
    github_url: str,
    hardware: str,
    gpu_info: str,
    llm_client: LLMClient,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    """Run the existing repository-analysis path for Productize context."""
    return run_paperpilot(
        pdf_path=pdf_path,
        github_url=github_url,
        hardware=hardware,
        gpu_info=gpu_info,
        goal="run official demo",
        llm_client=llm_client,
        progress_callback=progress_callback,
        generate_code=False,
    )


def _render_reproduce_mode() -> None:
    """Render the original PaperPilot reproduction workflow."""
    st.title("PaperPilot 2.0: Reproduce Paper")
    st.caption(
        "Generate executable, inspectable reproduction plans from paper PDFs, "
        "with or without an existing code repository."
    )
    configured_client = _get_llm_client()
    if configured_client.mock_mode:
        st.warning(
            "Mock Mode is enabled. The PDF will be parsed, but no LLM will read "
            "or analyze the paper."
        )
    elif not configured_client.api_key:
        st.warning(
            "No LLM API key is configured. Add one in the sidebar or through "
            "LLM_API_KEY before running a real paper analysis."
        )

    st.header("Input")
    uploaded_pdf = st.file_uploader(
        "Upload paper PDF",
        type=["pdf"],
        key="reproduce_pdf",
    )
    github_url = st.text_input(
        "GitHub URL (optional)",
        placeholder="https://github.com/owner/repository",
        help="Leave empty to continue with paper-only reproduction planning.",
        key="reproduce_github_url",
    )

    hardware_column, gpu_column, goal_column = st.columns(3)
    with hardware_column:
        hardware = st.selectbox(
            "Hardware",
            ["CPU only", "Single GPU", "Multi GPU"],
            key="reproduce_hardware",
        )
    with gpu_column:
        gpu_info = st.text_input(
            "GPU model",
            placeholder="e.g. RTX 4090",
            key="reproduce_gpu_info",
        )
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
            key="reproduce_goal",
        )

    user_idea = st.text_area(
        "Additional Notes (optional)",
        placeholder="Any specific focus areas, concerns, or ideas you want the analysis to consider...",
        key="reproduce_user_idea",
    )
    generate_code = st.checkbox(
        "Generate a minimal reproduction code project",
        value=True,
        help=(
            "Creates a separate, inspectable code project with a synthetic smoke "
            "test. Generated code is never executed automatically."
        ),
        key="reproduce_generate_code",
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
            analysis_client = _get_llm_client()
            if uploaded_pdf is None:
                validation_errors.append("Please upload a paper PDF.")
            if not analysis_client.mock_mode and not analysis_client.api_key:
                validation_errors.append(
                    "Configure an LLM API key for real analysis, or explicitly "
                    "enable Mock Mode for a pipeline-only demo."
                )
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
                                llm_client=analysis_client,
                                progress_callback=_on_progress,
                                user_idea=user_idea.strip(),
                                generate_code=generate_code,
                                implementation_model=st.session_state.get(
                                    "llm_implementation_model",
                                    "",
                                ),
                            )
                        except Exception as exc:
                            st.error(f"Pipeline execution failed: {exc}")
                            status.update(label="Analysis failed", state="error")
                        else:
                            st.session_state["paperpilot_result"] = result
                            pipeline_status = result.get("pipeline_status", "complete")
                            if pipeline_status == "failed":
                                _on_progress("Analysis failed; fallback outputs generated")
                                status.update(label="Pipeline failed", state="error")
                            elif pipeline_status == "degraded":
                                _on_progress("Analysis completed with issues")
                                status.update(
                                    label="Pipeline completed with issues",
                                    state="error",
                                )
                            elif pipeline_status == "mock":
                                _on_progress("Mock pipeline complete")
                                status.update(label="Mock pipeline complete", state="complete")
                            else:
                                _on_progress("Analysis complete")
                                status.update(label="Pipeline complete", state="complete")

    result = st.session_state.get("paperpilot_result")
    if result:
        _show_pipeline_errors(
            result.get("errors", []),
            result.get("pipeline_status", "complete"),
        )
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


def _show_productize_result(result: dict[str, Any]) -> None:
    errors = result.get("errors", [])
    if errors:
        if result.get("pipeline_status") == "failed":
            st.error(
                "LLM product analysis failed. The generated prototype uses "
                "fallback placeholder planning."
            )
        else:
            st.warning("The prototype was generated with partial-stage issues.")
        for error in errors:
            st.error(error)
    else:
        st.success("Product prototype generation completed.")

    tabs = st.tabs(
        [
            "Capability Cards",
            "Composition Plan",
            "Product Opportunities",
            "PRD & MVP",
            "Prototype Plan",
            "Generated Files",
            "Evaluation",
        ]
    )
    with tabs[0]:
        st.json(result.get("capability_cards") or [])
    with tabs[1]:
        st.json(result.get("composition_plan") or {})
    with tabs[2]:
        st.markdown(result.get("opportunities") or "Not generated.")
    with tabs[3]:
        st.caption(f"Template type: {result.get('template_type', 'file')}")
        st.markdown(result.get("product_spec") or "Not generated.")
    with tabs[4]:
        st.json(result.get("prototype_plan") or {})
        st.markdown(result.get("adapter_plan") or "Not generated.")
    with tabs[5]:
        scaffold = result.get("scaffold_result", {})
        output_dir = Path(scaffold.get("output_dir") or "")
        st.write(f"Output directory: `{output_dir}`")
        backup_dir = scaffold.get("backup_dir")
        if backup_dir:
            st.info(f"Previous product backed up to `{backup_dir}`.")
        for filename in scaffold.get("files", []):
            path = output_dir / filename
            if path.is_file():
                with st.expander(filename):
                    st.code(
                        path.read_text(encoding="utf-8"),
                        language="python" if path.suffix == ".py" else "markdown",
                    )
    with tabs[6]:
        inspection = result.get("inspection", {})
        st.json(inspection)
        st.json(result.get("evaluation") or {})
        st.markdown(result.get("test_report") or "Not generated.")

    st.subheader("How to Run Generated Product")
    st.code("cd generated_product\nstreamlit run app.py", language="bash")


def _render_productize_mode() -> None:
    """Render multi-paper Productize Mode with automatic analysis fallback."""
    st.title("PaperPilot 2.0: Productize Paper")
    st.caption(
        "Combine one or more paper capabilities into a theory-guided, "
        "mock-first Streamlit product prototype."
    )

    existing_analyses = st.session_state.get("paperpilot_results") or []
    existing_single = st.session_state.get("paperpilot_result")
    if not existing_analyses and _has_productize_context(existing_single):
        existing_analyses = [existing_single]
    if existing_analyses:
        st.success(
            f"Reusable analysis found for {len(existing_analyses)} paper(s). "
            "Upload new papers to replace it for this run."
        )
    else:
        st.info(
            "No reusable analysis is available. PaperPilot will automatically "
            "analyze each uploaded paper first."
        )

    st.header("Input")
    uploaded_pdfs = st.file_uploader(
        "Upload one or more paper PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="productize_pdf",
    )
    github_urls = st.text_area(
        "GitHub URL(s) (optional)",
        placeholder=(
            "Use one shared URL, or enter exactly one URL per paper on separate lines."
        ),
        help=(
            "Leave empty for paper-only product planning. Repositories are "
            "cloned and scanned only when explicitly provided."
        ),
        key="productize_github_url",
    )
    hardware_column, gpu_column = st.columns(2)
    with hardware_column:
        hardware = st.selectbox(
            "Hardware",
            ["CPU only", "Single GPU", "Multi GPU"],
            key="productize_hardware",
        )
    with gpu_column:
        gpu_info = st.text_input(
            "GPU model",
            placeholder="e.g. RTX 4090",
            key="productize_gpu_info",
        )
    target_user = st.text_input(
        "Target user",
        value="Machine learning learners",
        key="productize_target_user",
    )
    product_goal = st.text_area(
        "Product goal",
        value="Turn the paper technology into an interactive course demo.",
        key="productize_goal",
    )
    preferred_label = st.selectbox(
        "Preferred product type",
        ["Auto", "Image", "Text", "Video", "File"],
        key="productize_preferred_type",
    )
    user_idea = st.text_area(
        "Product Idea (optional)",
        placeholder="Describe any specific product idea you have in mind...",
        key="productize_user_idea",
    )

    if st.button(
        "Generate Product Prototype",
        type="primary",
        key="generate_product",
    ):
        progress_lines: list[str] = []
        progress_log = st.empty()

        def _on_progress(stage: str) -> None:
            progress_lines.append(f"- {stage}")
            progress_log.markdown(
                "**Productize Progress**\n" + "\n".join(progress_lines)
            )

        analyses: list[dict[str, Any]] = []
        titles: list[str] = []
        if uploaded_pdfs:
            try:
                assigned_urls = _assign_repo_urls(github_urls, len(uploaded_pdfs))
            except ValueError as exc:
                st.error(str(exc))
                return
            for index, (uploaded_pdf, assigned_url) in enumerate(
                zip(uploaded_pdfs, assigned_urls, strict=True),
                1,
            ):
                _on_progress(f"Analyzing paper {index}: {uploaded_pdf.name}")
                try:
                    saved_pdf = save_uploaded_pdf(uploaded_pdf)
                    analysis = _run_analysis_for_productize(
                        pdf_path=str(saved_pdf),
                        github_url=assigned_url,
                        hardware=hardware,
                        gpu_info=gpu_info.strip(),
                        llm_client=_get_llm_client(),
                        progress_callback=_on_progress,
                    )
                except Exception as exc:
                    st.error(f"Automatic analysis failed for {uploaded_pdf.name}: {exc}")
                    return
                analyses.append(analysis)
                titles.append(Path(uploaded_pdf.name).stem)
            st.session_state["paperpilot_results"] = analyses
            st.session_state["paperpilot_result"] = analyses[0]
        else:
            analyses = list(existing_analyses)
            titles = [f"Paper {index}" for index in range(1, len(analyses) + 1)]

        if not analyses:
            st.error("Upload at least one paper PDF or run Reproduce Mode first.")
            return
        incomplete = [
            index
            for index, analysis in enumerate(analyses, 1)
            if not _has_productize_context(analysis)
        ]
        if incomplete:
            st.error(
                "PaperPilot could not produce paper and method analysis for "
                f"paper(s): {', '.join(map(str, incomplete))}."
            )
            for analysis in analyses:
                _show_pipeline_errors(analysis.get("errors", []))
            return

        papers = [
            _analysis_to_productize_paper(
                analysis,
                index=index,
                title=titles[index - 1],
            )
            for index, analysis in enumerate(analyses, 1)
        ]
        primary = papers[0]
        primary_repo_path = next(
            (str(paper["repo_path"]) for paper in papers if paper["repo_path"]),
            "",
        )
        try:
            product_result = run_productize_pipeline(
                paper_info=str(primary["paper_info"]),
                method_info=str(primary["method_info"]),
                repo_info=str(primary["repo_info"]),
                repo_path=primary_repo_path,
                target_user=target_user.strip(),
                product_goal=product_goal.strip(),
                llm_client=_get_llm_client(),
                preferred_type=preferred_label.lower(),
                progress_callback=_on_progress,
                user_idea=user_idea.strip(),
                papers=papers,
            )
        except Exception as exc:
            st.error(f"Productize pipeline failed: {exc}")
        else:
            st.session_state["productize_result"] = product_result

    product_result = st.session_state.get("productize_result")
    if product_result:
        _show_productize_result(product_result)
    else:
        st.info("Generate a product prototype to view Productize outputs.")


def main() -> None:
    """Render the PaperPilot 2.0 Streamlit application."""
    st.set_page_config(
        page_title="PaperPilot 2.0: Reproduce and Productize",
        layout="wide",
    )

    with st.sidebar:
        st.header("PaperPilot 2.0")
        mode = st.radio(
            "Select Mode",
            ["Reproduce Paper", "Productize Paper"],
        )
        st.header("LLM Configuration")
        st.session_state.setdefault("llm_api_key", "")
        st.session_state.setdefault(
            "llm_base_url",
            LLM_BASE_URL or "https://api.openai.com/v1",
        )
        st.session_state.setdefault("llm_model", LLM_MODEL)
        st.session_state.setdefault("llm_implementation_model", "")
        st.session_state.setdefault("llm_mock_mode", LLM_MOCK_MODE)

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
        st.session_state["llm_implementation_model"] = st.text_input(
            "Implementation Model (optional)",
            value=st.session_state["llm_implementation_model"],
            help=(
                "Use a stronger model only for generated reproduction code. "
                "Leave empty to reuse the main model. Only use a dedicated model "
                "after Test Implementation Model succeeds."
            ),
        )
        if "mediem" in st.session_state["llm_implementation_model"].lower():
            st.error(
                "Implementation Model contains `mediem`. Check whether the exact "
                "provider model name should use `medium`."
            )
        st.session_state["llm_mock_mode"] = st.toggle(
            "Mock Mode",
            value=st.session_state["llm_mock_mode"],
            help="When enabled, LLM calls return fixed text (no API key needed).",
        )
        if st.button("Test LLM Connection", use_container_width=True):
            try:
                connection_result = _get_llm_client().test_connection()
            except LLMClientError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected LLM connection test failure: {exc}")
            else:
                st.success(f"LLM connection succeeded: {connection_result}")
        if st.session_state["llm_implementation_model"].strip() and st.button(
            "Test Implementation Model",
            use_container_width=True,
        ):
            try:
                connection_result = _get_implementation_llm_client().test_connection()
            except LLMClientError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected implementation-model test failure: {exc}")
            else:
                st.success(
                    f"Implementation model connection succeeded: {connection_result}"
                )

    if mode == "Reproduce Paper":
        _render_reproduce_mode()
    else:
        _render_productize_mode()


if __name__ == "__main__":
    main()
