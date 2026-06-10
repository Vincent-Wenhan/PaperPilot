"""Tests for structured agent output with schema parsing."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from agents.paper_reader_agent import PaperReaderAgent
from agents.repo_analyzer_agent import RepoAnalyzerAgent
from agents.product_opportunity_agent import ProductOpportunityAgent
from agents.schema_display import (
    opportunities_to_markdown,
    paper_summary_to_markdown,
    repo_analysis_to_markdown,
)
from schemas.paper_schema import PaperSummary
from schemas.product_schema import ProductOpportunityList
from schemas.repo_schema import RepoAnalysis
from tools.llm_client import LLMClient


class MockLLMClient:
    """A deterministic LLM stub that returns pre-configured responses."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.call_count = 0
        self.mock_mode = False

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        idx = self.call_count
        self.call_count += 1
        if idx < len(self.responses):
            return self.responses[idx]
        return ""


class TestStructuredOutput(unittest.TestCase):
    """Verify schema parsing, retry, and fallback in agents."""

    # ------------------------------------------------------------------
    # PaperReaderAgent
    # ------------------------------------------------------------------
    def test_paper_reader_parses_valid_json(self) -> None:
        valid_json = json.dumps({
            "title": "Test Paper",
            "task": "Image classification",
            "problem": "Low accuracy",
            "contributions": ["New method"],
            "method_summary": "A novel approach.",
            "datasets": ["CIFAR-10"],
            "metrics": ["Accuracy"],
            "training_details": ["Batch size 64"],
            "limitations": ["Small dataset"],
        })
        client = MockLLMClient([valid_json])
        agent = PaperReaderAgent(client)
        result = agent.run("summarize this paper")
        self.assertIn("Test Paper", result)
        self.assertIn("Image classification", result)
        self.assertIn("New method", result)

    def test_paper_reader_retries_on_invalid_json(self) -> None:
        bad = "This is not JSON at all"
        good = json.dumps({
            "title": "Retry Paper",
            "task": "Classification",
            "problem": "",
            "contributions": [],
            "method_summary": "Retry method.",
            "datasets": [],
            "metrics": [],
            "training_details": [],
            "limitations": [],
        })
        client = MockLLMClient([bad, good])
        agent = PaperReaderAgent(client)
        result = agent.run("summarize")
        self.assertEqual(client.call_count, 2)
        self.assertIn("Retry Paper", result)

    def test_paper_reader_falls_back_to_raw_text(self) -> None:
        bad = "Totally invalid output"
        client = MockLLMClient([bad, bad])
        agent = PaperReaderAgent(client)
        result = agent.run("summarize")
        self.assertEqual(result, bad)

    # ------------------------------------------------------------------
    # RepoAnalyzerAgent
    # ------------------------------------------------------------------
    def test_repo_analyzer_parses_valid_json(self) -> None:
        valid_json = json.dumps({
            "framework": "PyTorch",
            "task_type": "classification",
            "training_entrypoints": ["train.py"],
            "inference_entrypoints": ["infer.py"],
            "config_files": ["config.yaml"],
            "dependency_files": ["requirements.txt"],
            "dataset_requirements": ["ImageNet"],
            "checkpoint_requirements": [],
            "risk_level": "low",
            "notes": ["Well documented"],
        })
        client = MockLLMClient([valid_json])
        agent = RepoAnalyzerAgent(client)
        result = agent.run("analyze this repo")
        self.assertIn("PyTorch", result)
        self.assertIn("train.py", result)
        self.assertIn("low", result.lower())

    def test_repo_analyzer_falls_back_on_invalid_json(self) -> None:
        bad = "Some Markdown text that is not valid JSON"
        client = MockLLMClient([bad, bad])
        agent = RepoAnalyzerAgent(client)
        result = agent.run("analyze")
        self.assertEqual(result, bad)

    # ------------------------------------------------------------------
    # ProductOpportunityAgent
    # ------------------------------------------------------------------
    def test_product_opportunity_mock_mode_unchanged(self) -> None:
        agent = ProductOpportunityAgent(LLMClient(mock_mode=True))
        result = agent.run({"paper_info": "test"})
        from agents.product_mock_outputs import PRODUCT_OPPORTUNITY_MOCK
        self.assertEqual(result, PRODUCT_OPPORTUNITY_MOCK)

    def test_product_opportunity_parses_valid_json(self) -> None:
        valid_json = json.dumps({
            "opportunities": [
                {
                    "idea_name": "QA Bot",
                    "target_user": "Students",
                    "core_value": "Quick answers",
                    "technical_feasibility": 4,
                    "demo_feasibility": 5,
                    "model_availability": 3,
                    "data_requirement": 2,
                    "integration_risk": 2,
                    "user_value": 5,
                    "course_presentation_value": 4,
                    "overall_score": 3.8,
                    "reason": "Easy to demo",
                }
            ]
        })
        client = MockLLMClient([valid_json])
        agent = ProductOpportunityAgent(client)
        result = agent.run({"paper_info": "test"})
        self.assertIn("QA Bot", result)
        self.assertIn("Easy to demo", result)


class TestSchemaDisplay(unittest.TestCase):
    """Verify schema-to-markdown conversion functions."""

    def test_paper_summary_to_markdown(self) -> None:
        m = PaperSummary(
            title="Test",
            task="Classification",
            contributions=["C1"],
            method_summary="Method",
        )
        md = paper_summary_to_markdown(m)
        self.assertIn("Test", md)
        self.assertIn("Classification", md)
        self.assertIn("C1", md)
        self.assertIn("Method", md)

    def test_repo_analysis_to_markdown(self) -> None:
        m = RepoAnalysis(
            framework="TensorFlow",
            training_entrypoints=["run.py"],
            notes=["Test note"],
        )
        md = repo_analysis_to_markdown(m)
        self.assertIn("TensorFlow", md)
        self.assertIn("run.py", md)
        self.assertIn("Test note", md)

    def test_opportunities_to_markdown(self) -> None:
        data = {
            "opportunities": [
                {
                    "idea_name": "Idea1",
                    "target_user": "Users",
                    "core_value": "Value",
                    "technical_feasibility": 3,
                    "demo_feasibility": 4,
                    "model_availability": 3,
                    "data_requirement": 2,
                    "integration_risk": 2,
                    "user_value": 4,
                    "course_presentation_value": 3,
                    "overall_score": 3.2,
                    "reason": "Good idea",
                }
            ]
        }
        m = ProductOpportunityList.model_validate(data)
        md = opportunities_to_markdown(m)
        self.assertIn("Idea1", md)
        self.assertIn("Good idea", md)

    def test_opportunities_empty(self) -> None:
        m = ProductOpportunityList(opportunities=[])
        md = opportunities_to_markdown(m)
        self.assertIn("No opportunities", md)


if __name__ == "__main__":
    unittest.main()
