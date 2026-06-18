from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from productize.product_scaffold import scaffold_product
from productize.product_tester import inspect_generated_product


def _load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("generated_adapter", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load generated adapter.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductScaffoldTests(unittest.TestCase):
    def test_scaffold_generates_complete_mock_bundle_for_each_template(self) -> None:
        required = {
            "app.py",
            "adapter.py",
            "run_product.py",
            "README.md",
            "product_spec.md",
            "requirements.txt",
            "outputs",
        }
        for template_type in ("image", "text", "video", "file"):
            with self.subTest(template_type=template_type):
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_dir = Path(temp_dir) / "generated_product"
                    result = scaffold_product(
                        template_type=template_type,
                        product_spec=(
                            "# Demo Product\n\n"
                            "## Product Name\n\nEvidence Explorer\n\n"
                            "## PRD\n\n"
                            "### Core Features\n"
                            "- Rank evidence snippets\n"
                            "- Export structured findings\n"
                        ),
                        adapter_plan="# Adapter Plan",
                        frontend_plan=(
                            "# Frontend Plan\n\n"
                            "## Page Structure\n"
                            "- Evidence intake\n"
                            "- Result review\n"
                        ),
                        prototype_plan={
                            "page_structure": [
                                "Upload a learner answer sheet",
                                "Review weak concept evidence",
                            ],
                            "user_inputs": [
                                "Course module selector",
                                "Misconception sensitivity threshold",
                            ],
                            "system_outputs": [
                                "Ranked misconception summary",
                                "Teacher intervention checklist",
                            ],
                            "mock_result": {
                                "confidence": 0.82,
                                "next_action": "Assign a targeted mini lesson",
                            },
                            "adapter_boundary": [
                                "preprocess uploaded answer sheet",
                                "postprocess misconception evidence",
                            ],
                            "real_integration_placeholder": (
                                "Review repository inference.py before disabling mock mode."
                            ),
                        },
                        repo_path="../workspace/demo",
                        output_dir=output_dir,
                    )

                    self.assertTrue(result["success"])
                    self.assertEqual(
                        {path.name for path in output_dir.iterdir()},
                        required,
                    )
                    adapter = _load_adapter(output_dir / "adapter.py")
                    model = adapter.ModelAdapter()
                    self.assertTrue(model.setup()["ready"])
                    self.assertIsNone(model.load_model())
                    demo_result = model.predict("demo")
                    changed_result = model.predict("different input")
                    self.assertEqual(demo_result["type"], template_type)
                    self.assertIn("input_summary", demo_result)
                    self.assertIn("input_signature", demo_result)
                    self.assertNotEqual(
                        demo_result["input_signature"],
                        changed_result["input_signature"],
                    )

                    inspection = inspect_generated_product(output_dir)
                    self.assertEqual(inspection["missing_files"], [])
                    self.assertTrue(inspection["syntax_ok"])
                    self.assertTrue(inspection["can_run_mock"])
                    self.assertTrue(inspection["readme_has_run_command"])
                    self.assertTrue(inspection["run_launcher_ok"])
                    self.assertTrue(inspection["has_rich_layout"])

                    app_source = (output_dir / "app.py").read_text(encoding="utf-8")
                    self.assertIn("Evidence Explorer", app_source)
                    self.assertIn("st.sidebar", app_source)
                    self.assertIn("st.tabs", app_source)
                    self.assertIn("Rank evidence snippets", app_source)
                    self.assertIn("Course module selector", app_source)
                    self.assertIn("Misconception sensitivity threshold", app_source)
                    self.assertIn("Ranked misconception summary", app_source)
                    self.assertIn("next_action", app_source)

                    adapter_source = (output_dir / "adapter.py").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("Assign a targeted mini lesson", adapter_source)

    def test_scaffold_backs_up_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            output_dir.mkdir()
            (output_dir / "marker.txt").write_text("keep me", encoding="utf-8")

            result = scaffold_product(
                template_type="file",
                product_spec="# Demo",
                adapter_plan="# Adapter",
                frontend_plan="# Frontend",
                repo_path="../workspace",
                output_dir=output_dir,
            )

            backup_dir = Path(result["backup_dir"])
            self.assertTrue(backup_dir.name.startswith("generated_product_backup_"))
            self.assertEqual(
                (backup_dir / "marker.txt").read_text(encoding="utf-8"),
                "keep me",
            )

    def test_scaffold_renders_structured_ui_spec(self) -> None:
        from schemas.product_schema import (
            ProductUISpec,
            ResultComponent,
            UIControl,
            UIStateCopy,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            ui_spec = ProductUISpec(
                product_name="Evidence Console",
                template_type="text",
                page_sections=["Prepare case", "Run analysis", "Review evidence"],
                input_controls=[
                    UIControl(
                        control_id="review_mode",
                        label="Review mode",
                        control_type="selectbox",
                        options=["Default", "Strict"],
                        default="Default",
                    ),
                    UIControl(
                        control_id="review_mode",
                        label="Strictness threshold",
                        control_type="slider",
                        default=1.4,
                    ),
                ],
                result_components=[
                    ResultComponent(
                        component_id="confidence",
                        label="Confidence",
                        component_type="metric",
                        source_key="confidence",
                    ),
                    ResultComponent(
                        component_id="evidence",
                        label="Evidence summary",
                        component_type="summary",
                        source_key="evidence",
                    ),
                ],
                mock_result_schema={"confidence": "float", "evidence": "list"},
                states=UIStateCopy(
                    empty="Paste evidence to start.",
                    loading="Reviewing evidence.",
                    success="Evidence review complete.",
                    error="Evidence review failed.",
                ),
            )

            scaffold_product(
                template_type="text",
                product_spec="# Product\n\n## Product Name\n\nEvidence Console",
                adapter_plan="# Adapter",
                frontend_plan="# Frontend",
                repo_path="../workspace",
                output_dir=output_dir,
                ui_spec=ui_spec.model_dump(mode="json"),
            )

            app_source = (output_dir / "app.py").read_text(encoding="utf-8")
            self.assertIn("Evidence Console", app_source)
            self.assertIn("Review mode", app_source)
            self.assertIn("Evidence summary", app_source)
            self.assertIn("Paste evidence to start.", app_source)
            self.assertIn("context_values['review_mode']", app_source)
            self.assertIn("context_values['review_mode_2']", app_source)
            self.assertIn("key='ui_control_review_mode'", app_source)
            self.assertIn("key='ui_control_review_mode_2'", app_source)
            self.assertIn("st.slider('Strictness threshold', 0.0, 1.0, 1.0", app_source)
            inspection = inspect_generated_product(output_dir)
            self.assertTrue(inspection["has_rich_layout"])
            self.assertTrue(inspection["run_launcher_ok"])
            self.assertTrue(inspection["ui_spec_coverage"]["structured_controls"])
            self.assertTrue(inspection["ui_spec_coverage"]["result_components"])
            self.assertTrue(inspection["ui_spec_coverage"]["state_copy"])

    def test_inspector_reports_missing_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "app.py").write_text("invalid python (", encoding="utf-8")
            inspection = inspect_generated_product(output_dir)
            self.assertIn("adapter.py", inspection["missing_files"])
            self.assertFalse(inspection["syntax_ok"])
            self.assertTrue(inspection["compile_errors"])
            self.assertFalse(inspection["has_rich_layout"])

    def test_inspector_does_not_write_bytecode_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "outputs").mkdir()
            (output_dir / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            (output_dir / "adapter.py").write_text(
                "class ModelAdapter:\n"
                "    def __init__(self, mock_mode: bool = True):\n"
                "        self.mock_mode = mock_mode\n"
                "    def predict(self):\n"
                "        if self.mock_mode:\n"
                "            return None\n",
                encoding="utf-8",
            )
            (output_dir / "run_product.py").write_text(
                "print('launch')\n",
                encoding="utf-8",
            )
            (output_dir / "README.md").write_text(
                "Run with `python -m pip install -r requirements.txt` "
                "then `python run_product.py`. The launcher runs "
                "`python -m streamlit run app.py`.\n",
                encoding="utf-8",
            )
            (output_dir / "product_spec.md").write_text("# Spec\n", encoding="utf-8")
            (output_dir / "requirements.txt").write_text("streamlit\n", encoding="utf-8")

            inspection = inspect_generated_product(output_dir)

            self.assertTrue(inspection["syntax_ok"])
            self.assertFalse((output_dir / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
