"""Re-run individual reproduce pipeline stages after deferred HITL feedback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from agents import (
    ReproductionPlannerAgent,
    ResearchUnderstandingAgent,
)
from pipeline.output_builder import (
    build_report,
    build_reproduce_manifest,
    build_reproduction_plan,
    build_run_script,
    save_output,
)
from pipeline.reproduce_renderers import (
    render_environment_plan,
    render_execution_diagnosis,
    render_experiment_plan,
    render_method_breakdown,
    render_research_summary,
)
from pipeline.stage_tracker import STAGE_REAL, record_stage_source
from schemas.reproduction_schema import ExecutionDiagnosis
from tools.llm_client import LLMClient
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import parse_pdf


def rerun_reproduce_stage(
    result: dict[str, Any],
    stage_key: str,
    correction: str,
    *,
    llm_client: LLMClient,
    output_dir: Path,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Re-invoke one deferred HITL stage and refresh derived artifacts."""
    if stage_key == "research":
        research_input = {
            "paper_text": _paper_text_from_result(result),
            "user_idea": str(result.get("user_idea") or ""),
            "user_correction": correction,
        }
        if progress_callback:
            progress_callback("Research Understanding Agent retrying with feedback")
        research = ResearchUnderstandingAgent(llm_client).run_structured(research_input)
        record_stage_source(result, "Research Understanding Agent (retry)", STAGE_REAL)
        result["research_understanding"] = research.model_dump(mode="json")
        result["paper_info"] = render_research_summary(research)
        result["method_info"] = render_method_breakdown(research)
    elif stage_key == "experiment":
        planner_input = {
            "research_understanding": result.get("research_understanding") or {},
            "repository_understanding": result.get("repository_understanding") or {},
            "hardware": str(result.get("hardware") or "Not provided"),
            "gpu_info": str(result.get("gpu_info") or ""),
            "goal": str(result.get("goal") or "minimal training experiment"),
            "user_idea": str(result.get("user_idea") or ""),
            "user_correction": correction,
        }
        if progress_callback:
            progress_callback("Reproduction Planner Agent retrying with feedback")
        plan = ReproductionPlannerAgent(llm_client).run_structured(planner_input)
        record_stage_source(result, "Reproduction Planner Agent (retry)", STAGE_REAL)
        result["reproduction_plan"] = plan.model_dump(mode="json")
        result["env_plan"] = render_environment_plan(plan)
        result["experiment_plan"] = render_experiment_plan(plan)
        result["command_plans"] = [
            item.model_dump(mode="json") for item in plan.command_plans
        ]
    else:
        raise ValueError(f"Unsupported HITL retry stage: {stage_key}")

    _refresh_saved_outputs(result, output_dir)
    return result


def _paper_text_from_result(result: dict[str, Any]) -> str:
    text = str(result.get("paper_text") or "").strip()
    if text:
        return text
    understanding = result.get("research_understanding") or {}
    if isinstance(understanding, dict):
        for key in ("raw_paper_text", "paper_text"):
            candidate = str(understanding.get(key) or "").strip()
            if candidate:
                return candidate
    pdf_path = str(result.get("pdf_path") or "").strip()
    if pdf_path:
        try:
            return parse_pdf(pdf_path)
        except Exception:
            return ""
    return ""


def _ensure_output_fields(result: dict[str, Any]) -> None:
    defaults = {
        "errors": [],
        "paper_info": "Not generated.",
        "method_info": "Not generated.",
        "repo_info": "Not generated.",
        "repo_source": "Not generated.",
        "repo_path": "",
        "code_info": "",
        "env_plan": "Not generated.",
        "experiment_plan": "Not generated.",
    }
    for key, value in defaults.items():
        result.setdefault(key, value)


def _refresh_saved_outputs(result: dict[str, Any], output_dir: Path) -> None:
    _ensure_output_fields(result)
    diagnosis = ExecutionDiagnosis.model_validate(
        result.get("execution_diagnosis") or {}
    )
    diagnosis_text = render_execution_diagnosis(diagnosis)
    reproduction_plan = build_reproduction_plan(result)
    result["run_sh"] = build_run_script(None, result.get("implementation_bundle"))
    result["report"] = build_report(result, diagnosis_text)
    saved_outputs = {
        "reproduction_plan": str(output_dir / "reproduction_plan.md"),
        "run_script": str(output_dir / "run.sh"),
        "report": str(output_dir / "report.md"),
    }
    for writer, content, path in (
        (save_markdown, reproduction_plan, output_dir / "reproduction_plan.md"),
        (save_shell_script, result["run_sh"], output_dir / "run.sh"),
        (save_markdown, result["report"], output_dir / "report.md"),
        (
            save_markdown,
            build_reproduce_manifest(result, output_dir, saved_outputs),
            output_dir / "manifest.json",
        ),
    ):
        save_output(result, f"Failed to save {path.name}", writer, content, path)
