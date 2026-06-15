"""Debug log analysis UI."""

from __future__ import annotations

from typing import Any

import streamlit as st

from agents import ExecutionDiagnosisAgent
from pipeline.reproduce_renderers import render_execution_diagnosis
from ui.llm_config import get_llm_client

def show_debug_section() -> None:
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
                structured = ExecutionDiagnosisAgent(get_llm_client()).run_structured(
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


