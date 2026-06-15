"""High-level rubric-based product evaluation agent."""

from __future__ import annotations

from statistics import mean
from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.composition_schema import ResearchSynthesis
from schemas.evaluation_schema import ProductEvaluation
from tools.llm_client import LLMClient


class ProductEvaluatorAgent(StructuredAgent[ProductEvaluation]):
    """Evaluate paper faithfulness, MVP quality, mock behavior, and safety."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Evaluator Agent",
            prompt_path="product_evaluator_prompt.txt",
            schema_type=ProductEvaluation,
            guideline_names=(
                "product_evaluation_rubric.md",
                "product_design_principles.md",
                "evidence_traceability_rules.md",
                "confidence_and_limitations_rules.md",
                "adapter_integration_rules.md",
                "revision_response_rules.md",
                "safety_rules.md",
            ),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> ProductEvaluation:
        synthesis = ResearchSynthesis.model_validate(
            input_data.get("research_synthesis") or {}
        )
        inspection = input_data.get("inspection") or {}
        syntax_ok = bool(inspection.get("syntax_ok"))
        mock_ok = bool(inspection.get("can_run_mock"))
        deterministic_score = 5.0 if syntax_ok and mock_ok else 3.0
        scores = {
            "paper_faithfulness": 4.0 if synthesis.capability_cards else 3.0,
            "multi_paper_coherence": (
                4.0 if len(synthesis.capability_cards) > 1 else 5.0
            ),
            "user_clarity": 4.0,
            "problem_solution_fit": 4.0,
            "prd_completeness": 5.0,
            "mvp_simplicity": 4.0,
            "demo_feasibility": deterministic_score,
            "mock_first_correctness": deterministic_score,
            "safety_awareness": 5.0,
            "integration_feasibility": 4.0,
        }
        overall = round(mean(scores.values()), 2)
        problems = []
        suggestions = []
        if not syntax_ok:
            problems.append("Generated Python syntax inspection failed.")
            suggestions.append("Fix generated source before demonstrating the prototype.")
        if not mock_ok:
            problems.append("Mock-first adapter markers were not verified.")
            suggestions.append("Restore mock mode as the default adapter behavior.")
        return ProductEvaluation(
            **scores,
            overall_score=overall,
            detected_problems=problems,
            revision_suggestions=suggestions,
            safety_warnings=[
                "Real model integration still requires explicit manual review."
            ],
            demo_readiness="ready_with_mock" if overall >= 4 else "revise",
        )
