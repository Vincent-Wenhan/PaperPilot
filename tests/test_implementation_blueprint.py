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
        self.assertTrue(blueprint.files)
        self.assertTrue(blueprint.quality_requirements)
        self.assertTrue(blueprint.forbidden_patterns)

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
        bundle = ImplementationBundle(
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="def main() -> None:\n    print('ok')\n",
                )
            ]
        )

        coverage = assess_blueprint_coverage(bundle, blueprint)

        self.assertFalse(coverage["passes_blueprint_coverage"])
        self.assertIn("missing_blueprint_files", coverage["issue_codes"])
        self.assertTrue(coverage["issues"])
        self.assertTrue(coverage["suggestions"])


if __name__ == "__main__":
    unittest.main()
