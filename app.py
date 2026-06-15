"""Streamlit user interface for PaperPilot."""

from __future__ import annotations

import streamlit as st

from main import run_paperpilot
from pipeline.analysis_cache import load_cached_analysis, save_cached_analysis
from tools.llm_client import LLMClientError
from ui.llm_config import (
    get_implementation_llm_client,
    get_llm_client,
    init_llm_sidebar_defaults,
    save_secrets,
)
from ui.productize import render_productize_mode
from ui.productize_helpers import (
    analysis_to_productize_paper as _analysis_to_productize_paper,
    assign_repo_urls as _assign_repo_urls,
    has_productize_context as _has_productize_context,
    run_analysis_for_productize as _run_analysis_for_productize,
)
from ui.reproduce import render_reproduce_mode
from ui.shared import build_generated_code_zip as _build_generated_code_zip


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
        init_llm_sidebar_defaults()

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

        if st.button("Save & Test Connection", use_container_width=True):
            save_secrets(
                api_key=st.session_state["llm_api_key"],
                base_url=st.session_state["llm_base_url"],
                model=st.session_state["llm_model"],
            )
            try:
                connection_result = get_llm_client().test_connection()
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
                connection_result = get_implementation_llm_client().test_connection()
            except LLMClientError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected implementation-model test failure: {exc}")
            else:
                st.success(
                    f"Implementation model connection succeeded: {connection_result}"
                )

        st.session_state.setdefault("enable_hitl", False)
        st.session_state["enable_hitl"] = st.toggle(
            "Enable HITL Confirmation",
            value=st.session_state["enable_hitl"],
            help="Review agent outputs before continuing.",
        )
        st.session_state.setdefault("enable_sync_hitl", False)
        if st.session_state["enable_hitl"]:
            st.session_state["enable_sync_hitl"] = st.toggle(
                "Sync HITL (LangGraph interrupt)",
                value=st.session_state["enable_sync_hitl"],
                help=(
                    "Pause the pipeline before downstream agents run. "
                    "Requires HITL Confirmation to be enabled."
                ),
            )
        else:
            st.session_state["enable_sync_hitl"] = False

    st.session_state.setdefault("productize_stage", "input")
    st.session_state.setdefault("productize_proposals", [])
    st.session_state.setdefault("productize_selected_proposal", None)
    st.session_state.setdefault("productize_result", None)
    st.session_state.setdefault("productize_papers", [])
    st.session_state.setdefault("productize_preferred_type", "auto")

    if mode == "Reproduce Paper":
        render_reproduce_mode()
    else:
        render_productize_mode()


if __name__ == "__main__":
    main()
