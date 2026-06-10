from __future__ import annotations

import unittest

from pydantic import ValidationError


class GuidelineLoaderTests(unittest.TestCase):
    def test_loads_named_guideline_and_rejects_path_traversal(self) -> None:
        from tools.guideline_loader import load_guideline

        content = load_guideline("multi_paper_composition_rules.md")
        self.assertIn("complementary", content.lower())
        with self.assertRaises(ValueError):
            load_guideline("../README.md")


class FunctionalUpgradeSchemaTests(unittest.TestCase):
    def test_composition_and_evaluation_scores_are_bounded(self) -> None:
        from schemas.composition_schema import MethodCompositionPlan
        from schemas.evaluation_schema import ProductEvaluation

        plan = MethodCompositionPlan(
            strategy="pipeline",
            selected_paper_ids=["paper-1"],
            combined_capabilities=["structured analysis"],
            workflow_steps=["Analyze input"],
            rationale="One capability is sufficient for the MVP.",
        )
        self.assertEqual(plan.strategy, "pipeline")

        with self.assertRaises(ValidationError):
            ProductEvaluation(overall_score=6)

    def test_product_plan_contains_prd_and_moscow_scope(self) -> None:
        from schemas.product_schema import MVPScope, PRD, ProductPlan

        plan = ProductPlan(
            jtbd="When reviewing papers, I want a composition plan.",
            value_proposition={"customer_jobs": ["review papers"]},
            opportunities=[],
            selected_product="Research Composition Workbench",
            selection_reason="Clear mock-first workflow.",
            prd=PRD(
                product_name="Research Composition Workbench",
                problem_statement="Paper capabilities are difficult to combine.",
                target_users=["research learners"],
                goals=["make composition explicit"],
                non_goals=["run unreviewed repositories"],
                core_features=["capability cards"],
                user_flow=["upload papers", "review composition"],
                success_metrics=["users can explain the composition"],
            ),
            mvp_scope=MVPScope(
                must_have=["capability cards"],
                should_have=["download report"],
                could_have=["comparison chart"],
                wont_have=["automatic model execution"],
            ),
        )
        self.assertIn("automatic model execution", plan.mvp_scope.wont_have)


class HighLevelProductAgentTests(unittest.TestCase):
    def test_mock_agents_return_structured_outputs(self) -> None:
        from agents import (
            ProductEvaluatorAgent,
            ProductPlannerAgent,
            PrototypeBuilderAgent,
            ResearchSynthesizerAgent,
        )
        from tools.llm_client import LLMClient

        client = LLMClient(mock_mode=True)
        synthesis = ResearchSynthesizerAgent(client).run_structured(
            {
                "papers": [
                    {
                        "paper_id": "paper-1",
                        "title": "Vision Method",
                        "paper_info": "Image segmentation paper.",
                        "method_info": "Segments images.",
                    },
                    {
                        "paper_id": "paper-2",
                        "title": "Text Method",
                        "paper_info": "Text explanation paper.",
                        "method_info": "Explains results.",
                    },
                ]
            }
        )
        self.assertEqual(len(synthesis.capability_cards), 2)
        self.assertTrue(synthesis.composition_plan.relationships)

        product_plan = ProductPlannerAgent(client).run_structured(
            {
                "research_synthesis": synthesis.model_dump(),
                "target_user": "Students",
                "product_goal": "Explain combined research capabilities",
            }
        )
        self.assertTrue(product_plan.prd.product_name)
        self.assertTrue(product_plan.mvp_scope.must_have)

        prototype = PrototypeBuilderAgent(client).run_structured(
            {"product_plan": product_plan.model_dump(), "template_type": "file"}
        )
        self.assertTrue(prototype.mock_first)
        self.assertTrue(prototype.adapter_boundary)

        evaluation = ProductEvaluatorAgent(client).run_structured(
            {
                "research_synthesis": synthesis.model_dump(),
                "product_plan": product_plan.model_dump(),
                "prototype_plan": prototype.model_dump(),
                "inspection": {"syntax_ok": True, "can_run_mock": True},
            }
        )
        self.assertGreaterEqual(evaluation.overall_score, 4)


if __name__ == "__main__":
    unittest.main()
