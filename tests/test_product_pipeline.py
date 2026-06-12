from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.research_synthesizer_agent import ResearchSynthesizerAgent
from pipeline.productize_pipeline import run_productize_pipeline
from tools.llm_client import LLMClient, LLMConnectionError


class FailingLLMClient:
    mock_mode = False

    def __init__(self) -> None:
        self.generate_calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        self.generate_calls += 1
        raise LLMConnectionError("Could not connect to product endpoint.")


class ProductPipelineTests(unittest.TestCase):
    def test_complete_mock_pipeline_generates_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            result = run_productize_pipeline(
                paper_info="A paper about question answering.",
                method_info="Text question answering transformer.",
                repo_info="Repository has inference.py.",
                repo_path="/tmp/source-repository",
                target_user="Students",
                product_goal="Interactive course demo",
                llm_client=LLMClient(mock_mode=True),
                preferred_type="text",
                output_dir=output_dir,
            )

            expected_keys = {
                "opportunities",
                "product_spec",
                "research_synthesis",
                "capability_cards",
                "composition_plan",
                "product_plan",
                "prd",
                "mvp_scope",
                "prototype_plan",
                "evaluation",
                "template_type",
                "adapter_plan",
                "frontend_plan",
                "scaffold_result",
                "inspection",
                "test_report",
                "errors",
            }
            self.assertTrue(expected_keys.issubset(result))
            self.assertEqual(result["template_type"], "text")
            self.assertTrue(result["scaffold_result"]["success"])
            self.assertTrue(result["inspection"]["syntax_ok"])
            self.assertEqual(result["inspection"]["missing_files"], [])
            self.assertTrue((output_dir / "app.py").is_file())
            self.assertEqual(len(result["capability_cards"]), 1)
            self.assertEqual(result["evaluation"]["demo_readiness"], "ready_with_mock")

    def test_agent_failure_records_error_and_keeps_mock_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            with patch.object(
                ResearchSynthesizerAgent,
                "run_structured",
                side_effect=RuntimeError("synthesis unavailable"),
            ):
                result = run_productize_pipeline(
                    paper_info="paper",
                    method_info="method",
                    repo_info="repo",
                    repo_path="/tmp/source-repository",
                    target_user="Students",
                    product_goal="Demo",
                    llm_client=LLMClient(mock_mode=True),
                    output_dir=output_dir,
                )

            self.assertTrue(
                any("Research Synthesizer Agent" in error for error in result["errors"])
            )
            self.assertIn("# Product Plan", result["product_spec"])
            self.assertTrue(result["scaffold_result"]["success"])
            self.assertTrue(result["inspection"]["can_run_mock"])

    def test_connection_failure_stops_repeated_product_llm_requests(self) -> None:
        client = FailingLLMClient()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_productize_pipeline(
                paper_info="paper",
                method_info="method",
                repo_info="",
                repo_path="",
                target_user="Students",
                product_goal="Demo",
                llm_client=client,
                output_dir=Path(temp_dir) / "generated_product",
            )

        self.assertEqual(client.generate_calls, 1)
        self.assertEqual(result["pipeline_status"], "failed")
        self.assertEqual(len(result["errors"]), 1)
        self.assertNotIn("invalid structured output", result["errors"][0])

    def test_multi_paper_pipeline_builds_composition_and_prd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            papers = [
                {
                    "paper_id": "vision",
                    "title": "Vision Paper",
                    "paper_info": "Image segmentation research.",
                    "method_info": "Segments objects in images.",
                    "repo_info": "Has inference.py.",
                    "repo_path": "/tmp/vision",
                },
                {
                    "paper_id": "explain",
                    "title": "Explanation Paper",
                    "paper_info": "Result explanation research.",
                    "method_info": "Explains model outputs.",
                    "repo_info": "No repository.",
                    "repo_path": "",
                },
            ]
            result = run_productize_pipeline(
                paper_info=papers[0]["paper_info"],
                method_info=papers[0]["method_info"],
                repo_info=papers[0]["repo_info"],
                repo_path="",
                target_user="Students",
                product_goal="Explain image analysis",
                llm_client=LLMClient(mock_mode=True),
                output_dir=output_dir,
                papers=papers,
            )

            self.assertEqual(len(result["capability_cards"]), 2)
            self.assertEqual(
                result["composition_plan"]["relationships"][0]["relationship_type"],
                "complementary",
            )
            self.assertTrue(result["prd"]["core_features"])
            self.assertIn("Mock-first prototype", result["mvp_scope"]["must_have"])
            self.assertGreaterEqual(result["evaluation"]["overall_score"], 4)
            self.assertIn(
                "/tmp/vision",
                (output_dir / "adapter.py").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
