"""Tests for the active high-level structured agents and renderers."""

from __future__ import annotations

import json
import unittest

from agents import ResearchUnderstandingAgent, RepositoryUnderstandingAgent
from pipeline.productize_renderers import render_opportunities
from pipeline.reproduce_renderers import (
    render_method_breakdown,
    render_repository_understanding,
    render_research_summary,
)
from schemas.product_schema import ProductOpportunity, ProductOpportunityList


class MockLLMClient:
    mock_mode = False

    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(self.response)


class StructuredOutputTests(unittest.TestCase):
    def test_research_understanding_parses_real_json(self) -> None:
        agent = ResearchUnderstandingAgent(
            MockLLMClient(
                {
                    "title": "Test Paper",
                    "task": "Classification",
                    "method_summary": "A test method.",
                    "method_modules": ["encoder", "classifier"],
                }
            )
        )
        model = agent.run_structured({"paper_text": "paper"})
        self.assertEqual(model.title, "Test Paper")
        self.assertIn("encoder", render_method_breakdown(model))
        self.assertIn("Classification", render_research_summary(model))

    def test_repository_understanding_parses_real_json(self) -> None:
        agent = RepositoryUnderstandingAgent(
            MockLLMClient(
                {
                    "repo_source": "GitHub repository",
                    "repo_path": "/tmp/repo",
                    "detected_framework": "pytorch",
                    "training_entrypoints": ["train.py"],
                }
            )
        )
        model = agent.run_structured({"repo_scan": {"repo_path": "/tmp/repo"}})
        self.assertEqual(model.detected_framework, "pytorch")
        self.assertIn("GitHub repository", render_repository_understanding(model))

    def test_product_opportunity_renderer(self) -> None:
        model = ProductOpportunityList(
            opportunities=[
                ProductOpportunity(
                    idea_name="Research Workbench",
                    target_user="Students",
                    core_value="Explain methods",
                    technical_feasibility=5,
                    demo_feasibility=5,
                    model_availability=3,
                    data_requirement=5,
                    integration_risk=2,
                    user_value=4,
                    course_presentation_value=5,
                    overall_score=4.4,
                    reason="Bounded and clear.",
                )
            ]
        )
        rendered = render_opportunities(model)
        self.assertIn("Research Workbench", rendered)
        self.assertIn("4.4/5", rendered)


if __name__ == "__main__":
    unittest.main()
