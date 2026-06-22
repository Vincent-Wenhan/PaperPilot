"""End-to-end reproduce pipeline tests in mock mode."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from main import run_paperpilot
from tools.llm_client import LLMClient


def test_mock_reproduce_result_includes_implementation_blueprint(tmp_path):
    import fitz
    from main import run_paperpilot
    from tools.llm_client import LLMClient

    pdf = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "A paper describing an encoder and a contrastive objective.",
    )
    doc.save(pdf)
    doc.close()

    result = run_paperpilot(
        pdf_path=str(pdf),
        github_url="",
        hardware="CPU only",
        gpu_info="",
        goal="minimal training experiment",
        llm_client=LLMClient(mock_mode=True),
        generate_code=True,
        paper_name="blueprint_test",
    )

    assert result["implementation_blueprint"]["files"]
    assert "blueprint_quality" in result
    assert result["code_quality"]["metrics"]["blueprint"]["planned_files"] > 0


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
            output_dir = Path("outputs") / "sample"
            manifest_path = output_dir / "manifest.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_paths = {item["path"] for item in manifest["artifacts"]}
            self.assertIn("reproduction_plan.md", artifact_paths)
            self.assertIn("run.sh", artifact_paths)
            self.assertIn("report.md", artifact_paths)
            self.assertEqual(manifest["mode"], "reproduce")


if __name__ == "__main__":
    unittest.main()
