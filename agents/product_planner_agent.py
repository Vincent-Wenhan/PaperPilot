"""High-level theory-guided product planning agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.composition_schema import ResearchSynthesis
from schemas.product_schema import (
    MVPScope,
    PRD,
    ProductOpportunity,
    ProductPlan,
    ValueProposition,
)
from tools.llm_client import LLMClient


class ProductPlannerAgent(StructuredAgent[ProductPlan]):
    """Turn research synthesis into JTBD, PRD, and bounded MVP scope."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Planner Agent",
            prompt_path="product_planner_prompt.txt",
            schema_type=ProductPlan,
            guideline_names=(
                "product_design_principles.md",
                "prd_template.md",
                "jtbd_template.md",
                "value_proposition_canvas.md",
                "mvp_scope_rules.md",
                "safety_rules.md",
            ),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> ProductPlan:
        synthesis = ResearchSynthesis.model_validate(
            input_data.get("research_synthesis") or {}
        )
        target_user = str(input_data.get("target_user") or "Research learners")
        product_goal = str(
            input_data.get("product_goal")
            or "Understand and demonstrate research capabilities"
        )
        feature = (
            "Multi-paper capability cards and composition plan"
            if len(synthesis.capability_cards) > 1
            else "Paper capability card and product plan"
        )
        opportunity = ProductOpportunity(
            idea_name="Research Composition Workbench",
            target_user=target_user,
            core_value=product_goal,
            technical_feasibility=5,
            demo_feasibility=5,
            model_availability=3,
            data_requirement=5,
            integration_risk=2,
            user_value=4,
            course_presentation_value=5,
            paper_faithfulness=4,
            multi_paper_coherence=4,
            mock_first_suitability=5,
            overall_score=4.4,
            reason="The workflow exposes evidence, scope, and integration limits.",
        )
        return ProductPlan(
            jtbd=(
                f"When reviewing research, {target_user} want to understand and "
                "compose paper capabilities, so they can choose a feasible demo."
            ),
            value_proposition=ValueProposition(
                customer_jobs=["Understand paper capabilities", "Choose an MVP"],
                pains=["Capabilities and integration risks are unclear"],
                gains=["A traceable, bounded product plan"],
                pain_relievers=["Capability cards", "Explicit composition risks"],
                gain_creators=["PRD-driven prototype plan"],
                product_features=[feature, "Rubric-based evaluation"],
            ),
            opportunities=[opportunity],
            selected_product=opportunity.idea_name,
            selection_reason=opportunity.reason,
            prd=PRD(
                product_name=opportunity.idea_name,
                problem_statement=(
                    "Research capabilities are difficult to translate into a "
                    "clear and feasible product demonstration."
                ),
                target_users=[target_user],
                goals=[product_goal, "Keep paper evidence and limitations visible"],
                non_goals=[
                    "Automatically execute analyzed repositories",
                    "Claim production-ready real model integration",
                ],
                core_features=[
                    feature,
                    "PRD and MoSCoW scope",
                    "Mock-first result workflow",
                    "Product evaluation rubric",
                ],
                user_flow=[
                    "Upload or reuse paper analysis",
                    "Review capability cards and composition",
                    "Review PRD and MVP scope",
                    "Generate and inspect mock-first prototype",
                ],
                success_metrics=[
                    "User can explain selected capabilities and exclusions",
                    "Generated prototype passes deterministic inspection",
                ],
                risks=synthesis.composition_plan.risks,
                limitations=[
                    "Real adapters, checkpoints, and datasets require manual review."
                ],
            ),
            mvp_scope=MVPScope(
                must_have=[
                    "Capability cards",
                    "Composition plan",
                    "PRD and MVP scope",
                    "Mock-first prototype",
                    "Rubric evaluation",
                ],
                should_have=["Downloadable structured results"],
                could_have=["Side-by-side method comparison"],
                wont_have=[
                    "Automatic training",
                    "Arbitrary command execution",
                    "Unreviewed real-model integration",
                ],
            ),
            risks=synthesis.composition_plan.risks,
            limitations=["Mock results do not prove paper metric reproduction."],
        )
