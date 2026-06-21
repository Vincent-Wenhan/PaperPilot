from __future__ import annotations

import unittest

from agents import (
    ProductEvaluatorAgent,
    ProductPlannerAgent,
    PrototypeBuilderAgent,
    ResearchSynthesizerAgent,
)
from tools.llm_client import LLMClient


class ProductAgentTests(unittest.TestCase):
    def test_only_four_high_level_product_agents_run_product_reasoning(self) -> None:
        client = LLMClient(mock_mode=True)
        synthesis = ResearchSynthesizerAgent(client).run_structured(
            {"papers": [{"paper_id": "p1", "paper_info": "paper", "method_info": "method"}]}
        )
        product = ProductPlannerAgent(client).run_structured(
            {
                "research_synthesis": synthesis.model_dump(),
                "target_user": "Students",
                "product_goal": "Demo",
            }
        )
        prototype = PrototypeBuilderAgent(client).run_structured(
            {"product_plan": product.model_dump(), "template_type": "file"}
        )
        evaluation = ProductEvaluatorAgent(client).run_structured(
            {
                "research_synthesis": synthesis.model_dump(),
                "product_plan": product.model_dump(),
                "prototype_plan": prototype.model_dump(),
                "inspection": {"syntax_ok": True, "can_run_mock": True},
            }
        )
        self.assertTrue(synthesis.capability_cards)
        self.assertTrue(product.prd.core_features)
        self.assertGreaterEqual(len(product.opportunities), 2)
        self.assertLessEqual(len(product.opportunities), 3)
        self.assertTrue(prototype.mock_first)
        self.assertGreaterEqual(evaluation.overall_score, 4)


if __name__ == "__main__":
    unittest.main()
