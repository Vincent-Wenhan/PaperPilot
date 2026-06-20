from __future__ import annotations

import unittest

from schemas.reproduction_schema import (
    GeneratedCodeFile,
    ImplementationBundle,
    MethodModule,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)
from tools.implementation_blueprint import (
    assess_blueprint_coverage,
    build_implementation_blueprint,
)


class ImplementationBlueprintTests(unittest.TestCase):
    def test_builds_multi_file_blueprint_from_method_modules(self) -> None:
        paper = PaperUnderstanding(
            title="Contrastive Graph Learner",
            method_modules=[
                MethodModule(
                    name="Graph Encoder",
                    purpose="Encode graph neighborhoods",
                    inputs=["node features"],
                    outputs=["node embeddings"],
                ),
                MethodModule(
                    name="Contrastive Objective",
                    purpose="Score positive and negative pairs",
                    inputs=["node embeddings"],
                    outputs=["loss"],
                ),
            ],
            end_to_end_dataflow=[
                "Load synthetic graph features",
                "Encode neighborhoods",
                "Compute contrastive score",
            ],
        )
        repository = RepositoryUnderstanding(detected_framework="pytorch")
        plan = ReproductionPlan(
            implementation_strategy="Implement a tiny synthetic graph dataflow."
        )

        blueprint = build_implementation_blueprint(
            paper,
            repository,
            plan,
            hardware="CPU only",
            goal="minimal training experiment",
        )

        paths = [item.path for item in blueprint.files]
        self.assertIn("README.md", paths)
        self.assertIn("config.py", paths)
        self.assertIn("main.py", paths)
        self.assertIn("tests/test_dataflow.py", paths)
        self.assertTrue(
            any(
                path.endswith(".py") and path not in {"main.py", "config.py"}
                for path in paths
            )
        )
        self.assertIn("python main.py --smoke-test", blueprint.required_entrypoints)
        self.assertGreaterEqual(len(blueprint.core_dataflow), 3)

    def test_sparse_inputs_still_build_conservative_blueprint(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(title=""),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="run official demo",
        )

        self.assertEqual(blueprint.project_name, "paperpilot_reproduction")
        files_by_path = {item.path: item for item in blueprint.files}
        self.assertIn("README.md", files_by_path)
        self.assertIn("config.py", files_by_path)
        self.assertIn("model.py", files_by_path)
        self.assertIn("main.py", files_by_path)
        self.assertIn("tests/test_dataflow.py", files_by_path)
        self.assertIn("requirements.txt", files_by_path)
        self.assertIn("run_model", files_by_path["model.py"].required_symbols)
        self.assertIn("python main.py --smoke-test", blueprint.required_entrypoints)
        self.assertTrue(blueprint.quality_requirements)
        self.assertTrue(blueprint.forbidden_patterns)

    def test_fallback_research_module_does_not_become_unavailable_file(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(
                title="Fallback analysis - valid LLM result unavailable",
                method_modules=[
                    MethodModule(
                        name="Unavailable",
                        purpose="No valid LLM paper analysis is available.",
                        evidence=["No valid LLM analysis was available."],
                    )
                ],
                end_to_end_dataflow=["Not analyzed."],
            ),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="minimal training experiment",
        )

        paths = {item.path for item in blueprint.files}
        self.assertEqual(blueprint.project_name, "paperpilot_reproduction")
        self.assertNotIn("unavailable.py", paths)
        self.assertIn("model.py", paths)

    def test_module_file_paths_are_unique_and_do_not_collide_with_static_files(
        self,
    ) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(
                method_modules=[
                    MethodModule(name="Main", purpose="Reserved main module"),
                    MethodModule(name="Config", purpose="Reserved config module"),
                    MethodModule(name="Main", purpose="Duplicate main module"),
                ]
            ),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="minimal training experiment",
        )

        paths = [item.path for item in blueprint.files]
        self.assertEqual(len(paths), len(set(paths)))

        static_paths = {
            "README.md",
            "config.py",
            "main.py",
            "tests/test_dataflow.py",
            "requirements.txt",
        }
        module_paths = [
            item.path
            for item in blueprint.files
            if item.responsibility
            in {
                "Reserved main module",
                "Reserved config module",
                "Duplicate main module",
            }
        ]

        self.assertEqual(3, len(module_paths))
        self.assertTrue(static_paths.issubset(paths))
        self.assertFalse(static_paths.intersection(module_paths))
        self.assertEqual(len(module_paths), len(set(module_paths)))

    def test_coverage_flags_missing_planned_file_and_symbol(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(
                method_modules=[MethodModule(name="Encoder", purpose="Encode inputs")]
            ),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="minimal training experiment",
        )
        planned_method_file = next(
            item for item in blueprint.files if item.path == "encoder.py"
        )
        bundle = ImplementationBundle(
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="def main() -> None:\n    print('ok')\n",
                ),
                GeneratedCodeFile(
                    path=planned_method_file.path,
                    purpose=planned_method_file.responsibility,
                    content="def helper() -> None:\n    pass\n",
                )
            ]
        )

        coverage = assess_blueprint_coverage(bundle, blueprint)

        self.assertFalse(coverage["passes_blueprint_coverage"])
        self.assertIn("missing_blueprint_files", coverage["issue_codes"])
        self.assertIn("missing_required_symbols", coverage["issue_codes"])
        self.assertGreater(coverage["metrics"]["missing_symbol_count"], 0)
        self.assertTrue(coverage["issues"])
        self.assertTrue(coverage["suggestions"])

    def test_python_symbol_coverage_ignores_comment_only_occurrence(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(title=""),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="run official demo",
        )
        bundle = ImplementationBundle(
            files=[
                GeneratedCodeFile(
                    path="model.py",
                    purpose="fallback",
                    content="# run_model\nVALUE = 1\n",
                )
            ]
        )

        coverage = assess_blueprint_coverage(bundle, blueprint)

        self.assertFalse(coverage["passes_blueprint_coverage"])
        self.assertIn("missing_required_symbols", coverage["issue_codes"])
        self.assertGreater(coverage["metrics"]["missing_symbol_count"], 0)

    def test_python_symbol_coverage_ignores_nested_local_declarations(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(title=""),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="run official demo",
        )
        bundle = ImplementationBundle(
            files=[
                GeneratedCodeFile(
                    path="config.py",
                    purpose="config",
                    content=(
                        "def helper() -> None:\n"
                        "    DEFAULT_SEED = 1\n"
                        "    class HARDWARE_TARGET:\n"
                        "        pass\n"
                    ),
                )
            ]
        )

        coverage = assess_blueprint_coverage(bundle, blueprint)

        self.assertFalse(coverage["passes_blueprint_coverage"])
        self.assertIn("missing_required_symbols", coverage["issue_codes"])
        self.assertGreaterEqual(coverage["metrics"]["missing_symbol_count"], 2)

    def test_python_symbol_coverage_accepts_top_level_tuple_assignment(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(title=""),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="run official demo",
        )
        bundle = ImplementationBundle(
            files=[
                GeneratedCodeFile(
                    path="README.md",
                    purpose="docs",
                    content="Smoke reproduction\n",
                ),
                GeneratedCodeFile(
                    path="requirements.txt",
                    purpose="dependencies",
                    content="",
                ),
                GeneratedCodeFile(
                    path="config.py",
                    purpose="config",
                    content='DEFAULT_SEED, HARDWARE_TARGET = 123, "CPU"\n',
                ),
                GeneratedCodeFile(
                    path="model.py",
                    purpose="fallback",
                    content="def run_model() -> dict:\n    return {}\n",
                ),
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="def main() -> None:\n    pass\n",
                ),
                GeneratedCodeFile(
                    path="tests/test_dataflow.py",
                    purpose="tests",
                    content="def test_smoke_dataflow() -> None:\n    pass\n",
                ),
            ],
            smoke_test_command="python main.py --smoke-test",
        )

        coverage = assess_blueprint_coverage(bundle, blueprint)

        self.assertTrue(coverage["passes_blueprint_coverage"])
        self.assertNotIn("missing_required_symbols", coverage["issue_codes"])


if __name__ == "__main__":
    unittest.main()
