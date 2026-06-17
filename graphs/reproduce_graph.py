"""LangGraph orchestration for the PaperPilot Reproduce workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from graphs.subgraphs.command_review_graph import (
    build_pending_review,
    classify_command_plans,
    summarize_unexecuted_commands,
)
from runtime.graph_state import ReproduceState
from runtime.routing import route_after_code_review, route_command_plans
from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)
from schemas.code_review_schema import CodeReview


@dataclass(frozen=True)
class ReproduceGraphDependencies:
    parse_paper: Callable[[str], str]
    understand_research: Callable[[str, str], PaperUnderstanding | dict[str, Any]]
    prepare_repository: Callable[[str], dict[str, Any]]
    understand_repository: Callable[
        [dict[str, Any], dict[str, Any], str],
        RepositoryUnderstanding | dict[str, Any],
    ]
    plan_reproduction: Callable[
        [dict[str, Any], dict[str, Any], dict[str, Any]],
        ReproductionPlan | dict[str, Any],
    ]
    generate_implementation: Callable[
        [dict[str, Any]],
        ImplementationBundle | dict[str, Any],
    ]
    review_code: Callable[
        [dict[str, Any]],
        CodeReview | dict[str, Any],
    ]
    revise_code: Callable[
        [dict[str, Any], list[str]],
        ImplementationBundle | dict[str, Any],
    ]
    diagnose_execution: Callable[
        [dict[str, Any], list[dict[str, Any]]],
        ExecutionDiagnosis | dict[str, Any],
    ]
    build_outputs: Callable[[dict[str, Any]], dict[str, Any]]


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def build_reproduce_graph(
    dependencies: ReproduceGraphDependencies,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_after: tuple[str, ...] | None = None,
):
    """Compile the parallel evidence, planning, and risk-routing workflow."""

    def parse_paper_node(state: ReproduceState) -> dict[str, Any]:
        try:
            text = dependencies.parse_paper(str(state.get("pdf_path") or ""))
            return {"paper_text": text, "graph_trace": ["parse_paper"]}
        except Exception as exc:
            return {
                "paper_text": "",
                "errors": [f"[PDF Parser] {exc}"],
                "graph_trace": ["parse_paper"],
            }

    def research_understanding(state: ReproduceState) -> dict[str, Any]:
        research = dependencies.understand_research(
            str(state.get("paper_text") or ""),
            str(state.get("user_idea") or ""),
        )
        return {
            "research_understanding": _as_dict(research),
            "graph_trace": ["research_understanding"],
        }

    def prepare_repository_node(state: ReproduceState) -> dict[str, Any]:
        repo_scan = dependencies.prepare_repository(
            str(state.get("github_url") or "")
        )
        return {
            "repo_scan": repo_scan,
            "repo_path": str(repo_scan.get("repo_path") or ""),
            "graph_trace": ["prepare_repository"],
        }

    def repository_understanding(state: ReproduceState) -> dict[str, Any]:
        repository = dependencies.understand_repository(
            dict(state.get("research_understanding") or {}),
            dict(state.get("repo_scan") or {}),
            str(state.get("github_url") or ""),
        )
        return {
            "repository_understanding": _as_dict(repository),
            "graph_trace": ["repository_understanding"],
        }

    def reproduction_planner(state: ReproduceState) -> dict[str, Any]:
        inputs = {
            "goal": state.get("goal", "minimal training experiment"),
            "hardware": state.get("hardware", "Not provided"),
            "gpu_info": state.get("gpu_info", ""),
            "user_idea": state.get("user_idea", ""),
        }
        plan = ReproductionPlan.model_validate(
            dependencies.plan_reproduction(
                dict(state.get("research_understanding") or {}),
                dict(state.get("repository_understanding") or {}),
                inputs,
            )
        )
        return {
            "reproduction_plan": plan.model_dump(mode="json"),
            "command_plans": [
                item.model_dump(mode="json") for item in plan.command_plans
            ],
            "graph_trace": ["reproduction_planner"],
        }

    def command_risk_router(state: ReproduceState) -> dict[str, Any]:
        classified = classify_command_plans(
            list(state.get("command_plans") or [])
        )
        route = route_command_plans(classified)
        cwd = (
            str(state.get("repo_path") or "")
            or str((state.get("repo_scan") or {}).get("repo_path") or "")
        )
        return {
            "command_plans": classified,
            "command_route": route,
            "pending_human_review": build_pending_review(classified, cwd),
            "graph_trace": ["command_risk_router"],
        }

    def route_commands(state: ReproduceState) -> str:
        return str(state.get("command_route") or "safe")

    def command_summary(route: str):
        def summarize(state: ReproduceState) -> dict[str, Any]:
            plans = list(state.get("command_plans") or [])
            return {
                "command_results": summarize_unexecuted_commands(plans, route),
                "graph_trace": [f"{route}_summary"],
            }

        return summarize

    def reproduction_implementation(state: ReproduceState) -> dict[str, Any]:
        implementation = dependencies.generate_implementation(dict(state))
        return {
            "implementation_bundle": _as_dict(implementation),
            "graph_trace": ["reproduction_implementation"],
        }

    def code_review(state: ReproduceState) -> dict[str, Any]:
        review = dependencies.review_code(dict(state))
        return {
            "code_review": _as_dict(review),
            "graph_trace": ["code_review"],
        }

    def code_revise(state: ReproduceState) -> dict[str, Any]:
        code_review = dict(state.get("code_review") or {})
        suggestions = list(code_review.get("revision_suggestions") or [])
        implementation = dependencies.revise_code(dict(state), suggestions)
        revision_count = int(state.get("code_revision_count") or 0) + 1
        return {
            "implementation_bundle": _as_dict(implementation),
            "code_revision_count": revision_count,
            "graph_trace": ["code_revise"],
        }

    def execution_diagnosis(state: ReproduceState) -> dict[str, Any]:
        diagnosis = dependencies.diagnose_execution(
            dict(state.get("reproduction_plan") or {}),
            list(state.get("command_results") or []),
        )
        return {
            "execution_diagnosis": _as_dict(diagnosis),
            "graph_trace": ["execution_diagnosis"],
        }

    def build_outputs(state: ReproduceState) -> dict[str, Any]:
        return {
            "report_paths": dependencies.build_outputs(dict(state)),
            "graph_trace": ["build_outputs"],
        }

    builder = StateGraph(ReproduceState)
    builder.add_node("parse_paper", parse_paper_node)
    builder.add_node("research_understanding", research_understanding)
    builder.add_node("prepare_repository", prepare_repository_node)
    builder.add_node("repository_understanding", repository_understanding)
    builder.add_node("reproduction_planner", reproduction_planner)
    builder.add_node("command_risk_router", command_risk_router)
    builder.add_node("safe_summary", command_summary("safe"))
    builder.add_node("review_summary", command_summary("review"))
    builder.add_node("blocked_summary", command_summary("blocked"))
    builder.add_node("reproduction_implementation", reproduction_implementation)
    builder.add_node("code_review", code_review)
    builder.add_node("code_revise", code_revise)
    builder.add_node("execution_diagnosis", execution_diagnosis)
    builder.add_node("build_outputs", build_outputs)
    builder.add_edge(START, "parse_paper")
    builder.add_edge("parse_paper", "research_understanding")
    builder.add_edge("parse_paper", "prepare_repository")
    builder.add_edge(
        ["research_understanding", "prepare_repository"],
        "repository_understanding",
    )
    builder.add_edge("repository_understanding", "reproduction_planner")
    builder.add_edge("reproduction_planner", "command_risk_router")
    builder.add_conditional_edges(
        "command_risk_router",
        route_commands,
        {
            "safe": "safe_summary",
            "review": "review_summary",
            "blocked": "blocked_summary",
        },
    )
    for summary in ("safe_summary", "review_summary", "blocked_summary"):
        builder.add_edge(summary, "reproduction_implementation")
    builder.add_edge("reproduction_implementation", "code_review")
    builder.add_conditional_edges(
        "code_review",
        route_after_code_review,
        {
            "accept": "execution_diagnosis",
            "revise": "code_revise",
            "finish_with_warnings": "execution_diagnosis",
        },
    )
    builder.add_edge("code_revise", "code_review")
    builder.add_edge("execution_diagnosis", "build_outputs")
    builder.add_edge("build_outputs", END)
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_after:
        compile_kwargs["interrupt_after"] = list(interrupt_after)
    return builder.compile(**compile_kwargs)
