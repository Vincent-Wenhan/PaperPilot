"""Converged four-agent Reproduce pipeline."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from agents import (
    CodeReviewAgent,
    ExecutionDiagnosisAgent,
    RepositoryUnderstandingAgent,
    ReproductionImplementationAgent,
    ReproductionPlannerAgent,
    ResearchUnderstandingAgent,
)
from config import MAIN_GOAL_DEBUG, OUTPUTS_DIR
from graphs.reproduce_graph import (
    ReproduceGraphDependencies,
    build_reproduce_graph,
)
from pipeline.output_builder import (
    build_reproduce_manifest,
    build_report,
    build_reproduction_plan,
    build_run_script,
    save_output,
)
from pipeline.output_paths import resolve_output_dir, safe_output_name
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
from pipeline.graph_checkpointer import get_shared_checkpointer
from pipeline.hitl_retry import rerun_reproduce_stage
from pipeline.graph_hitl_runner import (
    REPRODUCE_HITL_INTERRUPT_AFTER,
    get_interrupt_node,
    graph_is_interrupted,
    invoke_until_pause_or_complete,
    new_hitl_thread_id,
    render_interrupt_content,
    resume_graph,
)
from pipeline.hitl_context import PipelineHITL
from pipeline.stage_tracker import (
    STAGE_FALLBACK,
    STAGE_MOCK,
    STAGE_REAL,
    init_stage_sources,
    record_stage_source,
)
from runtime.checkpointing import build_graph_config
from schemas.code_review_schema import CodeReview
from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    ImplementationBlueprint,
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
    ResourceLink,
)
from tools.code_writer import materialize_implementation
from tools.code_quality import assess_implementation_quality
from tools.command_runner import run_sandbox_verification
from tools.implementation_blueprint import build_implementation_blueprint
from tools.llm_client import LLMClient, LLMClientError
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import analyze_pdf_quality, parse_pdf
from tools.repo_evidence_gatherer import gather_repo_evidence
from tools.repo_scanner import scan_repo_detailed
from tools.resource_links import extract_resource_links

PipelineResult = dict[str, Any]
SchemaT = TypeVar("SchemaT", bound=BaseModel)
DEFAULT_CODE_MAX_REVISIONS = 4


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
        record_stage_source(result, stage, STAGE_FALLBACK)
        return fallback()
    if llm_client.mock_mode:
        record_stage_source(result, stage, STAGE_MOCK)
        return fallback()
    result["llm_attempts"] += 1
    try:
        output = agent_factory(llm_client).run_structured(input_data)
        record_stage_source(result, stage, STAGE_REAL)
        return output
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
        record_stage_source(result, stage, STAGE_FALLBACK)
        return fallback()
    except Exception as exc:
        _record_error(result, stage, exc)
        record_stage_source(result, stage, STAGE_FALLBACK)
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
        "implementation_blueprint": {},
        "implementation_bundle": {},
        "code_review": {},
        "code_second_review": {},
        "code_revision_count": 0,
        "code_max_revisions": DEFAULT_CODE_MAX_REVISIONS,
        "blueprint_quality": {},
        "code_quality": {},
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
        "command_plans": [],
        "command_route": "safe",
        "pending_human_review": None,
        "command_results": [],
        "graph_trace": [],
        "issues": [],
        "errors": [],
        "stage_sources": {},
        "pdf_quality": {},
        "paper_name": "",
        "paper_text": "",
        "pdf_path": "",
        "hardware": "",
        "gpu_info": "",
        "goal": "",
        "user_idea": "",
    }


def _merge_quality_into_review(
    review: CodeReview,
    quality: dict[str, Any],
) -> CodeReview:
    """Force a revision when deterministic generated-code quality is too low."""
    if not quality or quality.get("passes_minimum_quality", True):
        return review
    detected_problems = list(review.detected_problems)
    for issue in quality.get("issues") or []:
        issue_text = str(issue)
        if issue_text not in detected_problems:
            detected_problems.append(issue_text)
    revision_suggestions = list(review.revision_suggestions)
    for suggestion in quality.get("suggestions") or []:
        suggestion_text = str(suggestion)
        if suggestion_text not in revision_suggestions:
            revision_suggestions.append(suggestion_text)
    quality_score = float(quality.get("overall_score") or review.overall_score)
    capped_score = min(review.overall_score, quality_score, 3.0)
    return review.model_copy(
        update={
            "overall_score": max(1.0, capped_score),
            "runnability": min(review.runnability, max(1.0, quality_score)),
            "detected_problems": detected_problems,
            "revision_suggestions": revision_suggestions,
            "verdict": "revise",
        }
    )


def _save_outputs(
    result: PipelineResult,
    repo_scan: dict[str, Any] | None,
    diagnosis_text: str,
    output_dir: Path = OUTPUTS_DIR,
) -> None:
    reproduction_plan = build_reproduction_plan(result)
    result["run_sh"] = build_run_script(repo_scan, result.get("implementation_bundle"))
    result["report"] = build_report(result, diagnosis_text)
    saved_outputs = {
        "reproduction_plan": str(output_dir / "reproduction_plan.md"),
        "run_script": str(output_dir / "run.sh"),
        "report": str(output_dir / "report.md"),
    }
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
    _save_generated_code(result, output_dir)
    save_output(
        result,
        "Failed to save manifest.json",
        save_markdown,
        build_reproduce_manifest(result, output_dir, saved_outputs),
        output_dir / "manifest.json",
    )


def _save_generated_code(result: PipelineResult, output_dir: Path) -> None:
    repo_path = str(result.get("generated_repo_path") or "").strip()
    if not repo_path:
        return
    source = Path(repo_path).expanduser().resolve()
    if not source.is_dir():
        return
    destination = output_dir / "generated"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"),
    )
    result["generated_code_output_dir"] = str(destination)


def _merge_graph_state_into_result(
    result: PipelineResult,
    state: dict[str, Any],
    *,
    generate_code: bool,
    goal: str,
) -> None:
    result["research_understanding"] = state.get("research_understanding") or {}
    result["repository_understanding"] = state.get("repository_understanding") or {}
    result["reproduction_plan"] = state.get("reproduction_plan") or {}
    result["execution_diagnosis"] = state.get("execution_diagnosis") or {}
    if generate_code and goal != "understand paper":
        result["implementation_bundle"] = state.get("implementation_bundle") or {}
    result["command_plans"] = list(state.get("command_plans") or [])
    result["command_route"] = state.get("command_route") or "safe"
    result["pending_human_review"] = state.get("pending_human_review")
    result["command_results"] = list(state.get("command_results") or [])
    result["code_review"] = state.get("code_review") or {}
    result["code_second_review"] = state.get("code_second_review") or {}
    result["code_revision_count"] = int(state.get("code_revision_count") or 0)
    result["code_max_revisions"] = int(
        state.get("code_max_revisions") or DEFAULT_CODE_MAX_REVISIONS
    )
    result["graph_trace"] = list(state.get("graph_trace") or [])
    result["errors"].extend(state.get("errors") or [])
    _refresh_rendered_result_fields(result)


def _record_final_code_quality_status(
    result: PipelineResult,
    state: dict[str, Any],
    *,
    generate_code: bool,
    goal: str,
) -> None:
    """Make exhausted code-review failures visible in the run result."""
    if not generate_code or goal == "understand paper":
        return

    review = state.get("code_second_review") or state.get("code_review") or {}
    quality = result.get("code_quality") or {}
    verdict = str(review.get("verdict") or "").lower()
    revision_count = int(state.get("code_revision_count") or 0)
    max_revisions = int(state.get("code_max_revisions") or DEFAULT_CODE_MAX_REVISIONS)
    exhausted = revision_count >= max_revisions
    quality_failed = quality and not bool(quality.get("passes_minimum_quality", True))
    if not exhausted or (verdict in {"", "accept"} and not quality_failed):
        return

    score = review.get("overall_score") or quality.get("overall_score")
    problems = list(review.get("detected_problems") or quality.get("issues") or [])
    detail = (
        f"Generated code did not pass review after "
        f"{revision_count}/{max_revisions} revision attempts"
    )
    if score is not None:
        detail += f" (score: {score})"
    if problems:
        detail += ": " + "; ".join(str(item) for item in problems[:3])
    if detail not in result["errors"]:
        _record_error(result, "Code Quality Gate", detail)


def _refresh_rendered_result_fields(result: PipelineResult) -> None:
    """Rebuild display fields from checkpointed graph state after HITL resume."""
    if result.get("research_understanding"):
        try:
            research = PaperUnderstanding.model_validate(
                result["research_understanding"]
            )
            result["paper_info"] = render_research_summary(research)
            result["method_info"] = render_method_breakdown(research)
        except Exception:
            pass
    if result.get("repository_understanding"):
        try:
            repository = RepositoryUnderstanding.model_validate(
                result["repository_understanding"]
            )
            result["repo_info"] = render_repository_understanding(repository)
        except Exception:
            pass
    if result.get("reproduction_plan"):
        try:
            plan = ReproductionPlan.model_validate(result["reproduction_plan"])
            result["env_plan"] = render_environment_plan(plan)
            result["experiment_plan"] = render_experiment_plan(plan)
        except Exception:
            pass


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
    hitl: PipelineHITL | None = None,
    generate_code: bool = True,
    implementation_model: str = "",
    output_dir: str | Path | None = None,
    hitl_thread_id: str | None = None,
    hitl_action: str | None = None,
    hitl_stage: str | None = None,
    hitl_correction: str = "",
) -> PipelineResult:
    """Run the backward-compatible Reproduce API through LangGraph."""
    result = _initial_result()
    init_stage_sources(result)
    paper_name = safe_output_name(paper_name)
    output_dir = Path(output_dir).expanduser() if output_dir else resolve_output_dir({"paper_name": paper_name})
    result["paper_name"] = paper_name
    result["pdf_path"] = pdf_path
    result["hardware"] = hardware
    result["gpu_info"] = gpu_info
    result["goal"] = goal
    result["user_idea"] = user_idea
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

    paper_resource_links: list[ResourceLink] = []
    repository_resource_links: list[ResourceLink] = []
    generated_repo_scan: dict[str, Any] | None = None
    missing_paper_text = False

    def progress(stage: str) -> None:
        if progress_callback:
            progress_callback(stage)

    def parse_paper_dependency(path: str) -> str:
        nonlocal paper_resource_links
        if path.strip():
            try:
                result["pdf_quality"] = analyze_pdf_quality(path)
                for warning in result["pdf_quality"].get("warnings", []):
                    _record_error(result, "PDF Parser", warning)
            except Exception as exc:
                _record_error(result, "PDF Parser", f"PDF quality check failed: {exc}")
        text = parse_pdf(path) if path.strip() else ""
        if text.strip():
            result["paper_text"] = text
            result["paper_context"] = {
                "characters": len(text),
                "pages": text.count("[Page "),
                "truncated": "PDF text truncated by PaperPilot" in text,
            }
            paper_resource_links = extract_resource_links(text, "paper PDF")
        return text

    def understand_research(
        paper_text: str,
        graph_user_idea: str,
    ) -> PaperUnderstanding:
        nonlocal missing_paper_text
        if not paper_text.strip():
            missing_paper_text = True
            _record_error(
                result,
                "Research Understanding Agent",
                "No extractable paper text is available; provide a text-based or OCR PDF.",
            )
        progress("Research Understanding Agent analyzing")
        research_input = {
            "paper_text": paper_text,
            "user_idea": graph_user_idea,
        }
        if paper_text.strip():
            research = _run_structured_stage(
                result,
                "Research Understanding Agent",
                ResearchUnderstandingAgent,
                client,
                research_input,
                fallback=lambda: ResearchUnderstandingAgent(client).build_mock(
                    research_input
                ),
            )
        else:
            research = ResearchUnderstandingAgent(client).build_mock(research_input)
        research.resource_links = paper_resource_links
        result["research_understanding"] = research.model_dump(mode="json")
        result["paper_info"] = render_research_summary(research)
        result["method_info"] = render_method_breakdown(research)
        if hitl and paper_text.strip() and not hitl.sync_mode:
            hitl_result = hitl.request_confirmation(
                "research",
                "Paper Summary",
                f"{result['paper_info']}\n\n{result['method_info']}",
            )
            if hitl_result == "retry":
                research_input["user_correction"] = hitl.get_correction("research")
                progress("Research Understanding Agent retrying with feedback")
                research = _run_structured_stage(
                    result,
                    "Research Understanding Agent (retry)",
                    ResearchUnderstandingAgent,
                    client,
                    research_input,
                    fallback=lambda: ResearchUnderstandingAgent(client).build_mock(
                        research_input
                    ),
                )
                research.resource_links = paper_resource_links
                result["research_understanding"] = research.model_dump(mode="json")
                result["paper_info"] = render_research_summary(research)
                result["method_info"] = render_method_breakdown(research)
            elif hitl_result == "reject":
                _record_error(
                    result,
                    "HITL: Research Understanding",
                    "Rejected by user",
                )
                result["paper_info"] = "[Research understanding rejected by user]"
                result["method_info"] = ""
        return research

    def prepare_repository_dependency(url: str) -> dict[str, Any]:
        scan = prepare_repository(
            result=result,
            github_url=url,
            progress_callback=progress_callback,
        )
        return scan or {}

    def understand_repository(
        research: dict[str, Any],
        repo_scan: dict[str, Any],
        url: str,
    ) -> RepositoryUnderstanding:
        nonlocal repository_resource_links
        progress("Repository Understanding Agent analyzing")
        tool_evidence: dict[str, Any] = {}
        repo_path = str(repo_scan.get("repo_path") or "")
        if repo_path:
            try:
                tool_evidence = gather_repo_evidence(repo_path)
            except Exception as exc:
                _record_error(result, "Repository Tools", exc)
        repository_input = {
            "research_understanding": research,
            "repo_scan": repo_scan,
            "github_url": url,
            "tool_evidence": tool_evidence,
        }
        repository = _run_structured_stage(
            result,
            "Repository Understanding Agent",
            RepositoryUnderstandingAgent,
            client,
            repository_input,
            fallback=lambda: RepositoryUnderstandingAgent(client).build_mock(
                repository_input
            ),
        )
        repository_resource_links = [
            ResourceLink.model_validate(item)
            for item in repo_scan.get("resource_links", [])
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
        return repository

    def plan_reproduction(
        research: dict[str, Any],
        repository: dict[str, Any],
        inputs: dict[str, Any],
    ) -> ReproductionPlan:
        progress("Reproduction Planner Agent planning")
        planner_input = {
            "research_understanding": research,
            "repository_understanding": repository,
            **inputs,
        }
        plan = _run_structured_stage(
            result,
            "Reproduction Planner Agent",
            ReproductionPlannerAgent,
            client,
            planner_input,
            fallback=lambda: ReproductionPlannerAgent(client).build_mock(
                planner_input
            ),
        )
        result["reproduction_plan"] = plan.model_dump(mode="json")
        result["env_plan"] = render_environment_plan(plan)
        result["experiment_plan"] = render_experiment_plan(plan)
        if hitl and not hitl.sync_mode:
            hitl_result = hitl.request_confirmation(
                "experiment",
                "Experiment Plan",
                f"{result['env_plan']}\n\n{result['experiment_plan']}",
            )
            if hitl_result == "retry":
                planner_input["user_correction"] = hitl.get_correction("experiment")
                progress("Reproduction Planner Agent retrying with feedback")
                plan = _run_structured_stage(
                    result,
                    "Reproduction Planner Agent (retry)",
                    ReproductionPlannerAgent,
                    client,
                    planner_input,
                    fallback=lambda: ReproductionPlannerAgent(client).build_mock(
                        planner_input
                    ),
                )
                result["reproduction_plan"] = plan.model_dump(mode="json")
                result["env_plan"] = render_environment_plan(plan)
                result["experiment_plan"] = render_experiment_plan(plan)
            elif hitl_result == "reject":
                _record_error(
                    result,
                    "HITL: Reproduction Planner",
                    "Rejected by user",
                )
        return plan

    def generate_implementation(state: dict[str, Any]) -> dict[str, Any]:
        nonlocal generated_repo_scan
        if not generate_code or goal == "understand paper":
            return {}
        implementation_client = client
        if (
            implementation_model.strip()
            and implementation_model.strip() != client.model
        ):
            implementation_client = LLMClient(
                api_key=client.api_key,
                base_url=client.base_url,
                model=implementation_model.strip(),
                mock_mode=client.mock_mode,
            )
        result["implementation_model"] = implementation_client.model
        progress(
            "Reproduction Implementation Agent generating code "
            f"with {implementation_client.model}"
        )
        method_spec_json = json.dumps(
            ResearchUnderstandingAgent.build_method_spec(
                PaperUnderstanding.model_validate(
                    state.get("research_understanding") or {}
                )
            ).model_dump(mode="json")
        ) if state.get("research_understanding") else "{}"
        blueprint = build_implementation_blueprint(
            PaperUnderstanding.model_validate(
                state.get("research_understanding") or {}
            ),
            RepositoryUnderstanding.model_validate(
                state.get("repository_understanding") or {}
            ),
            ReproductionPlan.model_validate(state.get("reproduction_plan") or {}),
            hardware=hardware,
            goal=goal,
        )
        result["implementation_blueprint"] = blueprint.model_dump(mode="json")
        implementation_input = {
            "research_understanding": state.get("research_understanding") or {},
            "repository_understanding": state.get("repository_understanding") or {},
            "reproduction_plan": state.get("reproduction_plan") or {},
            "implementation_blueprint": result["implementation_blueprint"],
            "paper_text": state.get("paper_text", ""),
            "hardware": hardware,
            "gpu_info": gpu_info,
            "goal": goal,
            "user_idea": user_idea,
            "approved_resource_links": result["resource_links"],
            "method_spec": method_spec_json,
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
        if (
            implementation_client is not client
            and len(result["errors"]) > implementation_error_count
        ):
            progress(
                "Dedicated implementation model failed; retrying code generation "
                f"with main model {client.model}"
            )
            implementation = _run_structured_stage(
                result,
                "Reproduction Implementation Agent (main model retry)",
                ReproductionImplementationAgent,
                client,
                implementation_input,
                fallback=lambda: ReproductionImplementationAgent(
                    client
                ).build_mock(implementation_input),
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
        result["code_quality"] = assess_implementation_quality(
            implementation,
            blueprint=blueprint,
        )
        result["blueprint_quality"] = result["code_quality"]["metrics"].get(
            "blueprint",
            {},
        )
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
        # Actually run the smoke test so the reviewer and reviser see real output.
        smoke_cmd = implementation.smoke_test_command or "python main.py --smoke-test"
        smoke_result = _run_smoke_test(result.get("generated_repo_path", ""), smoke_cmd)
        result["smoke_test_result"] = smoke_result
        if not smoke_result.get("passed"):
            _record_error(
                result,
                "Smoke Test",
                f"exit={smoke_result.get('exit_code')}: "
                f"{(smoke_result.get('stderr') or '')[:400]}",
            )
        return result["implementation_bundle"]

    def review_code(state: dict[str, Any]) -> CodeReview:
        if not generate_code or goal == "understand paper":
            return CodeReview(
                overall_score=5.0,
                verdict="accept",
                detected_problems=[],
                revision_suggestions=[],
            )
        progress("Code Review Agent evaluating generated code")
        review_input = {
            "paper_text": state.get("paper_text", ""),
            "research_understanding": state.get("research_understanding") or {},
            "reproduction_plan": state.get("reproduction_plan") or {},
            "implementation_bundle": state.get("implementation_bundle") or {},
            "role": "initial",
            "sandbox_verification": json.dumps(
                state.get("sandbox_verification") or {}, indent=2
            ),
        }
        review = _run_structured_stage(
            result,
            "Code Review Agent",
            CodeReviewAgent,
            client,
            review_input,
            fallback=lambda: CodeReviewAgent(client).build_mock(review_input),
        )
        review = _merge_quality_into_review(review, result.get("code_quality") or {})
        progress(f"Code review verdict: {review.verdict} (score: {review.overall_score})")
        return review

    def second_review_code(state: dict[str, Any]) -> CodeReview:
        if not generate_code or goal == "understand paper":
            return CodeReview(
                overall_score=5.0,
                verdict="accept",
                detected_problems=[],
                revision_suggestions=[],
            )
        progress("Second Review Agent evaluating code (adversarial pass)")
        review_input = {
            "paper_text": state.get("paper_text", ""),
            "research_understanding": state.get("research_understanding") or {},
            "reproduction_plan": state.get("reproduction_plan") or {},
            "implementation_bundle": state.get("implementation_bundle") or {},
            "previous_review": state.get("code_review") or {},
            "role": "adversarial",
            "sandbox_verification": json.dumps(
                state.get("sandbox_verification") or {}, indent=2
            ),
        }
        review = _run_structured_stage(
            result,
            "Second Review Agent",
            CodeReviewAgent,
            client,
            review_input,
            fallback=lambda: CodeReviewAgent(client).build_mock(review_input),
        )
        review = _merge_quality_into_review(review, result.get("code_quality") or {})
        progress(f"Second review verdict: {review.verdict} (score: {review.overall_score})")
        return review

    def sandbox_verify_fn(state: dict[str, Any]) -> dict[str, Any]:
        if not generate_code or goal == "understand paper":
            return {"passed": True, "results": [], "error": None}
        progress("Sandbox verifying generated code")
        repo_path = result.get("generated_repo_path") or result.get("repo_path") or state.get("repo_path") or ""
        if not repo_path:
            return {"passed": False, "results": [], "error": "No generated repo path"}
        bundle = state.get("implementation_bundle") or {}
        smoke_test = bundle.get("smoke_test_command", "python main.py --smoke-test") if isinstance(bundle, dict) else "python main.py --smoke-test"
        verification = run_sandbox_verification(repo_path, smoke_test)
        passed_count = sum(1 for r in verification.get("results", []) if r.get("passed"))
        total = len(verification.get("results", []))
        progress(f"Sandbox verification: {passed_count}/{total} checks passed")
        return verification

    def _run_smoke_test(repo_path: str, smoke_command: str) -> dict[str, Any]:
        """Actually execute the smoke-test command and capture real output."""
        if not repo_path or not Path(repo_path).is_dir():
            return {
                "passed": False,
                "exit_code": None,
                "stdout": "",
                "stderr": f"Repo path does not exist: {repo_path}",
                "error": "No generated repo path",
            }
        try:
            proc = subprocess.run(
                shlex.split(smoke_command, posix=True),
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            return {
                "passed": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "exit_code": None,
                "stdout": "",
                "stderr": f"Smoke test timed out after 60 seconds.",
                "error": "timeout",
            }
        except OSError as exc:
            return {
                "passed": False,
                "exit_code": None,
                "stdout": "",
                "stderr": f"Failed to start smoke test: {exc}",
                "error": "startup_failure",
            }

    def revise_code(
        state: dict[str, Any],
        revision_suggestions: list[str],
    ) -> ImplementationBundle:
        revision_count = int(state.get("code_revision_count") or 0)
        max_revisions = int(state.get("code_max_revisions") or DEFAULT_CODE_MAX_REVISIONS)
        progress(
            "Reproduction Implementation Agent revising code with review feedback "
            f"(attempt {revision_count + 1}/{max_revisions})"
        )
        blueprint = ImplementationBlueprint.model_validate(
            result.get("implementation_blueprint") or {}
        )
        implementation_input = {
            "research_understanding": state.get("research_understanding") or {},
            "repository_understanding": state.get("repository_understanding") or {},
            "reproduction_plan": state.get("reproduction_plan") or {},
            "implementation_blueprint": result.get("implementation_blueprint") or {},
            "paper_text": state.get("paper_text", ""),
            "hardware": hardware,
            "gpu_info": gpu_info,
            "goal": goal,
            "user_idea": user_idea,
            "approved_resource_links": result["resource_links"],
            "revision_suggestions": revision_suggestions,
            "sandbox_verification_errors": [
                r for r in (state.get("sandbox_verification") or {}).get("results", [])
                if not r.get("passed")
            ],
            "method_spec": json.dumps(
                ResearchUnderstandingAgent.build_method_spec(
                    PaperUnderstanding.model_validate(
                        state.get("research_understanding") or {}
                    )
                ).model_dump(mode="json"),
                indent=2,
            ) if state.get("research_understanding") else "{}",
        }
        implementation = _run_structured_stage(
            result,
            "Reproduction Implementation Agent (revision)",
            ReproductionImplementationAgent,
            client,
            implementation_input,
            fallback=lambda: ReproductionImplementationAgent(
                client
            ).build_mock(implementation_input),
        )
        result["implementation_bundle"] = implementation.model_dump(mode="json")
        result["code_quality"] = assess_implementation_quality(
            implementation,
            blueprint=blueprint,
        )
        result["blueprint_quality"] = result["code_quality"]["metrics"].get(
            "blueprint",
            {},
        )
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
        except Exception as exc:
            _record_error(result, "Generated Code Writer (revision)", exc)
        return implementation

    def diagnose_execution(
        reproduction_plan: dict[str, Any],
        command_results: list[dict[str, Any]],
    ) -> ExecutionDiagnosis:
        progress("Execution & Diagnosis Agent assessing feasibility")
        diagnosis_input = {
            "command_results": command_results,
            "reproduction_plan": reproduction_plan,
        }
        diagnosis = _run_structured_stage(
            result,
            "Execution & Diagnosis Agent",
            ExecutionDiagnosisAgent,
            client,
            diagnosis_input,
            fallback=lambda: ExecutionDiagnosisAgent(client).build_mock(
                diagnosis_input
            ),
        )
        result["execution_diagnosis"] = diagnosis.model_dump(mode="json")
        return diagnosis

    def build_outputs(state: dict[str, Any]) -> dict[str, Any]:
        result["command_plans"] = list(state.get("command_plans") or [])
        result["command_route"] = state.get("command_route") or "safe"
        result["pending_human_review"] = state.get("pending_human_review")
        result["command_results"] = list(state.get("command_results") or [])
        diagnosis = ExecutionDiagnosis.model_validate(
            state.get("execution_diagnosis") or {}
        )
        _save_outputs(
            result,
            state.get("repo_scan") or generated_repo_scan,
            render_execution_diagnosis(diagnosis),
            output_dir=output_dir,
        )
        return {
            "reproduction_plan": str(output_dir / "reproduction_plan.md"),
            "run_script": str(output_dir / "run.sh"),
            "report": str(output_dir / "report.md"),
            "manifest": str(output_dir / "manifest.json"),
        }

    use_sync_hitl = bool(hitl and hitl.sync_mode)
    checkpointer = get_shared_checkpointer() if use_sync_hitl else None
    interrupt_after = REPRODUCE_HITL_INTERRUPT_AFTER if use_sync_hitl else None
    thread_id = hitl_thread_id or (new_hitl_thread_id() if use_sync_hitl else None)

    graph = build_reproduce_graph(
        ReproduceGraphDependencies(
            parse_paper=parse_paper_dependency,
            understand_research=understand_research,
            prepare_repository=prepare_repository_dependency,
            understand_repository=understand_repository,
            plan_reproduction=plan_reproduction,
            generate_implementation=generate_implementation,
            review_code=review_code,
            second_review_code=second_review_code,
            sandbox_verify=sandbox_verify_fn,
            revise_code=revise_code,
            diagnose_execution=diagnose_execution,
            build_outputs=build_outputs,
        ),
        checkpointer=checkpointer,
        interrupt_after=interrupt_after,
    )

    if hitl_thread_id and hitl_action:
        if hitl_action == "retry" and hitl_stage and hitl_correction.strip():
            rerun_reproduce_stage(
                result,
                hitl_stage,
                hitl_correction,
                llm_client=client,
                output_dir=output_dir,
            )
            interrupt_node = get_interrupt_node(graph, hitl_thread_id)
            updates: dict[str, Any] = {}
            if interrupt_node == "research_understanding":
                updates["research_understanding"] = result["research_understanding"]
            elif interrupt_node == "reproduction_planner":
                updates["reproduction_plan"] = result["reproduction_plan"]
            if updates:
                graph.update_state(
                    build_graph_config(hitl_thread_id),
                    updates,
                    as_node=interrupt_node,
                )
        elif hitl_action == "reject" and hitl_stage == "research":
            result["paper_info"] = "[Research understanding rejected by user]"
            result["method_info"] = ""
            _record_error(result, "HITL: Research Understanding", "Rejected by user")
        elif hitl_action == "reject" and hitl_stage == "experiment":
            _record_error(result, "HITL: Reproduction Planner", "Rejected by user")
        elif hitl_action == "confirm":
            pass  # Resume the graph without modification
        state = resume_graph(graph, hitl_thread_id, hitl_action)
    else:
        state = invoke_until_pause_or_complete(
            graph,
            {
                "pdf_path": pdf_path,
                "paper_name": paper_name,
                "github_url": github_url,
                "hardware": hardware,
                "gpu_info": gpu_info,
                "goal": goal,
                "user_idea": user_idea,
                "generate_code": generate_code,
                "implementation_model": implementation_model,
                "code_revision_count": 0,
                "code_max_revisions": DEFAULT_CODE_MAX_REVISIONS,
                "command_results": [],
                "graph_trace": [],
                "errors": [],
            },
            str(thread_id) if use_sync_hitl else None,
        )

    _merge_graph_state_into_result(
        result,
        state,
        generate_code=generate_code,
        goal=goal,
    )

    if use_sync_hitl and thread_id and graph_is_interrupted(graph, str(thread_id)):
        interrupt_node = get_interrupt_node(graph, str(thread_id)) or ""
        result["pipeline_status"] = "hitl_paused"
        result["hitl_thread_id"] = str(thread_id)
        result["hitl_interrupt_node"] = interrupt_node
        result["hitl_stage"] = (
            "research" if interrupt_node == "research_understanding" else "experiment"
        )
        result["hitl_title"] = (
            "Paper Summary"
            if interrupt_node == "research_understanding"
            else "Experiment Plan"
        )
        _refresh_rendered_result_fields(result)
        result["hitl_content"] = render_interrupt_content(result, interrupt_node)
        return result

    _record_final_code_quality_status(
        result,
        state,
        generate_code=generate_code,
        goal=goal,
    )
    _finalize_status(result, client)
    if missing_paper_text:
        result["pipeline_status"] = "failed"
    return result
