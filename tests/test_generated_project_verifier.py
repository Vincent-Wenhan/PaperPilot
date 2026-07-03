from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tools.generated_project_verifier import GeneratedProjectVerifier


class GeneratedProjectVerifierTests(unittest.TestCase):
    def test_verifier_accepts_contract_backed_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "tests").mkdir()
            (root / "outputs").mkdir()
            (root / "main.py").write_text(
                "from pathlib import Path\n"
                "import json\n"
                "Path('outputs').mkdir(exist_ok=True)\n"
                "Path('outputs/result.json').write_text("
                "json.dumps({'score': 0.91, 'labels': ['ok']}), encoding='utf-8')\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_cli.py").write_text(
                "def test_contract_smoke():\n    assert True\n",
                encoding="utf-8",
            )
            contract = {
                "required_files": ["main.py", "tests/test_cli.py"],
                "required_tests": ["tests/test_cli.py"],
                "output_schema": {"score": "number", "labels": "array"},
                "smoke_test_command": [sys.executable, "main.py"],
            }

            report = GeneratedProjectVerifier(root, contract).verify()

            self.assertTrue(report.ok, report.issues)
            self.assertTrue(report.syntax_ok)
            self.assertTrue(report.tests_collect_ok)
            self.assertTrue(report.smoke_ok)
            self.assertTrue(report.schema_ok)

    def test_verifier_reports_missing_schema_and_placeholder_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "tests").mkdir()
            (root / "outputs").mkdir()
            (root / "main.py").write_text(
                "from pathlib import Path\n"
                "Path('outputs/result.json').write_text('{}', encoding='utf-8')\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_cli.py").write_text(
                "def test_contract_smoke():\n    assert True\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "TODO: this fully reproduces the paper SOTA results.\n",
                encoding="utf-8",
            )

            report = GeneratedProjectVerifier(
                root,
                {
                    "required_files": ["main.py", "README.md"],
                    "output_schema": {"score": "number"},
                    "smoke_test_command": [sys.executable, "main.py"],
                    "forbidden_patterns": ["fully reproduces", "SOTA"],
                },
            ).verify()

            codes = {issue.code for issue in report.issues}
            self.assertFalse(report.ok)
            self.assertIn("output_schema_mismatch", codes)
            self.assertIn("forbidden_claim", codes)
            self.assertEqual(json.loads(report.to_json())["ok"], False)


if __name__ == "__main__":
    unittest.main()
