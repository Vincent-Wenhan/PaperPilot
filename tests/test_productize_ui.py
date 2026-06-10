from __future__ import annotations

import unittest
from unittest.mock import patch

import app
from tools.llm_client import LLMClient


class ProductizeUiTests(unittest.TestCase):
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
