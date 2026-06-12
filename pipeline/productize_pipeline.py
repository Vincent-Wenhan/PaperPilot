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
from pipeline.hitl_context import PipelineHITL
from pipeline.hitl_renderers import render_capability_cards
from schemas.composition_schema import ResearchSynthesis
from schemas.evaluation_schema import ProductEvaluation
from schemas.product_schema import (
    MVPScope,
    PRD,
    ProductOpportunity,
    ProductOpportunityList,
    ProductPlan,
    ProductProposal,
    PrototypePlan,
    ValueProposition,
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


def _sanitise_dirname(name: str) -> str:
    """Keep only safe characters for directory names."""
    return "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_", " "}).strip().rstrip(". ") or "product"


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


def _proposal_to_markdown(proposal: ProductProposal) -> str:
    """Render a ProductProposal as markdown product spec."""
    lines = [
        "# Product Proposal",
        "",
        f"## Product Name\n\n{proposal.product_name}",
        "",
        f"## Target User\n\n{proposal.target_user}",
        "",
        f"## Product Goal\n\n{proposal.product_goal}",
        "",
        f"## JTBD\n\n{proposal.jtbd}",
        "",
        "## PRD",
        "",
        f"### Problem\n\n{proposal.prd.problem_statement}",
        "",
        "### Core Features",
        *[f"- {item}" for item in proposal.prd.core_features],
        "",
        "### User Flow",
        *[f"{index}. {item}" for index, item in enumerate(proposal.prd.user_flow, 1)],
        "",
        "## MVP / MoSCoW",
        "",
        "### Must Have",
        *[f"- {item}" for item in proposal.mvp_scope.must_have],
        "",
        "### Should Have",
        *[f"- {item}" for item in proposal.mvp_scope.should_have],
        "",
        "### Could Have",
        *[f"- {item}" for item in proposal.mvp_scope.could_have],
        "",
        "### Won't Have",
        *[f"- {item}" for item in proposal.mvp_scope.wont_have],
        "",
        "## Risks",
        *[f"- {item}" for item in proposal.risks],
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


def _product_plan_to_proposal(
    product_plan: ProductPlan,
    target_user: str,
    product_goal: str,
) -> ProductProposal:
    """Convert a ProductPlan into a ProductProposal."""
    return ProductProposal(
        product_name=product_plan.prd.product_name or product_plan.selected_product,
        target_user=target_user,
        product_goal=product_goal,
        jtbd=product_plan.jtbd,
        opportunities=product_plan.opportunities,
        value_proposition=product_plan.value_proposition,
        prd=product_plan.prd,
        mvp_scope=product_plan.mvp_scope,
        risks=product_plan.risks,
    )


def generate_proposals(
    papers: list[dict[str, Any]],
    target_user: str,
    product_goal: str,
    llm_client: LLMClient,
    user_idea: str = "",
    progress_callback: Callable[[str], None] | None = None,
    hitl: PipelineHITL | None = None,
) -> list[ProductProposal]:
    """Run ResearchSynthesizerAgent + ProductPlannerAgent and return proposals.

    Returns a list of ``ProductProposal`` instances (one per product opportunity).
    In mock mode, multiple proposals with varied names are generated.
    """
    errors: list[str] = []
    dummy_result: ProductResult = {"errors": errors}
    normalized_papers = _normalize_papers(papers, "", "", "", "")

    def progress(stage: str) -> None:
        if progress_callback:
            progress_callback(stage)

    progress("Research Synthesizer Agent analyzing paper capabilities")
    synthesis = _run_structured_stage(
        dummy_result,
        "Research Synthesizer Agent",
        ResearchSynthesizerAgent,
        llm_client,
        {
            "papers": normalized_papers,
            "target_domain": product_goal,
            "user_goal": user_idea,
        },
        fallback=lambda: ResearchSynthesizerAgent(llm_client).build_mock(
            {"papers": normalized_papers}
        ),
    )
    synthesis_dict = synthesis.model_dump(mode="json")

    # HITL: confirm capability cards before product planning
    if hitl:
        cards_text = render_capability_cards(synthesis)
        hitl_result = hitl.request_confirmation("capabilities", "Capability Cards", cards_text)
        if hitl_result == "retry":
            correction = hitl.get_correction("capabilities")
            progress("Research Synthesizer Agent retrying with feedback")
            synthesis = _run_structured_stage(
                dummy_result,
                "Research Synthesizer Agent (retry)",
                ResearchSynthesizerAgent,
                llm_client,
                {
                    "papers": normalized_papers,
                    "target_domain": product_goal,
                    "user_goal": user_idea,
                    "user_correction": correction,
                },
                fallback=lambda: ResearchSynthesizerAgent(llm_client).build_mock(
                    {"papers": normalized_papers}
                ),
            )
            synthesis_dict = synthesis.model_dump(mode="json")
        elif hitl_result == "reject":
            _record_error(dummy_result, "HITL: Research Synthesis", "Rejected by user")
            synthesis_dict = {"capability_cards": [], "capability_map": {}, "composition_plan": {}, "summary": ""}

    progress("Product Planner Agent building PRD and MVP")
    product_plan = _run_structured_stage(
        dummy_result,
        "Product Planner Agent",
        ProductPlannerAgent,
        llm_client,
        {
            "research_synthesis": synthesis_dict,
            "target_user": target_user,
            "product_goal": product_goal,
            "user_idea": user_idea,
        },
        fallback=lambda: ProductPlannerAgent(llm_client).build_mock(
            {
                "research_synthesis": synthesis_dict,
                "target_user": target_user,
                "product_goal": product_goal,
            }
        ),
    )

    # Generate one proposal per opportunity, or at least one
    proposals: list[ProductProposal] = []
    if product_plan.opportunities:
        for opp in product_plan.opportunities:
            # Create a per-opportunity PRD with the opportunity's name
            per_opp_prd = PRD(
                product_name=opp.idea_name,
                problem_statement=product_plan.prd.problem_statement,
                target_users=product_plan.prd.target_users,
                goals=product_plan.prd.goals,
                non_goals=product_plan.prd.non_goals,
                core_features=product_plan.prd.core_features,
                user_flow=product_plan.prd.user_flow,
                success_metrics=product_plan.prd.success_metrics,
                risks=product_plan.prd.risks,
                limitations=product_plan.prd.limitations,
            )
            proposals.append(ProductProposal(
                product_name=opp.idea_name,
                target_user=opp.target_user,
                product_goal=product_goal,
                jtbd=product_plan.jtbd,
                opportunities=[opp],
                value_proposition=product_plan.value_proposition,
                prd=per_opp_prd,
                mvp_scope=product_plan.mvp_scope,
                risks=product_plan.risks,
            ))
    else:
        proposals.append(_product_plan_to_proposal(product_plan, target_user, product_goal))

    return proposals


def execute_proposal(
    proposal: ProductProposal,
    papers: list[dict[str, Any]],
    research_synthesis: dict[str, Any],
    preferred_type: str = "auto",
    repo_path: str = "",
    output_dir: str | Path = "generated_product",
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
    hitl: PipelineHITL | None = None,
) -> ProductResult:
    """Execute the full product generation for a selected proposal.

    Runs: template selection -> PrototypeBuilder -> scaffold -> inspection -> evaluation.
    Output is written to ``output_dir`` which defaults to
    ``generated_product/<sanitised_product_name>/``.
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
    normalized_papers = _normalize_papers(papers, "", "", "", repo_path)
    result["papers"] = normalized_papers
    effective_repo_path = repo_path or next(
        (
            str(paper.get("repo_path") or "")
            for paper in normalized_papers
            if paper.get("repo_path")
        ),
        "",
    )

    # Resolve output directory
    if output_dir == "generated_product" or str(output_dir) == "generated_product":
        safe_name = _sanitise_dirname(proposal.product_name)
        output_dir = f"generated_product/{safe_name}" if safe_name else "generated_product"
    output_path = Path(output_dir)

    def progress(stage: str) -> None:
        if progress_callback:
            progress_callback(stage)

    progress("Product Planner Agent building PRD and MVP")
    # Build a ProductPlan-like dict for downstream
    product_plan_dict = {
        "jtbd": proposal.jtbd,
        "value_proposition": proposal.value_proposition.model_dump(mode="json") if proposal.value_proposition else {},
        "opportunities": [o.model_dump(mode="json") for o in proposal.opportunities],
        "selected_product": proposal.product_name,
        "selection_reason": f"Selected by user from {len(proposal.opportunities)} opportunity/opportunities.",
        "prd": proposal.prd.model_dump(mode="json"),
        "mvp_scope": proposal.mvp_scope.model_dump(mode="json"),
        "risks": proposal.risks,
        "limitations": [],
    }
    result["product_plan"] = product_plan_dict
    result["prd"] = product_plan_dict["prd"]
    result["mvp_scope"] = product_plan_dict["mvp_scope"]
    result["opportunities"] = render_opportunities(
        ProductOpportunityList(opportunities=proposal.opportunities)
    )
    result["product_spec"] = _proposal_to_markdown(proposal)

    progress("Selecting product template")
    try:
        result["template_type"] = select_product_template(
            " ".join(str(item.get("paper_info", "")) for item in normalized_papers),
            " ".join(str(item.get("method_info", "")) for item in normalized_papers),
            " ".join(str(item.get("repo_info", "")) for item in normalized_papers),
            result["product_spec"],
            preferred_type,
        )
    except Exception as exc:
        _record_error(result, "Product Template Selection", exc)
        result["template_type"] = "file"

    progress("Prototype Builder Agent planning interface and adapter")
    # Wrap product_plan_dict into a ProductPlan for the agent
    pp = ProductPlan(**product_plan_dict)
    prototype_plan = _run_structured_stage(
        result,
        "Prototype Builder Agent",
        PrototypeBuilderAgent,
        client,
        {
            "product_plan": product_plan_dict,
            "template_type": result["template_type"],
        },
        fallback=lambda: PrototypeBuilderAgent(client).build_mock(
            {
                "product_plan": product_plan_dict,
                "template_type": result["template_type"],
            }
        ),
    )
    result["prototype_plan"] = prototype_plan.model_dump(mode="json")
    result["adapter_plan"] = _prototype_plan_to_markdown(prototype_plan)
    result["frontend_plan"] = result["adapter_plan"]

    # HITL: confirm prototype plan before generating scaffold
    if hitl:
        plan_text = result["adapter_plan"]
        hitl_result = hitl.request_confirmation("prototype", "Prototype Plan", plan_text)
        if hitl_result == "retry":
            correction = hitl.get_correction("prototype")
            progress("Prototype Builder Agent retrying with feedback")
            prototype_plan = _run_structured_stage(
                result,
                "Prototype Builder Agent (retry)",
                PrototypeBuilderAgent,
                client,
                {
                    "product_plan": product_plan_dict,
                    "template_type": result["template_type"],
                    "user_correction": correction,
                },
                fallback=lambda: PrototypeBuilderAgent(client).build_mock(
                    {
                        "product_plan": product_plan_dict,
                        "template_type": result["template_type"],
                    }
                ),
            )
            result["prototype_plan"] = prototype_plan.model_dump(mode="json")
            result["adapter_plan"] = _prototype_plan_to_markdown(prototype_plan)
            result["frontend_plan"] = result["adapter_plan"]
        elif hitl_result == "reject":
            _record_error(result, "HITL: Prototype Builder", "Rejected by user")
            result["errors"].append("Prototype generation skipped — user rejected the prototype plan.")
            return result

    progress("Generating product scaffold")
    try:
        result["scaffold_result"] = scaffold_product(
            template_type=result["template_type"],
            product_spec=result["product_spec"],
            adapter_plan=result["adapter_plan"],
            frontend_plan=result["frontend_plan"],
            repo_path=effective_repo_path,
            output_dir=output_path,
        )
    except Exception as exc:
        _record_error(result, "Product Scaffold", exc)
        result["scaffold_result"] = {
            "output_dir": str(output_path),
            "files": [],
            "backup_dir": "",
            "success": False,
            "message": str(exc),
        }

    progress("Inspecting generated product")
    try:
        result["inspection"] = inspect_generated_product(output_path)
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
            "research_synthesis": research_synthesis,
            "product_plan": product_plan_dict,
            "prototype_plan": result["prototype_plan"],
            "inspection": result["inspection"],
        },
        fallback=lambda: ProductEvaluatorAgent(client).build_mock(
            {
                "research_synthesis": research_synthesis,
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
    """Backward-compatible wrapper: generate proposals, execute the first one.

    Existing single-paper callers remain valid. Multi-paper callers may pass
    ``papers`` with paper, method, and optional repository context per item.
    """
    client = llm_client or LLMClient()
    normalized_papers = _normalize_papers(
        papers,
        paper_info,
        method_info,
        repo_info,
        repo_path,
    )

    proposals = generate_proposals(
        papers=normalized_papers,
        target_user=target_user,
        product_goal=product_goal,
        llm_client=client,
        user_idea=user_idea,
        progress_callback=progress_callback,
    )

    if not proposals:
        return {
            "papers": normalized_papers,
            "errors": ["No proposals were generated."],
        }

    # Build research_synthesis dict from the first proposal's context
    research_synthesis = {
        "capability_cards": [],
        "capability_map": {},
        "composition_plan": {},
        "summary": "",
    }

    return execute_proposal(
        proposal=proposals[0],
        papers=normalized_papers,
        research_synthesis=research_synthesis,
        preferred_type=preferred_type,
        repo_path=repo_path,
        output_dir=output_dir,
        llm_client=client,
        progress_callback=progress_callback,
    )
