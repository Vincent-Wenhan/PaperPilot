from __future__ import annotations

import unittest
from unittest.mock import patch

import app
from tools.llm_client import LLMClient


class ProductizeUiTests(unittest.TestCase):
    def test_has_productize_context_requires_analysis_and_repo_path(self) -> None:
        complete = {
            "paper_info": "paper",
            "method_info": "method",
            "repo_info": "repo",
            "repo_path": "/tmp/repo",
        }
        self.assertTrue(app._has_productize_context(complete))
        for key in complete:
            with self.subTest(key=key):
                incomplete = complete.copy()
                incomplete[key] = ""
                self.assertFalse(app._has_productize_context(incomplete))
        self.assertFalse(app._has_productize_context(None))

    def test_run_analysis_for_productize_uses_existing_pipeline(self) -> None:
        client = LLMClient(mock_mode=True)
        expected = {
            "paper_info": "paper",
            "method_info": "method",
            "repo_info": "repo",
            "repo_path": "/tmp/repo",
        }
        with patch.object(app, "run_paperpilot", return_value=expected) as run:
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
        )


if __name__ == "__main__":
    unittest.main()
