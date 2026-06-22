"""LangGraph orchestration for Productize proposal and execution workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from graphs.subgraphs.product_revision_graph import build_revision_record
from runtime.graph_state import ProductizeState
from runtime.routing import route_after_evaluation
from schemas.composition_schema import PaperCapabilityCard, ResearchSynthesis
from schemas.evaluation_schema import ProductEvaluation
from schemas.product_schema import PRD, ProductOpportunity, ProductPlan, ProductProposal, PrototypePlan


@dataclass(frozen=True)
class ProductizeProposalDependencies:
    extract_capability: Callable[[dict[str, Any]], PaperCapabilityCard | dict[str, Any]]
    synthesize_research: Callable[
        [list[dict[str, Any]], list[dict[str, Any]]],
        ResearchSynthesis | dict[str, Any],
    ]
    plan_product: Callable[
        [dict[str, Any], str, str, str],
        ProductPlan | dict[str, Any],
    ]


@dataclass(frozen=True)
class ProductizeExecutionDependencies:
    select_template: Callable[[dict[str, Any]], str]
    build_prototype: Callable[
        [dict[str, Any], str, dict[str, Any]],
        PrototypePlan | dict[str, Any],
    ]
    evaluate_product: Callable[
        [
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
        ],
        ProductEvaluation | dict[str, Any],
    ]
    revise_product_plan: Callable[
        [dict[str, Any], dict[str, Any]],
        ProductPlan | dict[str, Any],
    ]
    revise_prototype: Callable[
        [dict[str, Any], dict[str, Any], dict[str, Any]],
        PrototypePlan | dict[str, Any],
    ]
    scaffold_product: Callable[[dict[str, Any]], dict[str, Any]]
    inspect_product: Callable[[dict[str, Any]], dict[str, Any]]


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _normalize_paper(paper: dict[str, Any], index: int) -> dict[str, Any]:
    normalized = dict(paper)
    normalized.setdefault("paper_id", f"paper-{index}")
    normalized.setdefault("title", f"Paper {index}")
    normalized.setdefault("paper_info", "")
    normalized.setdefault("method_info", "")
    normalized.setdefault("repo_info", "")
    normalized.setdefault("repo_path", "")
    return normalized


def _build_proposals(
    product_plan: ProductPlan,
    target_user: str,
    product_goal: str,
) -> list[dict[str, Any]]:
    proposals: list[ProductProposal] = []
    opportunities = list(product_plan.opportunities)
    if not opportunities:
        from schemas.product_schema import ProductOpportunity as _PO
        opportunities = [
            _PO(
                idea_name="Product Opportunity 1",
                target_user=target_user,
                core_value=product_goal,
                technical_feasibility=5, demo_feasibility=5,
                model_availability=3, data_requirement=5,
                integration_risk=2, user_value=4,
                course_presentation_value=5, paper_faithfulness=4,
                multi_paper_coherence=4, mock_first_suitability=5,
                overall_score=4.0,
                reason="Default opportunity based on paper capabilities.",
            ),
        ]

    for opportunity in opportunities[:3]:
        per_opportunity_prd = PRD(
            **{
                **product_plan.prd.model_dump(mode="json"),
                "product_name": opportunity.idea_name,
            }
        )
        proposals.append(
            ProductProposal(
                product_name=opportunity.idea_name,
                target_user=opportunity.target_user,
                product_goal=product_goal,
                jtbd=product_plan.jtbd,
                opportunities=[opportunity],
                value_proposition=product_plan.value_proposition,
                prd=per_opportunity_prd,
                mvp_scope=product_plan.mvp_scope,
                risks=product_plan.risks,
            )
        )
    if not proposals:
        opps_for_fallback = product_plan.opportunities or [
            ProductOpportunity(
                idea_name=product_plan.prd.product_name or product_plan.selected_product,
                target_user=target_user,
                core_value=product_goal,
                technical_feasibility=5, demo_feasibility=5,
                model_availability=3, data_requirement=5,
                integration_risk=2, user_value=4,
                course_presentation_value=5, paper_faithfulness=4,
                multi_paper_coherence=4, mock_first_suitability=5,
                overall_score=4.0,
                reason="Default opportunity.",
            )
        ]
        proposals.append(
            ProductProposal(
                product_name=product_plan.prd.product_name
                or product_plan.selected_product,
                target_user=target_user,
                product_goal=product_goal,
                jtbd=product_plan.jtbd,
                opportunities=opps_for_fallback,
                value_proposition=product_plan.value_proposition,
                prd=product_plan.prd,
                mvp_scope=product_plan.mvp_scope,
                risks=product_plan.risks,
            )
        )
    return [proposal.model_dump(mode="json") for proposal in proposals]


def build_productize_proposal_graph(
    dependencies: ProductizeProposalDependencies,
    *,
    checkpointer=None,
    interrupt_after: tuple[str, ...] | None = None,
):
    """Compile the per-paper fan-out and proposal-building graph."""

    def normalize_inputs(state: ProductizeState) -> dict[str, Any]:
        papers = [
            _normalize_paper(paper, index)
            for index, paper in enumerate(state.get("papers") or [], 1)
        ]
        return {"papers": papers, "graph_trace": ["normalize_inputs"]}

    def prepare_capability_jobs(state: ProductizeState) -> dict[str, Any]:
        return {
            "capability_jobs": list(state.get("papers") or []),
            "graph_trace": ["prepare_capability_jobs"],
        }

    def dispatch_capability_jobs(
        state: ProductizeState,
    ) -> list[Send] | str:
        jobs = state.get("capability_jobs") or []
        if not jobs:
            return "synthesize_research"
        return [
            Send("extract_capability_card", {"capability_job": job})
            for job in jobs
        ]

    def extract_capability_card(state: ProductizeState) -> dict[str, Any]:
        paper = dict(state["capability_job"])
        try:
            card = PaperCapabilityCard.model_validate(
                dependencies.extract_capability(paper)
            )
            return {
                "capability_cards": [card.model_dump(mode="json")],
                "graph_trace": ["extract_capability_card"],
            }
        except Exception as exc:
            paper_id = paper.get("paper_id") or "unknown"
            return {
                "errors": [f"[Capability {paper_id}] {exc}"],
                "graph_trace": ["extract_capability_card"],
            }

    def synthesize_research(state: ProductizeState) -> dict[str, Any]:
        papers = list(state.get("papers") or [])
        cards = list(state.get("capability_cards") or [])
        try:
            synthesis = ResearchSynthesis.model_validate(
                dependencies.synthesize_research(papers, cards)
            )
        except Exception as exc:
            synthesis = ResearchSynthesis(
                capability_cards=[
                    PaperCapabilityCard.model_validate(card) for card in cards
                ]
            )
            return {
                "research_synthesis": synthesis.model_dump(mode="json"),
                "errors": [f"[Research Synthesis] {exc}"],
                "graph_trace": ["synthesize_research"],
            }
        return {
            "research_synthesis": synthesis.model_dump(mode="json"),
            "graph_trace": ["synthesize_research"],
        }

    def plan_product(state: ProductizeState) -> dict[str, Any]:
        plan = ProductPlan.model_validate(
            dependencies.plan_product(
                dict(state.get("research_synthesis") or {}),
                str(state.get("target_user") or ""),
                str(state.get("product_goal") or ""),
                str(state.get("user_idea") or ""),
            )
        )
        return {
            "product_plan": plan.model_dump(mode="json"),
            "graph_trace": ["plan_product"],
        }

    def build_proposals(state: ProductizeState) -> dict[str, Any]:
        plan = ProductPlan.model_validate(state["product_plan"])
        return {
            "proposals": _build_proposals(
                plan,
                str(state.get("target_user") or ""),
                str(state.get("product_goal") or ""),
            ),
            "graph_trace": ["build_proposals"],
        }

    builder = StateGraph(ProductizeState)
    builder.add_node("normalize_inputs", normalize_inputs)
    builder.add_node("prepare_capability_jobs", prepare_capability_jobs)
    builder.add_node("extract_capability_card", extract_capability_card)
    builder.add_node("synthesize_research", synthesize_research)
    builder.add_node("plan_product", plan_product)
    builder.add_node("build_proposals", build_proposals)
    builder.add_edge(START, "normalize_inputs")
    builder.add_edge("normalize_inputs", "prepare_capability_jobs")
    builder.add_conditional_edges(
        "prepare_capability_jobs",
        dispatch_capability_jobs,
        ["extract_capability_card", "synthesize_research"],
    )
    builder.add_edge("extract_capability_card", "synthesize_research")
    builder.add_edge("synthesize_research", "plan_product")
    builder.add_edge("plan_product", "build_proposals")
    builder.add_edge("build_proposals", END)
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_after:
        compile_kwargs["interrupt_after"] = list(interrupt_after)
    return builder.compile(**compile_kwargs)


def _proposal_to_plan(proposal: ProductProposal) -> ProductPlan:
    return ProductPlan(
        jtbd=proposal.jtbd,
        value_proposition=proposal.value_proposition,
        opportunities=proposal.opportunities,
        selected_product=proposal.product_name,
        selection_reason=(
            f"Selected from {len(proposal.opportunities)} product opportunity/opportunities."
        ),
        prd=proposal.prd,
        mvp_scope=proposal.mvp_scope,
        risks=proposal.risks,
        limitations=[],
    )


def build_productize_execution_graph(
    dependencies: ProductizeExecutionDependencies,
    *,
    checkpointer=None,
    interrupt_after: tuple[str, ...] | None = None,
):
    """Compile bounded product revision and terminal artifact generation."""

    def prepare_selected_proposal(state: ProductizeState) -> dict[str, Any]:
        proposal = ProductProposal.model_validate(state["selected_proposal"])
        plan = _proposal_to_plan(proposal)
        return {
            "product_plan": plan.model_dump(mode="json"),
            "revision_count": int(state.get("revision_count") or 0),
            "max_revisions": int(state.get("max_revisions") or 1),
            "graph_trace": ["prepare_selected_proposal"],
        }

    def select_template(state: ProductizeState) -> dict[str, Any]:
        return {
            "template_type": dependencies.select_template(dict(state)),
            "graph_trace": ["select_template"],
        }

    def build_prototype(state: ProductizeState) -> dict[str, Any]:
        prototype = dependencies.build_prototype(
            dict(state["product_plan"]),
            str(state["template_type"]),
            {},
        )
        return {
            "prototype_plan": _as_dict(prototype),
            "graph_trace": ["build_prototype"],
        }

    def evaluate_product(state: ProductizeState) -> dict[str, Any]:
        evaluation = dependencies.evaluate_product(
            dict(state.get("research_synthesis") or {}),
            dict(state["product_plan"]),
            dict(state["prototype_plan"]),
            {},
        )
        return {
            "evaluation": _as_dict(evaluation),
            "graph_trace": ["evaluate_product"],
        }

    def revise_product_plan(state: ProductizeState) -> dict[str, Any]:
        evaluation = dict(state["evaluation"])
        plan = _as_dict(
            dependencies.revise_product_plan(
                dict(state["product_plan"]),
                evaluation,
            )
        )
        prototype = _as_dict(
            dependencies.build_prototype(
                plan,
                str(state["template_type"]),
                evaluation,
            )
        )
        revision = int(state.get("revision_count") or 0) + 1
        return {
            "product_plan": plan,
            "prototype_plan": prototype,
            "revision_count": revision,
            "revision_history": [
                build_revision_record(dict(state), "revise_product_plan")
            ],
            "graph_trace": ["revise_product_plan"],
        }

    def revise_prototype(state: ProductizeState) -> dict[str, Any]:
        evaluation = dict(state["evaluation"])
        prototype = dependencies.revise_prototype(
            dict(state["product_plan"]),
            dict(state["prototype_plan"]),
            evaluation,
        )
        revision = int(state.get("revision_count") or 0) + 1
        return {
            "prototype_plan": _as_dict(prototype),
            "revision_count": revision,
            "revision_history": [
                build_revision_record(dict(state), "revise_prototype")
            ],
            "graph_trace": ["revise_prototype"],
        }

    def finish(state: ProductizeState) -> dict[str, Any]:
        del state
        return {"graph_trace": ["finish"]}

    def finish_with_warnings(state: ProductizeState) -> dict[str, Any]:
        score = (state.get("evaluation") or {}).get("overall_score", 0)
        return {
            "issues": [
                {
                    "severity": "warning",
                    "message": (
                        f"Product evaluation remained below threshold at {score} "
                        "after the revision limit."
                    ),
                }
            ],
            "graph_trace": ["finish_with_warnings"],
        }

    def scaffold_product(state: ProductizeState) -> dict[str, Any]:
        return {
            "scaffold_result": dependencies.scaffold_product(dict(state)),
            "graph_trace": ["scaffold_product"],
        }

    def inspect_product(state: ProductizeState) -> dict[str, Any]:
        return {
            "inspection": dependencies.inspect_product(dict(state)),
            "graph_trace": ["inspect_product"],
        }

    def final_evaluation(state: ProductizeState) -> dict[str, Any]:
        evaluation = dependencies.evaluate_product(
            dict(state.get("research_synthesis") or {}),
            dict(state["product_plan"]),
            dict(state["prototype_plan"]),
            dict(state.get("inspection") or {}),
        )
        return {
            "evaluation": _as_dict(evaluation),
            "graph_trace": ["final_evaluation"],
        }

    builder = StateGraph(ProductizeState)
    builder.add_node("prepare_selected_proposal", prepare_selected_proposal)
    builder.add_node("select_template", select_template)
    builder.add_node("build_prototype", build_prototype)
    builder.add_node("evaluate_product", evaluate_product)
    builder.add_node("revise_product_plan", revise_product_plan)
    builder.add_node("revise_prototype", revise_prototype)
    builder.add_node("finish", finish)
    builder.add_node("finish_with_warnings", finish_with_warnings)
    builder.add_node("scaffold_product", scaffold_product)
    builder.add_node("inspect_product", inspect_product)
    builder.add_node("final_evaluation", final_evaluation)
    builder.add_edge(START, "prepare_selected_proposal")
    builder.add_edge("prepare_selected_proposal", "select_template")
    builder.add_edge("select_template", "build_prototype")
    builder.add_edge("build_prototype", "evaluate_product")
    builder.add_conditional_edges(
        "evaluate_product",
        route_after_evaluation,
        {
            "finish": "finish",
            "finish_with_warnings": "finish_with_warnings",
            "revise_product_plan": "revise_product_plan",
            "revise_prototype": "revise_prototype",
        },
    )
    builder.add_edge("revise_product_plan", "evaluate_product")
    builder.add_edge("revise_prototype", "evaluate_product")
    builder.add_edge("finish", "scaffold_product")
    builder.add_edge("finish_with_warnings", "scaffold_product")
    builder.add_edge("scaffold_product", "inspect_product")
    builder.add_edge("inspect_product", "final_evaluation")
    builder.add_edge("final_evaluation", END)
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_after:
        compile_kwargs["interrupt_after"] = list(interrupt_after)
    return builder.compile(**compile_kwargs)
