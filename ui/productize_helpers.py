"""Productize mode helper functions."""

from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

import streamlit as st

from main import run_paperpilot
from pipeline.analysis_cache import load_cached_analysis, save_cached_analysis
from tools.llm_client import LLMClient


def has_productize_context(result: dict[str, Any] | None) -> bool:
    """Return whether a reproduction result can feed Productize Mode."""
    required = ("paper_info", "method_info")
    return bool(
        result
        and all(str(result.get(key) or "").strip() for key in required)
    )


def assign_repo_urls(repo_text: str, paper_count: int) -> list[str]:
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


def analysis_to_productize_paper(
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


def run_analysis_for_productize(
    pdf_path: str,
    github_url: str,
    hardware: str,
    gpu_info: str,
    llm_client: LLMClient,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    """Run or load cached reproduce analysis for Productize context."""
    cached = load_cached_analysis(
        pdf_path,
        github_url=github_url,
        hardware=hardware,
        gpu_info=gpu_info,
        mock_mode=llm_client.mock_mode,
    )
    if cached is not None:
        if progress_callback:
            progress_callback(f"Using cached analysis for {Path(pdf_path).name}")
        return cached
    result = run_paperpilot(
        pdf_path=pdf_path,
        github_url=github_url,
        hardware=hardware,
        gpu_info=gpu_info,
        goal="run official demo",
        llm_client=llm_client,
        progress_callback=progress_callback,
        generate_code=False,
        paper_name=Path(pdf_path).stem.replace(" ", "_")[:80],
    )
    save_cached_analysis(
        pdf_path,
        result,
        github_url=github_url,
        hardware=hardware,
        gpu_info=gpu_info,
        mock_mode=llm_client.mock_mode,
    )
    return result


def generated_product_run_command(scaffold_result: dict[str, Any]) -> str:
    """Return the shell command for the actual generated product directory."""
    output_dir = str(scaffold_result.get("output_dir") or "generated_product")
    return f"cd {shlex.quote(output_dir)}\nstreamlit run app.py"


def summarize_generated_product(result: dict[str, Any]) -> dict[str, Any]:
    """Build a compact generated-product status summary for the UI."""
    scaffold = result.get("scaffold_result") or {}
    inspection = result.get("inspection") or {}
    scaffold_success = bool(scaffold.get("success"))
    syntax_ok = bool(inspection.get("syntax_ok"))
    can_run_mock = bool(inspection.get("can_run_mock"))
    has_rich_layout = bool(inspection.get("has_rich_layout"))
    if scaffold_success and syntax_ok and can_run_mock and has_rich_layout:
        status = "ready"
    elif scaffold_success:
        status = "needs_review"
    else:
        status = "failed"
    return {
        "status": status,
        "output_dir": str(scaffold.get("output_dir") or ""),
        "file_count": len(scaffold.get("files") or []),
        "syntax_ok": syntax_ok,
        "can_run_mock": can_run_mock,
        "has_rich_layout": has_rich_layout,
        "run_command": generated_product_run_command(scaffold),
    }


def show_evaluation_scores(evaluation: dict[str, Any]) -> None:
    """Render rubric scores as a simple bar chart."""
    if not evaluation:
        st.info("Evaluation not generated.")
        return
    score_fields = [
        ("paper_faithfulness", "Paper faithfulness"),
        ("multi_paper_coherence", "Multi-paper coherence"),
        ("user_clarity", "User clarity"),
        ("problem_solution_fit", "Problem-solution fit"),
        ("prd_completeness", "PRD completeness"),
        ("mvp_simplicity", "MVP simplicity"),
        ("demo_feasibility", "Demo feasibility"),
        ("mock_first_correctness", "Mock-first correctness"),
        ("safety_awareness", "Safety awareness"),
        ("integration_feasibility", "Integration feasibility"),
        ("overall_score", "Overall"),
    ]
    rows = {
        label: float(evaluation.get(field, 0) or 0)
        for field, label in score_fields
        if field in evaluation
    }
    if rows:
        st.bar_chart(rows)
    st.metric("Demo readiness", str(evaluation.get("demo_readiness", "unknown")))
    if evaluation.get("detected_problems"):
        st.markdown("**Detected problems**")
        for item in evaluation["detected_problems"]:
            st.markdown(f"- {item}")
    if evaluation.get("revision_suggestions"):
        st.markdown("**Revision suggestions**")
        for item in evaluation["revision_suggestions"]:
            st.markdown(f"- {item}")


def show_productize_result(result: dict[str, Any]) -> None:
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

    summary = summarize_generated_product(result)
    st.subheader("Generated Product")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Status", summary["status"])
    metric_columns[1].metric("Files", summary["file_count"])
    metric_columns[2].metric("Syntax", "ok" if summary["syntax_ok"] else "review")
    metric_columns[3].metric("Layout", "rich" if summary["has_rich_layout"] else "basic")
    if summary["output_dir"]:
        st.caption(f"Output directory: `{summary['output_dir']}`")
    st.code(summary["run_command"], language="bash")

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
        evaluation = result.get("evaluation") or {}
        show_evaluation_scores(evaluation if isinstance(evaluation, dict) else {})
        with st.expander("Raw evaluation JSON"):
            st.json(evaluation)
        st.markdown(result.get("test_report") or "Not generated.")

    st.subheader("How to Run Generated Product")
    st.code(summary["run_command"], language="bash")
