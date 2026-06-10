from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.product_opportunity_agent import ProductOpportunityAgent
from productize.product_pipeline import run_productize_pipeline
from tools.llm_client import LLMClient


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

    def test_agent_failure_records_error_and_keeps_mock_product(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            with patch.object(
                ProductOpportunityAgent,
                "run",
                side_effect=RuntimeError("opportunity unavailable"),
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
                any("Product Opportunity Agent" in error for error in result["errors"])
            )
            self.assertIn("# Generated Product Specification", result["product_spec"])
            self.assertTrue(result["scaffold_result"]["success"])
            self.assertTrue(result["inspection"]["can_run_mock"])


if __name__ == "__main__":
    unittest.main()
