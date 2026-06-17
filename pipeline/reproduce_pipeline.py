"""Converged four-agent Reproduce pipeline."""

from __future__ import annotations

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
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
    ResourceLink,
)
from tools.code_writer import materialize_implementation
from tools.llm_client import LLMClient, LLMClientError
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import analyze_pdf_quality, parse_pdf
from tools.repo_evidence_gatherer import gather_repo_evidence
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


def _save_outputs(
    result: PipelineResult,
    repo_scan: dict[str, Any] | None,
    diagnosis_text: str,
    output_dir: Path = OUTPUTS_DIR,
) -> None:
    reproduction_plan = build_reproduction_plan(result)
    result["run_sh"] = build_run_script(repo_scan, result.get("implementation_bundle"))
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
    result["graph_trace"] = list(state.get("graph_trace") or [])
    result["errors"].extend(state.get("errors") or [])
    _refresh_rendered_result_fields(result)


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
    hitl_thread_id: str | None = None,
    hitl_action: str | None = None,
    hitl_stage: str | None = None,
    hitl_correction: str = "",
) -> PipelineResult:
    """Run the backward-compatible Reproduce API through LangGraph."""
    result = _initial_result()
    init_stage_sources(result)
    paper_name = safe_output_name(paper_name)
    output_dir = resolve_output_dir({"paper_name": paper_name})
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
        implementation_input = {
            "research_understanding": state.get("research_understanding") or {},
            "repository_understanding": state.get("repository_understanding") or {},
            "reproduction_plan": state.get("reproduction_plan") or {},
            "paper_text": state.get("paper_text", ""),
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
        }
        review = _run_structured_stage(
            result,
            "Code Review Agent",
            CodeReviewAgent,
            client,
            review_input,
            fallback=lambda: CodeReviewAgent(client).build_mock(review_input),
        )
        progress(f"Code review verdict: {review.verdict} (score: {review.overall_score})")
        return review

    def revise_code(
        state: dict[str, Any],
        revision_suggestions: list[str],
    ) -> ImplementationBundle:
        progress("Reproduction Implementation Agent revising code with review feedback")
        implementation_input = {
            "research_understanding": state.get("research_understanding") or {},
            "repository_understanding": state.get("repository_understanding") or {},
            "reproduction_plan": state.get("reproduction_plan") or {},
            "paper_text": state.get("paper_text", ""),
            "hardware": hardware,
            "gpu_info": gpu_info,
            "goal": goal,
            "user_idea": user_idea,
            "approved_resource_links": result["resource_links"],
            "revision_suggestions": revision_suggestions,
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
                "code_max_revisions": 1,
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

    _finalize_status(result, client)
    if missing_paper_text:
        result["pipeline_status"] = "failed"
    return result
