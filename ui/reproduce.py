"""Reproduce mode UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from config import MAIN_GOAL_DEBUG
from main import run_paperpilot
from ui.llm_config import get_llm_client
from ui.runner import show_runner_section
from ui.debug import show_debug_section
from ui.shared import (
    save_uploaded_pdf,
    show_downloads,
    show_outputs,
    show_pipeline_errors,
)

def render_reproduce_mode() -> None:
    """Render the original PaperPilot reproduction workflow."""
    st.title("PaperPilot 2.0: Reproduce Paper")
    st.caption(
        "Generate executable, inspectable reproduction plans from paper PDFs, "
        "with or without an existing code repository."
    )
    configured_client = get_llm_client()
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
            analysis_client = get_llm_client()
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
                        """Update progress. Safe to call from any thread."""
                        progress_lines.append(f"- {agent_name}...")
                        try:
                            progress_log.markdown(
                                "**Agent Progress**\n" + "\n".join(progress_lines)
                            )
                        except Exception:
                            pass  # Cross-thread call from LangGraph, no session context

                    paper_name = Path(uploaded_pdf.name).stem.replace(" ", "_")[:80]

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
                                paper_name=paper_name,
                                generate_code=generate_code,
                                implementation_model=st.session_state.get(
                                    "llm_implementation_model",
                                    "",
                                ),
                            )
                        except Exception as exc:
                            import traceback
                            tb = traceback.format_exc()
                            st.error(f"Pipeline execution failed: {exc}")
                            with st.expander("Error details"):
                                st.code(tb)
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
        show_pipeline_errors(
            result.get("errors", []),
            result.get("pipeline_status", "complete"),
        )
        show_outputs(result)
    elif st.session_state.get("debug_goal_selected"):
        st.info(
            "Debug mode does not run the main analysis pipeline. Please use the Debug section below."
        )
    else:
        st.info("Submit inputs and click Analyze to see results here.")

    show_downloads(result)
    show_runner_section(result)
    show_debug_section()


