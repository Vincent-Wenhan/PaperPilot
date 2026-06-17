from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from zipfile import ZipFile
from io import BytesIO

import app
from tools.llm_client import LLMClient
from ui import shared
from ui import productize_helpers


class ProductizeUiTests(unittest.TestCase):
    def test_build_generated_code_zip_uses_manifest_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            data = app._build_generated_code_zip(str(root), ["main.py"])
        with ZipFile(BytesIO(data)) as archive:
            self.assertEqual(archive.namelist(), ["main.py"])

    def test_show_downloads_resolves_default_output_dir(self) -> None:
        columns = [MagicMock(), MagicMock(), MagicMock()]
        with (
            patch.object(shared.st, "subheader"),
            patch.object(shared.st, "columns", return_value=columns) as st_columns,
            patch.object(shared.st, "info"),
            patch.object(shared.st, "download_button"),
        ):
            shared.show_downloads(None)

        st_columns.assert_called_once_with(3)

    def test_blank_sidebar_values_fall_back_to_environment(self) -> None:
        state = {
            "llm_api_key": "",
            "llm_base_url": "",
            "llm_model": "",
            "llm_mock_mode": False,
        }
        with (
            patch.object(app.st, "session_state", state),
            patch.dict(
                "os.environ",
                {
                    "LLM_API_KEY": "env-key",
                    "LLM_BASE_URL": "https://example.test/v1",
                    "LLM_MODEL": "test-model",
                },
            ),
        ):
            client = app.get_llm_client()

        self.assertEqual(client.api_key, "env-key")
        self.assertEqual(client.base_url, "https://example.test/v1")
        self.assertEqual(client.model, "test-model")
        self.assertFalse(client.mock_mode)

    def test_implementation_client_uses_optional_model(self) -> None:
        state = {
            "llm_api_key": "key",
            "llm_base_url": "https://example.test/v1",
            "llm_model": "main-model",
            "llm_implementation_model": "code-model",
            "llm_mock_mode": False,
        }
        with patch.object(app.st, "session_state", state):
            client = app.get_implementation_llm_client()

        self.assertEqual(client.model, "code-model")
        self.assertEqual(client.base_url, "https://example.test/v1")
        self.assertEqual(client.api_key, "key")

    def test_has_productize_context_allows_paper_only_analysis(self) -> None:
        complete = {
            "paper_info": "paper",
            "method_info": "method",
        }
        self.assertTrue(app._has_productize_context(complete))
        for key in complete:
            with self.subTest(key=key):
                incomplete = complete.copy()
                incomplete[key] = ""
                self.assertFalse(app._has_productize_context(incomplete))
        self.assertFalse(app._has_productize_context(None))

    def test_assign_repo_urls_supports_shared_or_per_paper(self) -> None:
        self.assertEqual(app._assign_repo_urls("", 2), ["", ""])
        self.assertEqual(
            app._assign_repo_urls("https://github.com/owner/shared", 2),
            [
                "https://github.com/owner/shared",
                "https://github.com/owner/shared",
            ],
        )
        self.assertEqual(
            app._assign_repo_urls(
                "https://github.com/owner/one\nhttps://github.com/owner/two",
                2,
            ),
            [
                "https://github.com/owner/one",
                "https://github.com/owner/two",
            ],
        )
        with self.assertRaises(ValueError):
            app._assign_repo_urls("one\ntwo\nthree", 2)

    def test_analysis_is_normalized_for_multi_paper_pipeline(self) -> None:
        paper = app._analysis_to_productize_paper(
            {
                "paper_info": "paper",
                "method_info": "method",
                "repo_info": "",
                "repo_path": "",
            },
            index=2,
            title="Example Paper",
        )
        self.assertEqual(paper["paper_id"], "paper-2")
        self.assertEqual(paper["title"], "Example Paper")
        self.assertEqual(paper["method_info"], "method")

    def test_generated_product_run_command_uses_actual_output_dir(self) -> None:
        command = productize_helpers.generated_product_run_command(
            {"output_dir": "/tmp/PaperPilot/generated_product/Evidence Explorer"}
        )

        self.assertEqual(
            command,
            "cd '/tmp/PaperPilot/generated_product/Evidence Explorer'\nstreamlit run app.py",
        )

    def test_generated_product_summary_prefers_inspection_status(self) -> None:
        summary = productize_helpers.summarize_generated_product(
            {
                "scaffold_result": {
                    "success": True,
                    "output_dir": "/tmp/generated",
                    "files": ["app.py", "adapter.py"],
                },
                "inspection": {
                    "syntax_ok": True,
                    "can_run_mock": True,
                    "has_rich_layout": True,
                },
            }
        )

        self.assertEqual(summary["status"], "ready")
        self.assertEqual(summary["file_count"], 2)
        self.assertEqual(summary["output_dir"], "/tmp/generated")

    def test_run_analysis_for_productize_uses_existing_pipeline(self) -> None:
        client = LLMClient(mock_mode=True)
        expected = {
            "paper_info": "paper",
            "method_info": "method",
            "repo_info": "repo",
            "repo_path": "/tmp/repo",
        }
        with patch.object(
            productize_helpers,
            "load_cached_analysis",
            return_value=None,
        ), patch.object(
            productize_helpers,
            "run_paperpilot",
            return_value=expected,
        ) as run, patch.object(productize_helpers, "save_cached_analysis"):
            result = app._run_analysis_for_productize(
                pdf_path="/tmp/paper.pdf",
                github_url="https://github.com/owner/repo",
                hardware="CPU only",
                gpu_info="",
                llm_client=client,
            )

        self.assertEqual(result, expected)
        run.assert_called_once_with(
            pdf_path="/tmp/paper.pdf",
            github_url="https://github.com/owner/repo",
            hardware="CPU only",
            gpu_info="",
            goal="run official demo",
            llm_client=client,
            progress_callback=None,
            generate_code=False,
            paper_name="paper",
        )


if __name__ == "__main__":
    unittest.main()
