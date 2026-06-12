"""Converged four-agent Reproduce pipeline."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from agents import (
    ExecutionDiagnosisAgent,
    RepositoryUnderstandingAgent,
    ReproductionImplementationAgent,
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
    render_implementation_summary,
    render_method_breakdown,
    render_repository_understanding,
    render_research_summary,
)
from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
    ResourceLink,
)
from tools.code_writer import materialize_implementation
from tools.llm_client import LLMClient, LLMClientError
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import parse_pdf
from tools.repo_scanner import scan_repo_detailed
from tools.resource_links import extract_resource_links

PipelineResult = dict[str, Any]
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _record_error(result: PipelineResult, step: str, error: object) -> None:
    result["errors"].append(f"[{step}] {error}")


def _llm_client_key(client: LLMClient) -> str:
    return f"{getattr(client, 'base_url', '')}|{getattr(client, 'model', '')}"


def _run_structured_stage(
    result: PipelineResult,
    stage: str,
    agent_factory: Callable[[LLMClient], Any],
    llm_client: LLMClient,
    input_data: dict[str, Any],
    fallback: Callable[[], SchemaT],
) -> SchemaT:
    client_key = _llm_client_key(llm_client)
    unavailable_clients = result["llm_unavailable_clients"]
    if client_key in unavailable_clients and not llm_client.mock_mode:
        return fallback()
    if not llm_client.mock_mode:
        result["llm_attempts"] += 1
    try:
        return agent_factory(llm_client).run_structured(input_data)
    except LLMClientError as exc:
        result["llm_failures"] += 1
        if exc.blocks_client and client_key not in unavailable_clients:
            unavailable_clients.append(client_key)
        fallback_note = (
            "Remaining stages using the same endpoint and model used fallback outputs."
            if exc.blocks_client
            else "This stage used a fallback output; later stages will continue."
        )
        _record_error(
            result,
            stage,
            f"{exc} {fallback_note}",
        )
        return fallback()
    except Exception as exc:
        _record_error(result, stage, exc)
        return fallback()


def _finalize_status(result: PipelineResult, client: LLMClient) -> None:
    if client.mock_mode:
        result["pipeline_status"] = "mock"
    elif result["llm_failures"] and result["llm_failures"] == result["llm_attempts"]:
        result["pipeline_status"] = "failed"
    elif result["errors"]:
        result["pipeline_status"] = "degraded"
    else:
        result["pipeline_status"] = "complete"


def _initial_result() -> PipelineResult:
    return {
        "pipeline_status": "initializing",
        "llm_attempts": 0,
        "llm_failures": 0,
        "llm_unavailable_clients": [],
        "research_understanding": {},
        "repository_understanding": {},
        "reproduction_plan": {},
        "execution_diagnosis": {},
        "implementation_bundle": {},
        "implementation_model": "",
        "resource_links": [],
        "paper_context": {},
        "paper_info": "",
        "method_info": "",
        "repo_path": "",
        "repo_source": "",
        "generated_repo_path": "",
        "generated_files": [],
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
) -> None:
    reproduction_plan = build_reproduction_plan(result)
    result["run_sh"] = build_run_script(repo_scan, result.get("implementation_bundle"))
    result["report"] = build_report(result, diagnosis_text)
    for step, writer, content, path in (
        (
            "Failed to save reproduction_plan.md",
            save_markdown,
            reproduction_plan,
            OUTPUTS_DIR / "reproduction_plan.md",
        ),
        (
            "Failed to save run.sh",
            save_shell_script,
            result["run_sh"],
            OUTPUTS_DIR / "run.sh",
        ),
        (
            "Failed to save report.md",
            save_markdown,
            result["report"],
            OUTPUTS_DIR / "report.md",
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
    generate_code: bool = True,
    implementation_model: str = "",
) -> PipelineResult:
    """Run the high-level Reproduce reasoning and implementation stages.

    Repository acquisition, scanning, command execution, and artifact writing
    remain deterministic tools. Generated code is materialized but never run
    automatically.
    """
    result = _initial_result()
    if goal == MAIN_GOAL_DEBUG:
        result["pipeline_status"] = "skipped"
        result["errors"].append(
            "Pipeline skipped under debug goal. Please paste logs in the Debug section."
        )
        return result
    client = llm_client or LLMClient()
    if client.mock_mode:
        _record_error(
            result,
            "Configuration",
            "Mock Mode is enabled. LLM agents were not called, so semantic paper "
            "analysis and reproduction planning are placeholders.",
        )

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
        result["pipeline_status"] = "failed"
        _save_outputs(result, None, "Execution diagnosis skipped.")
        return result
    result["paper_context"] = {
        "characters": len(paper_text),
        "pages": paper_text.count("[Page "),
        "truncated": "PDF text truncated by PaperPilot" in paper_text,
    }
    paper_resource_links = extract_resource_links(paper_text, "paper PDF")

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
    research.resource_links = paper_resource_links
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
    repository_resource_links = [
        ResourceLink.model_validate(item)
        for item in (repo_scan or {}).get("resource_links", [])
    ]
    repository.resource_links = repository_resource_links
    result["repository_understanding"] = repository.model_dump(mode="json")
    result["repo_info"] = render_repository_understanding(repository)
    approved_resource_links: list[ResourceLink] = []
    seen_resource_urls: set[str] = set()
    for resource in [*paper_resource_links, *repository_resource_links]:
        if resource.url not in seen_resource_urls:
            seen_resource_urls.add(resource.url)
            approved_resource_links.append(resource)
    result["resource_links"] = [
        item.model_dump(mode="json") for item in approved_resource_links
    ]

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

    generated_repo_scan: dict[str, Any] | None = None
    if generate_code and goal != "understand paper":
        implementation_client = client
        if implementation_model.strip() and implementation_model.strip() != client.model:
            implementation_client = LLMClient(
                api_key=client.api_key,
                base_url=client.base_url,
                model=implementation_model.strip(),
                mock_mode=client.mock_mode,
            )
        result["implementation_model"] = implementation_client.model
        if progress_callback:
            progress_callback(
                "Reproduction Implementation Agent generating code "
                f"with {implementation_client.model}"
            )
        implementation_input = {
            "research_understanding": result["research_understanding"],
            "repository_understanding": result["repository_understanding"],
            "reproduction_plan": result["reproduction_plan"],
            "hardware": hardware,
            "gpu_info": gpu_info,
            "goal": goal,
            "user_idea": user_idea,
            "approved_resource_links": result["resource_links"],
        }
        implementation_error_count = len(result["errors"])
        implementation = _run_structured_stage(
            result,
            "Reproduction Implementation Agent",
            ReproductionImplementationAgent,
            implementation_client,
            implementation_input,
            fallback=lambda: ReproductionImplementationAgent(
                implementation_client
            ).build_mock(implementation_input),
        )
        if implementation_client is not client and len(result["errors"]) > implementation_error_count:
            if progress_callback:
                progress_callback(
                    "Dedicated implementation model failed; retrying code generation "
                    f"with main model {client.model}"
                )
            implementation = _run_structured_stage(
                result,
                "Reproduction Implementation Agent (main model retry)",
                ReproductionImplementationAgent,
                client,
                implementation_input,
                fallback=lambda: ReproductionImplementationAgent(client).build_mock(
                    implementation_input
                ),
            )
            result["implementation_model"] = client.model
            if len(result["errors"]) == implementation_error_count + 1:
                result["errors"][implementation_error_count] = result["errors"][
                    implementation_error_count
                ].replace(
                    "This stage used a fallback output; later stages will continue.",
                    f"Main model retry `{client.model}` succeeded and replaced the fallback code.",
                )
        result["implementation_bundle"] = implementation.model_dump(mode="json")
        try:
            materialized = materialize_implementation(implementation)
            result["generated_repo_path"] = str(materialized["repo_path"])
            result["generated_files"] = list(materialized["files"])
            result["code_info"] = render_implementation_summary(
                implementation,
                result["generated_repo_path"],
                result["generated_files"],
                result["implementation_model"],
            )
            generated_repo_scan = scan_repo_detailed(result["generated_repo_path"])
            if not result["repo_path"]:
                result["repo_path"] = result["generated_repo_path"]
                result["repo_source"] = "Generated reproduction"
        except Exception as exc:
            _record_error(result, "Generated Code Writer", exc)

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
    _save_outputs(result, repo_scan or generated_repo_scan, diagnosis_text)
    _finalize_status(result, client)
    return result
