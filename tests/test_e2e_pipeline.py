"""End-to-end reproduce pipeline tests in mock mode."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import run_paperpilot
from tools.llm_client import LLMClient


class E2EPipelineTests(unittest.TestCase):
    def test_mock_reproduce_pipeline_produces_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "sample.pdf"
            pdf.write_bytes(b"%PDF-1.4 mock paper content for testing")
            client = LLMClient(mock_mode=True)
            with patch(
                "pipeline.reproduce_pipeline.analyze_pdf_quality",
                return_value={"is_scanned": False, "warnings": []},
            ), patch(
                "pipeline.reproduce_pipeline.parse_pdf",
                return_value="[Page 1]\nSample paper about neural networks.",
            ):
                result = run_paperpilot(
                    pdf_path=str(pdf),
                    llm_client=client,
                    generate_code=False,
                    paper_name="sample",
                )
            self.assertIn(
                result.get("pipeline_status"),
                {"mock", "complete", "degraded"},
            )
            self.assertTrue(result.get("paper_info"))
            self.assertTrue(result.get("experiment_plan"))
            self.assertIn("stage_sources", result)


if __name__ == "__main__":
    unittest.main()
