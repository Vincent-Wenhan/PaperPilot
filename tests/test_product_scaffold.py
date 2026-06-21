from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from productize.product_scaffold import scaffold_product
from productize.product_tester import inspect_generated_product


class ProductScaffoldTests(unittest.TestCase):
    def test_scaffold_generates_complete_mock_bundle_for_each_template(self) -> None:
        required = {
            "index.html",
            "app.js",
            "adapter.js",
            "styles.css",
            "README.md",
            "product_spec.md",
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

                    inspection = inspect_generated_product(output_dir)
                    self.assertEqual(inspection["missing_files"], [])
                    self.assertTrue(inspection["syntax_ok"])
                    self.assertTrue(inspection["can_run_mock"])
                    self.assertTrue(inspection["readme_has_run_command"])
                    self.assertTrue(inspection["run_launcher_ok"])
                    self.assertTrue(inspection["has_rich_layout"])

                    index_source = (output_dir / "index.html").read_text(encoding="utf-8")
                    app_source = (output_dir / "app.js").read_text(encoding="utf-8")
                    self.assertIn("Evidence Explorer", index_source)
                    self.assertIn("Rank evidence snippets", app_source)
                    self.assertIn("Course module selector", app_source)
                    self.assertIn("Misconception sensitivity threshold", app_source)
                    self.assertIn("Ranked misconception summary", app_source)
                    self.assertIn("next_action", app_source)
                    self.assertNotIn("streamlit", app_source.lower())

                    adapter_source = (output_dir / "adapter.js").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("class ModelAdapter", adapter_source)
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

            app_source = (output_dir / "app.js").read_text(encoding="utf-8")
            self.assertIn("Evidence Console", app_source)
            self.assertIn("Review mode", app_source)
            self.assertIn("Evidence summary", app_source)
            self.assertIn("Paste evidence to start.", app_source)
            self.assertIn('"controlId": "review_mode"', app_source)
            self.assertIn('"controlId": "review_mode_2"', app_source)
            self.assertIn('"type": "range"', app_source)
            inspection = inspect_generated_product(output_dir)
            self.assertTrue(inspection["has_rich_layout"])
            self.assertTrue(inspection["run_launcher_ok"])
            self.assertTrue(inspection["ui_spec_coverage"]["structured_controls"])
            self.assertTrue(inspection["ui_spec_coverage"]["result_components"])
            self.assertTrue(inspection["ui_spec_coverage"]["state_copy"])

    def test_inspector_reports_missing_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "app.js").write_text("function invalid (", encoding="utf-8")
            inspection = inspect_generated_product(output_dir)
            self.assertIn("adapter.js", inspection["missing_files"])
            self.assertFalse(inspection["syntax_ok"])
            self.assertTrue(inspection["compile_errors"])
            self.assertFalse(inspection["has_rich_layout"])

    def test_inspector_does_not_write_bytecode_cache_or_require_python_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "outputs").mkdir()
            (output_dir / "index.html").write_text(
                '<main id="app"></main><script type="module" src="./app.js"></script>\n',
                encoding="utf-8",
            )
            (output_dir / "app.js").write_text(
                "const UI_SPEC_MARKERS = { structured_controls: true, result_components: true, state_copy: true };\n"
                "const tabs = ['Summary', 'Evidence & Limits', 'Export'];\n"
                "console.log(UI_SPEC_MARKERS, tabs);\n",
                encoding="utf-8",
            )
            (output_dir / "adapter.js").write_text(
                "class ModelAdapter { constructor({ mockMode = true } = {}) { this.mockMode = mockMode; } predict() { if (this.mockMode) return {}; } }\n",
                encoding="utf-8",
            )
            (output_dir / "styles.css").write_text(
                ".workspace-grid{}\n.panel{}\n.json-block{}\n",
                encoding="utf-8",
            )
            (output_dir / "README.md").write_text(
                "Open `index.html` directly or run `python -m http.server 8000`.\n",
                encoding="utf-8",
            )
            (output_dir / "product_spec.md").write_text("# Spec\n", encoding="utf-8")

            inspection = inspect_generated_product(output_dir)

            self.assertTrue(inspection["syntax_ok"])
            self.assertFalse((output_dir / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
