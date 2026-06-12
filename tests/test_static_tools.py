from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.code_analysis_tools import (
    extract_cli_args,
    parse_dependency_file,
    python_ast_summary,
)
from tools.code_search_tools import code_search, find_entrypoints
from tools.env_tools import (
    detect_cuda_requirement,
    parse_environment_yml,
    parse_pyproject,
    parse_requirements,
)
from tools.file_tools import read_file, tree_view
from tools.test_tools import compileall_check, pytest_collect, python_syntax_check


class StaticToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "main.py").write_text(
            "import argparse\n"
            "import torch\n"
            "class Demo: pass\n"
            "def run(value): return value\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--epochs', type=int)\n",
            encoding="utf-8",
        )
        (self.root / "train.py").write_text("print('train')\n", encoding="utf-8")
        (self.root / "requirements.txt").write_text(
            "torch>=2\nnumpy==1.26\n",
            encoding="utf-8",
        )
        (self.root / "environment.yml").write_text(
            "name: demo\ndependencies:\n  - python=3.12\n  - pip\n",
            encoding="utf-8",
        )
        (self.root / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.11"\ndependencies = ["pydantic>=2"]\n',
            encoding="utf-8",
        )
        (self.root / ".env").write_text("SECRET=value\n", encoding="utf-8")
        (self.root / "__pycache__").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_file_tools_enforce_roots_and_secret_rules(self) -> None:
        result = read_file(self.root / "train.py", allowed_roots=[self.root])
        self.assertIn("train", result["content"])
        with self.assertRaises(PermissionError):
            read_file(self.root / ".env", allowed_roots=[self.root])
        with self.assertRaises(PermissionError):
            read_file(
                self.root.parent / "outside.txt",
                allowed_roots=[self.root],
            )
        with self.assertRaisesRegex(ValueError, "character limit"):
            read_file(
                self.root / "train.py",
                allowed_roots=[self.root],
                max_chars=3,
            )
        tree = tree_view(self.root, allowed_roots=[self.root])
        self.assertNotIn("__pycache__", tree["entries"])
        self.assertNotIn(".env", tree["entries"])

    def test_search_and_ast_tools_return_structured_evidence(self) -> None:
        matches = code_search(
            self.root,
            "argparse",
            allowed_roots=[self.root],
        )
        self.assertEqual(matches[0]["path"], "pkg/main.py")
        self.assertGreater(matches[0]["line"], 0)
        entrypoints = find_entrypoints(self.root, allowed_roots=[self.root])
        self.assertIn("train.py", entrypoints)

        summary = python_ast_summary(
            self.root / "pkg" / "main.py",
            allowed_roots=[self.root],
        )
        self.assertIn("Demo", summary["classes"])
        self.assertIn("run", summary["functions"])
        self.assertIn("torch", summary["imports"])
        self.assertIn("--epochs", extract_cli_args(
            self.root / "pkg" / "main.py",
            allowed_roots=[self.root],
        ))

    def test_environment_parsers(self) -> None:
        requirements = parse_requirements(
            self.root / "requirements.txt",
            allowed_roots=[self.root],
        )
        self.assertEqual(requirements["packages"][0]["name"], "torch")
        self.assertTrue(detect_cuda_requirement(requirements))
        pyproject = parse_pyproject(
            self.root / "pyproject.toml",
            allowed_roots=[self.root],
        )
        self.assertEqual(pyproject["requires_python"], ">=3.11")
        environment = parse_environment_yml(
            self.root / "environment.yml",
            allowed_roots=[self.root],
        )
        self.assertEqual(environment["name"], "demo")
        dependency = parse_dependency_file(
            self.root / "requirements.txt",
            allowed_roots=[self.root],
        )
        self.assertEqual(dependency["format"], "requirements")

    def test_validation_tools_do_not_run_test_bodies(self) -> None:
        valid = python_syntax_check(
            self.root / "train.py",
            allowed_roots=[self.root],
        )
        self.assertTrue(valid["success"])
        (self.root / "bad.py").write_text("invalid (", encoding="utf-8")
        invalid = python_syntax_check(
            self.root / "bad.py",
            allowed_roots=[self.root],
        )
        self.assertFalse(invalid["success"])
        compiled = compileall_check(self.root, allowed_roots=[self.root])
        self.assertFalse(compiled["success"])
        self.assertFalse((self.root / "pkg" / "__pycache__").exists())

        (self.root / "test_never_run.py").write_text(
            "def test_never_run():\n"
            "    raise RuntimeError('test body executed')\n",
            encoding="utf-8",
        )
        collected = pytest_collect(self.root, allowed_roots=[self.root])
        self.assertTrue(collected["success"])
        self.assertIn("test_never_run", collected["stdout"])
        self.assertFalse((self.root / ".pytest_cache").exists())


if __name__ == "__main__":
    unittest.main()
