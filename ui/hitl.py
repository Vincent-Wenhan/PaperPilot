"""Streamlit HITL helpers for PaperPilot."""

from __future__ import annotations

from typing import Any

import streamlit as st

from main import run_paperpilot
from pipeline.hitl_context import HITLStatus, PipelineHITL
from pipeline.hitl_retry import rerun_reproduce_stage
from pipeline.output_paths import resolve_output_dir
from pipeline.productize_pipeline import execute_proposal, generate_proposals
from schemas.product_schema import ProductProposal
from ui.llm_config import get_llm_client


def _markdown_or_fallback(content: str, fallback: str) -> None:
    if content.strip():
        st.markdown(content)
    else:
        st.info(fallback)


def _rebuild_reproduce_hitl_content(result: dict[str, Any]) -> str:
    content = str(result.get("hitl_content") or "").strip()
    if content:
        return content

    stage = str(result.get("hitl_stage") or "")
    node = str(result.get("hitl_interrupt_node") or "")
    try:
        if stage == "research" or node == "research_understanding":
            from pipeline.reproduce_renderers import (
                render_method_breakdown,
                render_research_summary,
            )
            from schemas.reproduction_schema import PaperUnderstanding

            research = PaperUnderstanding.model_validate(
                result.get("research_understanding") or {}
            )
            content = (
                f"{render_research_summary(research)}\n\n"
                f"{render_method_breakdown(research)}"
            ).strip()
        elif stage == "experiment" or node == "reproduction_planner":
            from pipeline.reproduce_renderers import (
                render_environment_plan,
                render_experiment_plan,
            )
            from schemas.reproduction_schema import ReproductionPlan

            plan = ReproductionPlan.model_validate(
                result.get("reproduction_plan") or {}
            )
            content = (
                f"{render_environment_plan(plan)}\n\n"
                f"{render_experiment_plan(plan)}"
            ).strip()
    except Exception:
        content = ""

    if not content:
        content = (
            f"{result.get('paper_info', '')}\n\n"
            f"{result.get('method_info', '')}\n\n"
            f"{result.get('env_plan', '')}\n\n"
            f"{result.get('experiment_plan', '')}"
        ).strip()
    if content:
        result["hitl_content"] = content
    return content


def _rebuild_productize_hitl_content(result: dict[str, Any]) -> str:
    content = str(result.get("hitl_content") or "").strip()
    if content:
        return content

    stage = str(result.get("hitl_stage") or "")
    try:
        if stage == "capabilities":
            from pipeline.hitl_renderers import render_capability_cards
            from schemas.composition_schema import ResearchSynthesis

            synthesis = ResearchSynthesis.model_validate(
                result.get("research_synthesis") or {}
            )
            content = render_capability_cards(synthesis).strip()
        elif stage == "prototype":
            from pipeline.productize_pipeline import _prototype_plan_to_markdown
            from schemas.product_schema import PrototypePlan

            prototype = PrototypePlan.model_validate(result.get("prototype_plan") or {})
            content = _prototype_plan_to_markdown(prototype).strip()
    except Exception:
        content = ""

    if content:
        result["hitl_content"] = content
    return content


