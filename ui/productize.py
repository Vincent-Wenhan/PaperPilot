"""Productize mode UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from pipeline.productize_pipeline import execute_proposal, generate_proposals
from schemas.product_schema import ProductProposal
from ui.hitl import (
    StreamlitHITL,
    render_productize_sync_hitl_pause,
    store_productize_hitl_context,
)
from ui.llm_config import get_llm_client
from ui.productize_helpers import (
    analysis_to_productize_paper,
    assign_repo_urls,
    has_productize_context,
    run_analysis_for_productize,
    show_productize_result,
)
from ui.shared import save_uploaded_pdf, show_pipeline_errors


def render_productize_mode() -> None:
    """Render multi-paper Productize Mode with three-stage proposal flow."""
    st.title("PaperPilot 2.0: Productize Paper")
    st.caption(
        "Combine one or more paper capabilities into a theory-guided, "
        "mock-first Streamlit product prototype. "
        "Generate proposals, select one, adjust the plan, then execute."
    )

    # Show HITL confirmation dialogs if pending (after generate_proposals or execute_proposal)
    productize_hitl: StreamlitHITL | None = st.session_state.get("_productize_hitl")
    if productize_hitl and productize_hitl._pending_keys:
        st.header("Review & Confirm Agent Outputs")
        st.caption("The pipeline has completed. Review each stage's output below and confirm, reject, or retry with feedback.")
        if productize_hitl.render_pending_dialogs():
            if st.button("Continue to proposals", key="hitl_continue_productize"):
                st.session_state["productize_stage"] = "review"
                st.session_state.pop("_productize_hitl", None)
                st.rerun()
            st.stop()

    hitl_result = st.session_state.get("productize_hitl_result")
    if hitl_result and render_productize_sync_hitl_pause(hitl_result):
        st.stop()

    stage = st.session_state.get("productize_stage", "input")

    # ---------- Input ----------
    with st.expander("Input", expanded=(stage == "input")):
        existing_analyses = st.session_state.get("paperpilot_results") or []
        existing_single = st.session_state.get("paperpilot_result")
        if not existing_analyses and has_productize_context(existing_single):
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
        hw_col, gpu_col = st.columns(2)
        with hw_col:
            hardware = st.selectbox(
                "Hardware",
                ["CPU only", "Single GPU", "Multi GPU"],
                key="productize_hardware",
            )
        with gpu_col:
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

        if st.button("Generate Proposals", type="primary", key="generate_proposals_btn"):
            progress_lines: list[str] = []
            progress_log = st.empty()

            def _on_progress(msg: str) -> None:
                progress_lines.append(f"- {msg}")
                try:
                    progress_log.markdown(
                        "**Progress**\n" + "\n".join(progress_lines)
                    )
                except Exception:
                    pass  # Cross-thread call from LangGraph, no session context

            analyses: list[dict[str, Any]] = []
            titles: list[str] = []
            if uploaded_pdfs:
                try:
                    assigned_urls = assign_repo_urls(github_urls, len(uploaded_pdfs))
                except ValueError as exc:
                    st.error(str(exc))
                    return
                for index, (uploaded_pdf, assigned_url) in enumerate(
                    zip(uploaded_pdfs, assigned_urls, strict=True), 1
                ):
                    _on_progress(f"Analyzing paper {index}: {uploaded_pdf.name}")
                    try:
                        saved_pdf = save_uploaded_pdf(uploaded_pdf)
                        analysis = run_analysis_for_productize(
                            pdf_path=str(saved_pdf),
                            github_url=assigned_url,
                            hardware=hardware,
                            gpu_info=gpu_info.strip(),
                            llm_client=get_llm_client(),
                            progress_callback=_on_progress,
                        )
                    except Exception as exc:
                        import traceback
                        st.error(
                            f"Automatic analysis failed for {uploaded_pdf.name}: {exc}"
                        )
                        with st.expander("Error details"):
                            st.code(traceback.format_exc())
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
                idx
                for idx, analysis in enumerate(analyses, 1)
                if not has_productize_context(analysis)
            ]
            if incomplete:
                st.error(
                    "PaperPilot could not produce paper and method analysis for "
                    f"paper(s): {', '.join(map(str, incomplete))}."
                )
                for analysis in analyses:
                    show_pipeline_errors(analysis.get("errors", []))
                return

            papers = [
                analysis_to_productize_paper(
                    analysis, index=idx, title=titles[idx - 1]
                )
                for idx, analysis in enumerate(analyses, 1)
            ]

            _on_progress("Generating proposals...")
            try:
                if st.session_state.get("enable_hitl", False):
                    productize_hitl = StreamlitHITL(
                        sync_mode=st.session_state.get("enable_sync_hitl", False),
                    )
                    if not productize_hitl.sync_mode:
                        st.session_state["_productize_hitl"] = productize_hitl
                else:
                    productize_hitl = None
                    st.session_state.pop("_productize_hitl", None)

                proposals, proposal_meta = generate_proposals(
                    papers=papers,
                    target_user=target_user.strip(),
                    product_goal=product_goal.strip(),
                    llm_client=get_llm_client(),
                    user_idea=user_idea.strip(),
                    progress_callback=_on_progress,
                    hitl=productize_hitl,
                )
            except Exception as exc:
                st.error(f"Proposal generation failed: {exc}")
                return

            if proposal_meta.get("pipeline_status") == "hitl_paused":
                store_productize_hitl_context(
                    phase="proposal",
                    papers=papers,
                    target_user=target_user.strip(),
                    product_goal=product_goal.strip(),
                    user_idea=user_idea.strip(),
                    result=proposal_meta,
                )
                st.session_state["productize_hitl_result"] = proposal_meta
                st.session_state["productize_papers"] = papers
                st.session_state["productize_stage"] = "input"
                st.rerun()

            if not proposals:
                st.error("No proposals were generated. Please try different inputs.")
                return

            st.session_state["productize_proposals"] = [
                p.model_dump(mode="json") for p in proposals
            ]
            st.session_state["productize_papers"] = papers

            # Check if HITL dialogs are pending — stay on input page to show them
            productize_hitl = st.session_state.get("_productize_hitl")
            if productize_hitl and productize_hitl._pending_keys:
                st.session_state["productize_stage"] = "input"
            else:
                st.session_state["productize_stage"] = "review"
            st.rerun()

    # ---------- Review ----------
    if stage == "review":
        proposals_data = st.session_state.get("productize_proposals", [])
        papers = st.session_state.get("productize_papers", [])
        preferred_type = st.session_state.get("productize_preferred_type", "auto")

        if not proposals_data:
            st.error("No proposals available. Go back to input.")
            if st.button("Back to input"):
                st.session_state["productize_stage"] = "input"
                st.rerun()
            return

        selected_data = st.session_state.get("productize_selected_proposal")
        if selected_data is None:
            # Show proposals in tabs
            proposal_names = [
                p.get("product_name") or f"Proposal {i+1}"
                for i, p in enumerate(proposals_data)
            ]
            tabs = st.tabs(proposal_names)
            for i, (tab, prop) in enumerate(zip(tabs, proposals_data)):
                with tab:
                    st.subheader(prop.get("product_name", "Untitled"))
                    st.markdown(f"**Target User:** {prop.get('target_user', 'N/A')}")
                    st.markdown(f"**Product Goal:** {prop.get('product_goal', 'N/A')}")
                    st.markdown(f"**JTBD:** {prop.get('jtbd', 'N/A')}")

                    # Opportunities
                    opps = prop.get("opportunities", [])
                    if opps:
                        st.markdown("**Product Opportunities:**")
                        for opp in opps:
                            st.markdown(
                                f"- **{opp.get('idea_name', 'Idea')}** "
                                f"(Score: {opp.get('overall_score', 'N/A')}/5) — "
                                f"{opp.get('core_value', '')}"
                            )

                    # PRD
                    prd = prop.get("prd", {})
                    with st.expander("PRD", expanded=True):
                        st.markdown(f"**Problem:** {prd.get('problem_statement', 'N/A')}")
                        st.markdown("**Core Features:**")
                        for feat in prd.get("core_features", []):
                            st.markdown(f"- {feat}")
                        st.markdown("**User Flow:**")
                        for step_text in prd.get("user_flow", []):
                            st.markdown(f"- {step_text}")

                    # MVP Scope
                    mvp = prop.get("mvp_scope", {})
                    with st.expander("MVP / MoSCoW"):
                        for label, key in [("Must Have", "must_have"), ("Should Have", "should_have"),
                                          ("Could Have", "could_have"), ("Won't Have", "wont_have")]:
                            items = mvp.get(key, [])
                            st.markdown(f"**{label}:**")
                            for item in items:
                                st.markdown(f"- {item}")

                    # Risks
                    risks = prop.get("risks", [])
                    if risks:
                        with st.expander("Risks"):
                            for r in risks:
                                st.markdown(f"- {r}")

                    if st.button("Select This Proposal", key=f"select_proposal_{i}"):
                        st.session_state["productize_selected_proposal"] = prop
                        st.rerun()
        else:
            # Proposal selected — show editable view
            st.subheader(f"Selected: {selected_data.get('product_name', 'Untitled')}")
            st.markdown(f"**Target User:** {selected_data.get('target_user', 'N/A')}")
            st.markdown(f"**JTBD:** {selected_data.get('jtbd', 'N/A')}")

            # Editable fields
            prd = selected_data.get("prd", {})
            st.markdown("### Edit PRD & MVP")
            edited_core_features = st.text_area(
                "Core Features (one per line)",
                value="\n".join(prd.get("core_features", [])),
                height=100,
                key="edit_core_features",
            )
            edited_must_have = st.text_area(
                "Must Have (one per line)",
                value="\n".join(selected_data.get("mvp_scope", {}).get("must_have", [])),
                height=80,
                key="edit_must_have",
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Back to proposals", key="back_to_proposals"):
                    st.session_state["productize_selected_proposal"] = None
                    st.rerun()
            with col2:
                if st.button("Execute Proposal", type="primary", key="execute_proposal_btn"):
                    # Apply edits
                    prd["core_features"] = [
                        l.strip() for l in edited_core_features.split("\n") if l.strip()
                    ]
                    selected_data["mvp_scope"]["must_have"] = [
                        l.strip() for l in edited_must_have.split("\n") if l.strip()
                    ]

                    # Rebuild ProductProposal
                    from schemas.product_schema import PRD as PRDModel, MVPScope as MVPScopeModel
                    edited_proposal = ProductProposal(
                        product_name=selected_data.get("product_name", ""),
                        target_user=selected_data.get("target_user", ""),
                        product_goal=selected_data.get("product_goal", ""),
                        jtbd=selected_data.get("jtbd", ""),
                        opportunities=[
                            ProductProposal.__pydantic_fields__["opportunities"].__class__(
                                **opp
                            ) if isinstance(opp, dict) else opp
                            for opp in selected_data.get("opportunities", [])
                        ],
                        value_proposition=selected_data.get("value_proposition", {}),
                        prd=PRDModel(**prd),
                        mvp_scope=MVPScopeModel(**selected_data.get("mvp_scope", {})),
                        risks=selected_data.get("risks", []),
                    )

                    progress_lines = []
                    progress_log = st.empty()

                    def _on_progress2(msg: str) -> None:
                        progress_lines.append(f"- {msg}")
                        try:
                            progress_log.markdown(
                                "**Execution Progress**\n" + "\n".join(progress_lines)
                            )
                        except Exception:
                            pass  # Cross-thread call from LangGraph, no session context

                    _on_progress2("Executing proposal...")
                    try:
                        exec_hitl: StreamlitHITL | None = None
                        if st.session_state.get("enable_hitl", False):
                            exec_hitl = StreamlitHITL(
                                sync_mode=st.session_state.get("enable_sync_hitl", False),
                            )
                            if not exec_hitl.sync_mode:
                                st.session_state["_productize_hitl"] = exec_hitl

                        result = execute_proposal(
                            proposal=edited_proposal,
                            papers=papers,
                            research_synthesis={},
                            preferred_type=preferred_type,
                            repo_path="",
                            llm_client=get_llm_client(),
                            progress_callback=_on_progress2,
                            hitl=exec_hitl,
                        )
                    except Exception as exc:
                        st.error(f"Proposal execution failed: {exc}")
                        return

                    if result.get("pipeline_status") == "hitl_paused":
                        store_productize_hitl_context(
                            phase="execution",
                            papers=papers,
                            preferred_type=preferred_type,
                            proposal=selected_data,
                            result=result,
                        )
                        st.session_state["productize_hitl_result"] = result
                        st.rerun()

                    st.session_state["productize_result"] = result
                    exec_hitl = st.session_state.get("_productize_hitl")
                    if exec_hitl and exec_hitl._pending_keys:
                        pass
                    else:
                        st.session_state["productize_stage"] = "result"
                    st.rerun()

    # ---------- Result ----------
    if stage == "result":
        result = st.session_state.get("productize_result")
        if result:
            show_productize_result(result)
        if st.button("Start over", key="productize_start_over"):
            st.session_state["productize_stage"] = "input"
            st.session_state["productize_proposals"] = []
            st.session_state["productize_selected_proposal"] = None
            st.session_state["productize_result"] = None
            st.rerun()


