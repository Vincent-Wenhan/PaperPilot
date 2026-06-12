"""Theory-guided, multi-paper Productize Mode orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from agents import (
    ProductEvaluatorAgent,
    ProductPlannerAgent,
    PrototypeBuilderAgent,
    ResearchSynthesizerAgent,
)
from productize import inspect_generated_product, scaffold_product, select_product_template
from pipeline.productize_renderers import render_opportunities
from schemas.composition_schema import ResearchSynthesis
from schemas.evaluation_schema import ProductEvaluation
from schemas.product_schema import (
    ProductOpportunityList,
    ProductPlan,
    PrototypePlan,
)
from tools.llm_client import LLMClient, LLMClientError

ProductResult = dict[str, Any]
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _record_error(result: ProductResult, stage: str, error: object) -> None:
    result["errors"].append(f"[{stage}] {error}")


def _llm_client_key(client: LLMClient) -> str:
    return f"{getattr(client, 'base_url', '')}|{getattr(client, 'model', '')}"


def _run_structured_stage(
    result: ProductResult,
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


def _normalize_papers(
    papers: list[dict[str, Any]] | None,
    paper_info: str,
    method_info: str,
    repo_info: str,
    repo_path: str,
) -> list[dict[str, Any]]:
    source = papers or [
        {
            "paper_id": "paper-1",
            "title": "Paper 1",
            "paper_info": paper_info,
            "method_info": method_info,
            "repo_info": repo_info,
            "repo_path": repo_path,
        }
    ]
    normalized: list[dict[str, Any]] = []
    for index, paper in enumerate(source, 1):
        item = dict(paper)
        item.setdefault("paper_id", f"paper-{index}")
        item.setdefault("title", f"Paper {index}")
        item.setdefault("paper_info", "")
        item.setdefault("method_info", "")
        item.setdefault("repo_info", "")
        item.setdefault("repo_path", "")
        normalized.append(item)
    return normalized


def _product_plan_to_markdown(plan: ProductPlan) -> str:
    lines = [
        "# Product Plan",
        "",
        f"## Selected Product\n\n{plan.selected_product}",
        "",
        f"## Selection Reason\n\n{plan.selection_reason}",
        "",
        f"## JTBD\n\n{plan.jtbd}",
        "",
        "## PRD",
        "",
        f"### Problem\n\n{plan.prd.problem_statement}",
        "",
        "### Core Features",
        *[f"- {item}" for item in plan.prd.core_features],
        "",
        "### User Flow",
        *[f"{index}. {item}" for index, item in enumerate(plan.prd.user_flow, 1)],
        "",
        "## MVP / MoSCoW",
        "",
        "### Must Have",
        *[f"- {item}" for item in plan.mvp_scope.must_have],
        "",
        "### Should Have",
        *[f"- {item}" for item in plan.mvp_scope.should_have],
        "",
        "### Could Have",
        *[f"- {item}" for item in plan.mvp_scope.could_have],
        "",
        "### Won't Have",
        *[f"- {item}" for item in plan.mvp_scope.wont_have],
    ]
    return "\n".join(lines)


def _prototype_plan_to_markdown(plan: PrototypePlan) -> str:
    lines = [
        "# Prototype Plan",
        "",
        f"**Template:** {plan.template_type}",
        f"**Mock First:** {plan.mock_first}",
        "",
        "## Page Structure",
        *[f"- {item}" for item in plan.page_structure],
        "",
        "## Adapter Boundary",
        *[f"- {item}" for item in plan.adapter_boundary],
        "",
        "## Real Integration Placeholder",
        plan.real_integration_placeholder,
    ]
    return "\n".join(lines)


def _evaluation_to_markdown(evaluation: ProductEvaluation) -> str:
    lines = [
        "# Product Evaluation",
        "",
        f"**Overall Score:** {evaluation.overall_score}/5",
        f"**Demo Readiness:** {evaluation.demo_readiness}",
        "",
        "## Revision Suggestions",
    ]
    lines.extend(
        f"- {item}" for item in evaluation.revision_suggestions
    )
    if not evaluation.revision_suggestions:
        lines.append("- No mandatory revision identified.")
    lines.extend(["", "## Safety Warnings"])
    lines.extend(f"- {item}" for item in evaluation.safety_warnings)
    return "\n".join(lines)


def run_productize_pipeline(
    paper_info: str,
    method_info: str,
    repo_info: str,
    repo_path: str,
    target_user: str,
    product_goal: str,
    llm_client: LLMClient | None = None,
    preferred_type: str = "auto",
    output_dir: str | Path = "generated_product",
    progress_callback: Callable[[str], None] | None = None,
    user_idea: str = "",
    papers: list[dict[str, Any]] | None = None,
) -> ProductResult:
    """Generate a structured mock-first product from one or more papers.

    Existing single-paper callers remain valid. Multi-paper callers may pass
    ``papers`` with paper, method, and optional repository context per item.
    """
    result: ProductResult = {
        "pipeline_status": "initializing",
        "llm_attempts": 0,
        "llm_failures": 0,
        "llm_unavailable_clients": [],
        "papers": [],
        "research_synthesis": {},
        "capability_cards": [],
        "capability_map": {},
        "composition_plan": {},
        "opportunities": "",
        "product_plan": {},
        "prd": {},
        "mvp_scope": {},
        "product_spec": "",
        "template_type": "",
        "prototype_plan": {},
        "adapter_plan": "",
        "frontend_plan": "",
        "scaffold_result": {},
        "inspection": {},
        "evaluation": {},
        "test_report": "",
        "errors": [],
    }
    client = llm_client or LLMClient()
    normalized_papers = _normalize_papers(
        papers,
        paper_info,
        method_info,
        repo_info,
        repo_path,
    )
    result["papers"] = normalized_papers
    effective_repo_path = repo_path or next(
        (
            str(paper.get("repo_path") or "")
            for paper in normalized_papers
            if paper.get("repo_path")
        ),
        "",
    )

    def progress(stage: str) -> None:
        if progress_callback:
            progress_callback(stage)

    progress("Research Synthesizer Agent analyzing paper capabilities")
    synthesis = _run_structured_stage(
        result,
        "Research Synthesizer Agent",
        ResearchSynthesizerAgent,
        client,
        {
            "papers": normalized_papers,
            "target_domain": product_goal,
            "user_goal": user_idea,
        },
        fallback=lambda: ResearchSynthesizerAgent(client).build_mock(
            {"papers": normalized_papers}
        ),
    )
    result["research_synthesis"] = synthesis.model_dump(mode="json")
    result["capability_cards"] = result["research_synthesis"]["capability_cards"]
    result["capability_map"] = result["research_synthesis"]["capability_map"]
    result["composition_plan"] = result["research_synthesis"]["composition_plan"]

    progress("Product Planner Agent building PRD and MVP")
    product_plan = _run_structured_stage(
        result,
        "Product Planner Agent",
        ProductPlannerAgent,
        client,
        {
            "research_synthesis": result["research_synthesis"],
            "target_user": target_user,
            "product_goal": product_goal,
            "user_idea": user_idea,
        },
        fallback=lambda: ProductPlannerAgent(client).build_mock(
            {
                "research_synthesis": result["research_synthesis"],
                "target_user": target_user,
                "product_goal": product_goal,
            }
        ),
    )
    result["product_plan"] = product_plan.model_dump(mode="json")
    result["prd"] = result["product_plan"]["prd"]
    result["mvp_scope"] = result["product_plan"]["mvp_scope"]
    result["opportunities"] = render_opportunities(
        ProductOpportunityList(opportunities=product_plan.opportunities)
    )
    if user_idea:
        result["opportunities"] += f"\n\n## User's Own Idea\n{user_idea}"
    result["product_spec"] = _product_plan_to_markdown(product_plan)

    progress("Selecting product template")
    try:
        result["template_type"] = select_product_template(
            " ".join(str(item["paper_info"]) for item in normalized_papers),
            " ".join(str(item["method_info"]) for item in normalized_papers),
            " ".join(str(item["repo_info"]) for item in normalized_papers),
            result["product_spec"],
            preferred_type,
        )
    except Exception as exc:
        _record_error(result, "Product Template Selection", exc)
        result["template_type"] = "file"

    progress("Prototype Builder Agent planning interface and adapter")
    prototype_plan = _run_structured_stage(
        result,
        "Prototype Builder Agent",
        PrototypeBuilderAgent,
        client,
        {
            "product_plan": result["product_plan"],
            "template_type": result["template_type"],
        },
        fallback=lambda: PrototypeBuilderAgent(client).build_mock(
            {
                "product_plan": result["product_plan"],
                "template_type": result["template_type"],
            }
        ),
    )
    result["prototype_plan"] = prototype_plan.model_dump(mode="json")
    result["adapter_plan"] = _prototype_plan_to_markdown(prototype_plan)
    result["frontend_plan"] = result["adapter_plan"]

    progress("Generating product scaffold")
    try:
        result["scaffold_result"] = scaffold_product(
            template_type=result["template_type"],
            product_spec=result["product_spec"],
            adapter_plan=result["adapter_plan"],
            frontend_plan=result["frontend_plan"],
            repo_path=effective_repo_path,
            output_dir=output_dir,
        )
    except Exception as exc:
        _record_error(result, "Product Scaffold", exc)
        result["scaffold_result"] = {
            "output_dir": str(output_dir),
            "files": [],
            "backup_dir": "",
            "success": False,
            "message": str(exc),
        }

    progress("Inspecting generated product")
    try:
        result["inspection"] = inspect_generated_product(output_dir)
    except Exception as exc:
        _record_error(result, "Product Inspector", exc)
        result["inspection"] = {
            "exists": False,
            "missing_files": [],
            "files": [],
            "can_run_mock": False,
            "readme_has_run_command": False,
            "syntax_ok": False,
            "compile_errors": [str(exc)],
            "notes": ["Product inspection failed."],
        }

    progress("Product Evaluator Agent scoring prototype")
    evaluation = _run_structured_stage(
        result,
        "Product Evaluator Agent",
        ProductEvaluatorAgent,
        client,
        {
            "research_synthesis": result["research_synthesis"],
            "product_plan": result["product_plan"],
            "prototype_plan": result["prototype_plan"],
            "inspection": result["inspection"],
        },
        fallback=lambda: ProductEvaluatorAgent(client).build_mock(
            {
                "research_synthesis": result["research_synthesis"],
                "inspection": result["inspection"],
            }
        ),
    )
    result["evaluation"] = evaluation.model_dump(mode="json")
    result["test_report"] = _evaluation_to_markdown(evaluation)
    if client.mock_mode:
        result["pipeline_status"] = "mock"
    elif result["llm_failures"] and result["llm_failures"] == result["llm_attempts"]:
        result["pipeline_status"] = "failed"
    elif result["errors"]:
        result["pipeline_status"] = "degraded"
    else:
        result["pipeline_status"] = "complete"
    return result
