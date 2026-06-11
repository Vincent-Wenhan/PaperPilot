"""Converged four-agent Reproduce pipeline."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from agents import (
    ExecutionDiagnosisAgent,
    RepositoryUnderstandingAgent,
    ReproductionPlannerAgent,
    ResearchUnderstandingAgent,
)
from config import MAIN_GOAL_DEBUG, OUTPUTS_DIR
from pipeline.output_builder import (
    build_report,
    build_reproduction_plan,
    build_run_script,
    save_output,
)
from pipeline.repository_stage import prepare_repository
from pipeline.reproduce_renderers import (
    render_environment_plan,
    render_execution_diagnosis,
    render_experiment_plan,
    render_method_breakdown,
    render_repository_understanding,
    render_research_summary,
)
from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)
from tools.llm_client import LLMClient
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import parse_pdf

PipelineResult = dict[str, Any]
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _record_error(result: PipelineResult, step: str, error: object) -> None:
    result["errors"].append(f"[{step}] {error}")


def _run_structured_stage(
    result: PipelineResult,
    stage: str,
    agent_factory: Callable[[LLMClient], Any],
    llm_client: LLMClient,
    input_data: dict[str, Any],
    fallback: Callable[[], SchemaT],
) -> SchemaT:
    try:
        return agent_factory(llm_client).run_structured(input_data)
    except Exception as exc:
        _record_error(result, stage, exc)
        return fallback()


def _initial_result() -> PipelineResult:
    return {
        "research_understanding": {},
        "repository_understanding": {},
        "reproduction_plan": {},
        "execution_diagnosis": {},
        "paper_info": "",
        "method_info": "",
        "repo_path": "",
        "repo_source": "",
        "code_info": "",
        "repo_info": "",
        "env_plan": "",
        "experiment_plan": "",
        "report": "",
        "run_sh": "",
        "errors": [],
    }


def _save_outputs(
    result: PipelineResult,
    repo_scan: dict[str, Any] | None,
    diagnosis_text: str,
    output_dir: Path = OUTPUTS_DIR,
) -> None:
    reproduction_plan = build_reproduction_plan(result)
    result["run_sh"] = build_run_script(repo_scan)
    result["report"] = build_report(result, diagnosis_text)
    for step, writer, content, path in (
        (
            "Failed to save reproduction_plan.md",
            save_markdown,
            reproduction_plan,
            output_dir / "reproduction_plan.md",
        ),
        (
            "Failed to save run.sh",
            save_shell_script,
            result["run_sh"],
            output_dir / "run.sh",
        ),
        (
            "Failed to save report.md",
            save_markdown,
            result["report"],
            output_dir / "report.md",
        ),
    ):
        save_output(result, step, writer, content, path)


def run_reproduce_pipeline(
    pdf_path: str,
    github_url: str = "",
    hardware: str = "Not provided",
    gpu_info: str = "",
    goal: str = "minimal training experiment",
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
    user_idea: str = "",
    paper_name: str = "",
) -> PipelineResult:
    """Run the four high-level Reproduce reasoning stages.

    Repository acquisition, scanning, command execution, and artifact writing
    remain deterministic tools. No legacy fragmented agent is called.

    When ``paper_name`` is provided, output files are written to
    ``outputs/<paper_name>/`` instead of the root ``outputs/`` directory.
    """
    result = _initial_result()
    output_dir = OUTPUTS_DIR / paper_name if paper_name else OUTPUTS_DIR
    if goal == MAIN_GOAL_DEBUG:
        result["errors"].append(
            "Pipeline skipped under debug goal. Please paste logs in the Debug section."
        )
        return result
    client = llm_client or LLMClient()

    try:
        paper_text = parse_pdf(pdf_path) if pdf_path.strip() else ""
    except Exception as exc:
        _record_error(result, "PDF Parser", exc)
        paper_text = ""
    if not paper_text.strip():
        _record_error(
            result,
            "Research Understanding Agent",
            "No extractable paper text is available; provide a text-based or OCR PDF.",
        )
        _save_outputs(result, None, "Execution diagnosis skipped.", output_dir=output_dir)
        return result

    if progress_callback:
        progress_callback("Research Understanding Agent analyzing")
    research_input = {"paper_text": paper_text, "user_idea": user_idea}
    research = _run_structured_stage(
        result,
        "Research Understanding Agent",
        ResearchUnderstandingAgent,
        client,
        research_input,
        fallback=lambda: ResearchUnderstandingAgent(client).build_mock(research_input),
    )
    result["research_understanding"] = research.model_dump(mode="json")
    result["paper_info"] = render_research_summary(research)
    result["method_info"] = render_method_breakdown(research)

    repo_scan = prepare_repository(
        result=result,
        github_url=github_url,
        progress_callback=progress_callback,
    )
    if progress_callback:
        progress_callback("Repository Understanding Agent analyzing")
    repository_input = {
        "research_understanding": result["research_understanding"],
        "repo_scan": repo_scan or {},
        "github_url": github_url,
    }
    repository = _run_structured_stage(
        result,
        "Repository Understanding Agent",
        RepositoryUnderstandingAgent,
        client,
        repository_input,
        fallback=lambda: RepositoryUnderstandingAgent(client).build_mock(repository_input),
    )
    result["repository_understanding"] = repository.model_dump(mode="json")
    result["repo_info"] = render_repository_understanding(repository)

    if progress_callback:
        progress_callback("Reproduction Planner Agent planning")
    planner_input = {
        "research_understanding": result["research_understanding"],
        "repository_understanding": result["repository_understanding"],
        "goal": goal,
        "hardware": hardware,
        "gpu_info": gpu_info,
        "user_idea": user_idea,
    }
    plan = _run_structured_stage(
        result,
        "Reproduction Planner Agent",
        ReproductionPlannerAgent,
        client,
        planner_input,
        fallback=lambda: ReproductionPlannerAgent(client).build_mock(planner_input),
    )
    result["reproduction_plan"] = plan.model_dump(mode="json")
    result["env_plan"] = render_environment_plan(plan)
    result["experiment_plan"] = render_experiment_plan(plan)

    if progress_callback:
        progress_callback("Execution & Diagnosis Agent assessing feasibility")
    diagnosis_input = {
        "command_results": [],
        "reproduction_plan": result["reproduction_plan"],
    }
    diagnosis = _run_structured_stage(
        result,
        "Execution & Diagnosis Agent",
        ExecutionDiagnosisAgent,
        client,
        diagnosis_input,
        fallback=lambda: ExecutionDiagnosisAgent(client).build_mock(diagnosis_input),
    )
    result["execution_diagnosis"] = diagnosis.model_dump(mode="json")
    diagnosis_text = render_execution_diagnosis(diagnosis)
    _save_outputs(result, repo_scan, diagnosis_text, output_dir=output_dir)
    return result
