from __future__ import annotations

import unittest
from pathlib import Path

from pipeline.reproduce_pipeline import _merge_quality_into_review
from schemas.code_review_schema import CodeReview
from schemas.reproduction_schema import GeneratedCodeFile, ImplementationBundle
from tools.code_quality import assess_implementation_quality


class CodeQualityTests(unittest.TestCase):
    def test_workbench_runtime_panels_do_not_import_mock_types(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for relative_path in [
            "frontend/components/inspector/runner-panel.tsx",
            "frontend/components/inspector/tool-call-panel.tsx",
        ]:
            source = (root / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("@/lib/mock-data", source, relative_path)

    def test_flags_placeholder_only_bundle(self) -> None:
        bundle = ImplementationBundle(
            project_name="placeholder",
            summary="Generic scaffold",
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="placeholder entry",
                    content=(
                        '"""Placeholder."""\n\n'
                        "def main():\n"
                        "    pass\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="README.md",
                    purpose="docs",
                    content="# Mock Reproduction\n\nThis is a generic placeholder.\n",
                ),
            ],
        )

        quality = assess_implementation_quality(bundle)

        self.assertLess(quality["overall_score"], 3.0)
        self.assertIn("placeholder_body", quality["issue_codes"])
        self.assertIn("missing_tests", quality["issue_codes"])
        self.assertFalse(quality["passes_minimum_quality"])

    def test_rewards_structured_runnable_bundle(self) -> None:
        bundle = ImplementationBundle(
            project_name="structured_reproduction",
            summary="Implements a small method-specific dataflow.",
            smoke_test_command="python main.py --smoke-test",
            files=[
                GeneratedCodeFile(
                    path="README.md",
                    purpose="docs",
                    content=(
                        "# Structured Reproduction\n\n"
                        "## Implemented Scope\n"
                        "Synthetic smoke test for the encoder and scoring module.\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="config.py",
                    purpose="configuration",
                    content=(
                        "from dataclasses import dataclass\n\n"
                        "@dataclass\n"
                        "class ModelConfig:\n"
                        "    input_dim: int = 4\n"
                        "    hidden_dim: int = 3\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="model.py",
                    purpose="method modules",
                    content=(
                        '"""Method-specific model components."""\n\n'
                        "from config import ModelConfig\n\n"
                        "class TinyEncoder:\n"
                        "    def __init__(self, config: ModelConfig) -> None:\n"
                        "        self.config = config\n\n"
                        "    def encode(self, values: list[float]) -> list[float]:\n"
                        "        total = sum(values) or 1.0\n"
                        "        return [value / total for value in values[: self.config.hidden_dim]]\n\n"
                        "def score(values: list[float]) -> float:\n"
                        "    return sum(value * value for value in values)\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="main.py",
                    purpose="safe entry point",
                    content=(
                        "import argparse\n"
                        "from config import ModelConfig\n"
                        "from model import TinyEncoder, score\n\n"
                        "def main() -> None:\n"
                        "    parser = argparse.ArgumentParser()\n"
                        "    parser.add_argument('--smoke-test', action='store_true')\n"
                        "    args = parser.parse_args()\n"
                        "    if args.smoke_test:\n"
                        "        encoded = TinyEncoder(ModelConfig()).encode([1.0, 2.0, 1.0, 0.0])\n"
                        "        print(f'score={score(encoded):.3f}')\n\n"
                        "if __name__ == '__main__':\n"
                        "    main()\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="tests/test_model.py",
                    purpose="dataflow test",
                    content=(
                        "from config import ModelConfig\n"
                        "from model import TinyEncoder, score\n\n"
                        "def test_encoder_score_dataflow() -> None:\n"
                        "    encoded = TinyEncoder(ModelConfig()).encode([1.0, 2.0, 1.0, 0.0])\n"
                        "    assert score(encoded) > 0\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="requirements.txt",
                    purpose="dependencies",
                    content="# standard library only\n",
                ),
            ],
        )

        quality = assess_implementation_quality(bundle)

        self.assertGreaterEqual(quality["overall_score"], 4.0)
        self.assertEqual(quality["metrics"]["python_files"], 4)
        self.assertTrue(quality["metrics"]["has_tests"])
        self.assertTrue(quality["passes_minimum_quality"])

    def test_quality_merges_blueprint_coverage_failures(self) -> None:
        from schemas.reproduction_schema import BlueprintFile, ImplementationBlueprint

        blueprint = ImplementationBlueprint(
            files=[
                BlueprintFile(
                    path="model.py",
                    responsibility="method",
                    required_symbols=["run_model"],
                ),
                BlueprintFile(
                    path="tests/test_dataflow.py",
                    responsibility="test",
                    required_symbols=["test_synthetic_dataflow"],
                ),
            ],
            required_entrypoints=["python main.py --smoke-test"],
        )
        bundle = ImplementationBundle(
            smoke_test_command="python main.py --smoke-test",
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="def main() -> None:\n    print('ok')\n",
                )
            ],
        )

        quality = assess_implementation_quality(bundle, blueprint=blueprint)

        self.assertFalse(quality["passes_minimum_quality"])
        self.assertIn("missing_blueprint_files", quality["issue_codes"])
        self.assertIn("blueprint", quality["metrics"])

    def test_fallback_artifact_names_fail_minimum_quality(self) -> None:
        bundle = ImplementationBundle(
            project_name="fallback_analysis_valid_llm_result_unavailable",
            summary="Valid LLM result unavailable.",
            smoke_test_command="python main.py --smoke-test",
            files=[
                GeneratedCodeFile(
                    path="README.md",
                    purpose="docs",
                    content="# Reproduction\n",
                ),
                GeneratedCodeFile(
                    path="config.py",
                    purpose="configuration",
                    content="DEFAULT_SEED = 7\nHARDWARE_TARGET = 'CPU'\n",
                ),
                GeneratedCodeFile(
                    path="unavailable.py",
                    purpose="fallback method",
                    content=(
                        "class MiniModel:\n"
                        "    def run(self) -> float:\n"
                        "        return 1.0\n\n"
                        "def run_unavailable() -> dict:\n"
                        "    return {'status': 'ok'}\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content=(
                        "from unavailable import run_unavailable\n\n"
                        "def main() -> None:\n"
                        "    print(run_unavailable()['status'])\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="tests/test_dataflow.py",
                    purpose="tests",
                    content=(
                        "from unavailable import run_unavailable\n\n"
                        "def test_smoke_dataflow() -> None:\n"
                        "    assert run_unavailable()['status'] == 'ok'\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="requirements.txt",
                    purpose="dependencies",
                    content="# standard library only\n",
                ),
            ],
        )

        quality = assess_implementation_quality(bundle)

        self.assertIn("unavailable_fallback_artifact", quality["issue_codes"])
        self.assertFalse(quality["passes_minimum_quality"])

    def test_assertion_free_tests_fail_minimum_quality(self) -> None:
        bundle = ImplementationBundle(
            project_name="paper_method",
            summary="Looks structured but test does not verify behavior.",
            smoke_test_command="python main.py --smoke-test",
            files=[
                GeneratedCodeFile(
                    path="README.md",
                    purpose="docs",
                    content="# Paper Method\n",
                ),
                GeneratedCodeFile(
                    path="config.py",
                    purpose="configuration",
                    content="VALUE = 1\n",
                ),
                GeneratedCodeFile(
                    path="model.py",
                    purpose="method",
                    content=(
                        "def encode(values: list[float]) -> list[float]:\n"
                        "    total = sum(values) or 1.0\n"
                        "    return [value / total for value in values]\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="from model import encode\nprint(encode([1.0]))\n",
                ),
                GeneratedCodeFile(
                    path="tests/test_model.py",
                    purpose="tests",
                    content=(
                        "from model import encode\n\n"
                        "def test_encode_imports() -> None:\n"
                        "    encode([1.0, 2.0])\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="requirements.txt",
                    purpose="dependencies",
                    content="# standard library only\n",
                ),
            ],
        )

        quality = assess_implementation_quality(bundle)

        self.assertIn("assertion_free_tests", quality["issue_codes"])
        self.assertFalse(quality["passes_minimum_quality"])

    def test_generic_artifact_names_fail_minimum_quality(self) -> None:
        bundle = ImplementationBundle(
            project_name="paper_method",
            summary="Uses generic names despite having files.",
            smoke_test_command="python main.py --smoke-test",
            files=[
                GeneratedCodeFile(
                    path="README.md",
                    purpose="docs",
                    content="# Paper Method\n",
                ),
                GeneratedCodeFile(
                    path="placeholder_model.py",
                    purpose="method",
                    content=(
                        "class DummyModel:\n"
                        "    def run(self, values: list[float]) -> float:\n"
                        "        return sum(values)\n"
                    ),
                ),
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="from placeholder_model import DummyModel\nprint(DummyModel().run([1.0]))\n",
                ),
                GeneratedCodeFile(
                    path="tests/test_model.py",
                    purpose="tests",
                    content=(
                        "from placeholder_model import DummyModel\n\n"
                        "def test_model_dataflow() -> None:\n"
                        "    assert DummyModel().run([1.0, 2.0]) == 3.0\n"
                    ),
                ),
            ],
        )

        quality = assess_implementation_quality(bundle)

        self.assertIn("generic_artifact_names", quality["issue_codes"])
        self.assertFalse(quality["passes_minimum_quality"])

    def test_quality_gate_forces_revision_when_review_accepts_thin_code(self) -> None:
        review = CodeReview(
            overall_score=4.8,
            verdict="accept",
            detected_problems=[],
            revision_suggestions=[],
        )
        quality = {
            "overall_score": 2.4,
            "passes_minimum_quality": False,
            "issues": [
                "Generated implementation is a thin single-file scaffold.",
                "Generated bundle does not include tests under tests/.",
            ],
            "suggestions": [
                "Separate configuration, method modules, and entry point when justified.",
                "Add a smoke or dataflow test under tests/.",
            ],
        }

        merged = _merge_quality_into_review(review, quality)

        self.assertEqual(merged.verdict, "revise")
        self.assertLessEqual(merged.overall_score, 3.0)
        self.assertIn(
            "Generated implementation is a thin single-file scaffold.",
            merged.detected_problems,
        )
        self.assertIn(
            "Add a smoke or dataflow test under tests/.",
            merged.revision_suggestions,
        )


if __name__ == "__main__":
    unittest.main()