class StreamlitHITL(PipelineHITL):
    """Deferred or sync HITL for Streamlit."""

    def __init__(self, *, sync_mode: bool = False) -> None:
        super().__init__(sync_mode=sync_mode)
        self._pending_keys: list[str] = []

    def on_confirm(self, key: str, title: str, content: str) -> str | None:
        if self.sync_mode:
            return None
        if key not in self._pending_keys:
            self._pending_keys.append(key)
        st.session_state[f"hitl_pending_{key}"] = True
        st.session_state[f"hitl_title_{key}"] = title
        st.session_state[f"hitl_content_{key}"] = content
        return None

    def is_deferred_pending(self, key: str) -> bool:
        return self.is_pending(key) and st.session_state.get(f"hitl_pending_{key}", False)

    def render_pending_dialogs(self) -> bool:
        shown_any = False
        for key in list(self._pending_keys):
            if not self.is_deferred_pending(key):
                continue
            title = st.session_state.get(f"hitl_title_{key}", "Confirmation Required")
            content = st.session_state.get(f"hitl_content_{key}", "")
            st.markdown(f"#### {title}")
            st.markdown(content)
            feedback = st.text_area(
                "Feedback (optional, for retry)",
                key=f"hitl_feedback_{key}",
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Confirm", key=f"hitl_btn_confirm_{key}", type="primary"):
                    st.session_state[f"hitl_pending_{key}"] = False
                    self.stages[key].status = HITLStatus.CONFIRMED
                    st.rerun()
            with col2:
                if st.button("Retry with feedback", key=f"hitl_btn_retry_{key}"):
                    st.session_state[f"hitl_pending_{key}"] = False
                    self.set_correction(key, feedback)
                    self.stages[key].status = HITLStatus.RETRY
                    st.rerun()
            with col3:
                if st.button("Reject & Continue", key=f"hitl_btn_reject_{key}"):
                    st.session_state[f"hitl_pending_{key}"] = False
                    self.record_rejection(key, "User rejected this stage.")
                    st.rerun()
            shown_any = True
        return shown_any


def store_hitl_resume_context(
    *,
    pdf_path: str,
    github_url: str,
    hardware: str,
    gpu_info: str,
    goal: str,
    user_idea: str,
    paper_name: str,
    generate_code: bool,
    implementation_model: str,
    result: dict[str, Any],
) -> None:
    st.session_state["hitl_resume_context"] = {
        "pdf_path": pdf_path,
        "github_url": github_url,
        "hardware": hardware,
        "gpu_info": gpu_info,
        "goal": goal,
        "user_idea": user_idea,
        "paper_name": paper_name,
        "generate_code": generate_code,
        "implementation_model": implementation_model,
        "thread_id": result.get("hitl_thread_id"),
        "stage": result.get("hitl_stage"),
    }


def resume_hitl_pipeline(action: str, correction: str = "") -> dict[str, Any]:
    ctx = st.session_state["hitl_resume_context"]
    hitl = StreamlitHITL(sync_mode=st.session_state.get("enable_sync_hitl", False))
    return run_paperpilot(
        pdf_path=ctx["pdf_path"],
        github_url=ctx["github_url"],
        hardware=ctx["hardware"],
        gpu_info=ctx["gpu_info"],
        goal=ctx["goal"],
        llm_client=get_llm_client(),
        user_idea=ctx["user_idea"],
        paper_name=ctx["paper_name"],
        hitl=hitl,
        generate_code=ctx["generate_code"],
        implementation_model=ctx["implementation_model"],
        hitl_thread_id=ctx.get("thread_id"),
        hitl_action=action,
        hitl_stage=ctx.get("stage"),
        hitl_correction=correction,
    )


def render_sync_hitl_pause(result: dict[str, Any]) -> bool:
    """Render sync HITL pause UI. Returns True when the page should stop."""
    if result.get("pipeline_status") != "hitl_paused":
        return False
    st.header("Pipeline Paused - Review Required")
    st.caption(
        "LangGraph paused before downstream agents ran. "
        "Confirm to continue, retry with feedback, or reject and continue."
    )
    st.markdown(f"#### {result.get('hitl_title', 'Review')}")
    _markdown_or_fallback(
        _rebuild_reproduce_hitl_content(result),
        (
            "No rendered output was attached to this HITL checkpoint. "
            "The checkpoint state is still available; you can continue or retry."
        ),
    )
    feedback = st.text_area("Feedback (for retry)", key="sync_hitl_feedback")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Confirm & Continue", key="sync_hitl_confirm", type="primary"):
            with st.spinner("Continuing pipeline..."):
                try:
                    updated = resume_hitl_pipeline("confirm")
                except Exception as exc:
                    st.error(f"Failed to continue pipeline: {exc}")
                    return True
                st.session_state["paperpilot_result"] = updated
                if updated.get("pipeline_status") != "hitl_paused":
                    st.session_state.pop("hitl_resume_context", None)
                st.rerun()
    with col2:
        if st.button("Retry with feedback", key="sync_hitl_retry"):
            with st.spinner("Retrying with feedback..."):
                try:
                    updated = resume_hitl_pipeline("retry", feedback)
                except Exception as exc:
                    st.error(f"Failed to retry pipeline: {exc}")
                    return True
                st.session_state["paperpilot_result"] = updated
                if updated.get("pipeline_status") != "hitl_paused":
                    st.session_state.pop("hitl_resume_context", None)
                st.rerun()
    with col3:
        if st.button("Reject & Continue", key="sync_hitl_reject"):
            with st.spinner("Continuing after rejection..."):
                try:
                    updated = resume_hitl_pipeline("reject")
                except Exception as exc:
                    st.error(f"Failed to continue pipeline: {exc}")
                    return True
                st.session_state["paperpilot_result"] = updated
                if updated.get("pipeline_status") != "hitl_paused":
                    st.session_state.pop("hitl_resume_context", None)
                st.rerun()
    return True


def store_productize_hitl_context(
    *,
    phase: str,
    papers: list[dict[str, Any]],
    target_user: str = "",
    product_goal: str = "",
    user_idea: str = "",
    preferred_type: str = "auto",
    proposal: dict[str, Any] | None = None,
    research_synthesis: dict[str, Any] | None = None,
    result: dict[str, Any],
) -> None:
    st.session_state["productize_hitl_resume"] = {
        "phase": phase,
        "papers": papers,
        "target_user": target_user,
        "product_goal": product_goal,
        "user_idea": user_idea,
        "preferred_type": preferred_type,
        "proposal": proposal,
        "research_synthesis": research_synthesis or {},
        "thread_id": result.get("hitl_thread_id"),
        "stage": result.get("hitl_stage"),
    }


def resume_productize_hitl(action: str, correction: str = "") -> dict[str, Any]:
    ctx = st.session_state["productize_hitl_resume"]
    hitl = StreamlitHITL(sync_mode=st.session_state.get("enable_sync_hitl", False))
    client = get_llm_client()
    if ctx["phase"] == "proposal":
        proposals, result = generate_proposals(
            papers=ctx["papers"],
            target_user=ctx["target_user"],
            product_goal=ctx["product_goal"],
            llm_client=client,
            user_idea=ctx["user_idea"],
            hitl=hitl,
            hitl_thread_id=ctx.get("thread_id"),
            hitl_action=action,
            hitl_correction=correction,
        )
        return {
            "phase": "proposal",
            "proposals": proposals,
            "result": result,
        }
    proposal_data = ctx.get("proposal") or {}
    proposal = ProductProposal.model_validate(proposal_data)
    result = execute_proposal(
        proposal=proposal,
        papers=ctx["papers"],
        research_synthesis=ctx.get("research_synthesis") or {},
        preferred_type=ctx.get("preferred_type", "auto"),
        llm_client=client,
        hitl=hitl,
        hitl_thread_id=ctx.get("thread_id"),
        hitl_action=action,
        hitl_correction=correction,
    )
    return {"phase": "execution", "result": result}


def render_productize_sync_hitl_pause(result: dict[str, Any]) -> bool:
    """Render productize sync HITL pause UI. Returns True when the page should stop."""
    if result.get("pipeline_status") != "hitl_paused":
        return False
    st.header("Productize Pipeline Paused - Review Required")
    st.caption(
        "LangGraph paused before downstream agents ran. "
        "Confirm to continue, retry with feedback, or reject and continue."
    )
    st.markdown(f"#### {result.get('hitl_title', 'Review')}")
    _markdown_or_fallback(
        _rebuild_productize_hitl_content(result),
        (
            "No rendered output was attached to this HITL checkpoint. "
            "The checkpoint state is still available; you can continue or retry."
        ),
    )
    feedback = st.text_area("Feedback (for retry)", key="productize_sync_hitl_feedback")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Confirm & Continue", key="productize_sync_hitl_confirm", type="primary"):
            with st.spinner("Continuing productize pipeline..."):
                try:
                    updated = resume_productize_hitl("confirm")
                except Exception as exc:
                    st.error(f"Failed to continue productize pipeline: {exc}")
                    return True
                _apply_productize_hitl_resume(updated)
                st.rerun()
    with col2:
        if st.button("Retry with feedback", key="productize_sync_hitl_retry"):
            with st.spinner("Retrying productize pipeline..."):
                try:
                    updated = resume_productize_hitl("retry", feedback)
                except Exception as exc:
                    st.error(f"Failed to retry productize pipeline: {exc}")
                    return True
                _apply_productize_hitl_resume(updated)
                st.rerun()
    with col3:
        if st.button("Reject & Continue", key="productize_sync_hitl_reject"):
            with st.spinner("Continuing after rejection..."):
                try:
                    updated = resume_productize_hitl("reject")
                except Exception as exc:
                    st.error(f"Failed to continue productize pipeline: {exc}")
                    return True
                _apply_productize_hitl_resume(updated)
                st.rerun()
    return True


def _apply_productize_hitl_resume(updated: dict[str, Any]) -> None:
    if updated["phase"] == "proposal":
        result = updated["result"]
        proposals = updated["proposals"]
        if result.get("pipeline_status") == "hitl_paused":
            st.session_state["productize_hitl_result"] = result
            return
        st.session_state.pop("productize_hitl_resume", None)
        st.session_state.pop("productize_hitl_result", None)
        st.session_state["productize_proposals"] = [
            proposal.model_dump(mode="json") for proposal in proposals
        ]
        st.session_state["productize_stage"] = "review" if proposals else "input"
        return
    result = updated["result"]
    st.session_state["productize_result"] = result
    if result.get("pipeline_status") == "hitl_paused":
        st.session_state["productize_hitl_result"] = result
        return
    st.session_state.pop("productize_hitl_resume", None)
    st.session_state.pop("productize_hitl_result", None)
    st.session_state["productize_stage"] = "result"


def handle_deferred_hitl_retries(
    reproduce_hitl: StreamlitHITL,
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    retry_keys = reproduce_hitl.get_retry_keys()
    if not retry_keys or not result:
        return result
    output_dir = resolve_output_dir(result)
    for retry_key in retry_keys:
        correction = reproduce_hitl.get_correction(retry_key)
        with st.spinner(f"Retrying {retry_key} with your feedback..."):
            result = rerun_reproduce_stage(
                result,
                retry_key,
                correction,
                llm_client=get_llm_client(),
                output_dir=output_dir,
            )
            st.session_state["paperpilot_result"] = result
            st.success(f"Retry complete for {retry_key}.")
    st.session_state.pop("_reproduce_hitl", None)
    st.rerun()
    return result
