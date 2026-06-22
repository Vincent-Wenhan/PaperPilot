from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from productize.product_scaffold import scaffold_product
from productize.product_tester import inspect_generated_product


class ProductScaffoldTests(unittest.TestCase):
    def test_scaffold_generates_complete_mock_bundle_for_each_template(self) -> None:
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
                    manifest = json.loads(
                        (output_dir / "manifest.json").read_text(encoding="utf-8")
                    )
                    manifest_paths = {item["path"] for item in manifest["files"]}
                    self.assertIn("frontend/index.html", manifest_paths)
                    self.assertIn("frontend/app.js", manifest_paths)
                    self.assertIn("backend/main.py", manifest_paths)
                    self.assertIn("backend/adapter.py", manifest_paths)
                    self.assertIn("requirements.txt", manifest_paths)
                    self.assertIn("README.md", manifest_paths)
                    self.assertIn("product_spec.md", manifest_paths)
                    self.assertIn("outputs/.gitkeep", manifest_paths)
                    self.assertEqual(manifest["entrypoints"]["frontend"], "frontend/index.html")
                    self.assertEqual(manifest["entrypoints"]["backend"], "backend/main.py")
                    self.assertTrue(manifest["mock_first"])

                    inspection = inspect_generated_product(output_dir)
                    self.assertEqual(inspection["missing_files"], [])
                    self.assertTrue(inspection["syntax_ok"])
                    self.assertTrue(inspection["can_run_mock"])
                    self.assertTrue(inspection["readme_has_run_command"])
                    self.assertTrue(inspection["run_launcher_ok"])
                    self.assertTrue(inspection["has_rich_layout"])
                    self.assertTrue(inspection["manifest_ok"])

                    index_source = (output_dir / "frontend" / "index.html").read_text(encoding="utf-8")
                    app_source = (output_dir / "frontend" / "app.js").read_text(encoding="utf-8")
                    self.assertIn("Evidence Explorer", index_source)
                    self.assertIn("Rank evidence snippets", app_source)
                    self.assertIn("Course module selector", app_source)
                    self.assertIn("Misconception sensitivity threshold", app_source)
                    self.assertIn("Ranked misconception summary", app_source)
                    self.assertIn("next_action", app_source)
                    self.assertNotIn("streamlit", app_source.lower())

                    adapter_source = (output_dir / "backend" / "adapter.py").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("class ModelAdapter", adapter_source)
                    self.assertIn("def predict", adapter_source)
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

            app_source = (output_dir / "frontend" / "app.js").read_text(encoding="utf-8")
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

    def test_scaffold_uses_prototype_generated_files_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            scaffold_product(
                template_type="text",
                product_spec="# Product\n\n## Product Name\n\nCustom Console",
                adapter_plan="# Adapter",
                frontend_plan="# Frontend",
                repo_path="../workspace",
                output_dir=output_dir,
                prototype_plan={
                    "generated_files": [
                        {
                            "path": "frontend/custom.js",
                            "purpose": "Custom frontend behavior",
                            "content": "export const custom = true;\n",
                            "role": "frontend",
                        },
                        {
                            "path": "backend/custom_adapter.py",
                            "purpose": "Custom backend adapter",
                            "content": "def predict(payload):\n    return {'ok': True, 'payload': payload}\n",
                            "role": "backend",
                        },
                    ],
                    "backend_endpoints": [
                        {
                            "path": "/predict",
                            "method": "POST",
                            "purpose": "Run custom adapter prediction",
                        }
                    ],
                    "dependencies": [
                        {"name": "fastapi", "version": ">=0.115,<1", "kind": "python"}
                    ],
                },
            )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            paths = {item["path"] for item in manifest["files"]}
            self.assertIn("frontend/custom.js", paths)
            self.assertIn("backend/custom_adapter.py", paths)
            self.assertIn("backend/main.py", paths)
            self.assertEqual(manifest["backend_endpoints"][0]["path"], "/predict")

    def test_inspector_reports_missing_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "frontend").mkdir()
            (output_dir / "frontend" / "app.js").write_text(
                "function invalid (",
                encoding="utf-8",
            )
            inspection = inspect_generated_product(output_dir)
            self.assertIn("backend/adapter.py", inspection["missing_files"])
            self.assertFalse(inspection["syntax_ok"])
            self.assertTrue(inspection["compile_errors"])
            self.assertFalse(inspection["has_rich_layout"])

    def test_inspector_does_not_write_bytecode_cache_or_require_python_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "frontend").mkdir()
            (output_dir / "backend").mkdir()
            (output_dir / "outputs").mkdir()
            manifest = {
                "mode": "productize",
                "mock_first": True,
                "entrypoints": {
                    "frontend": "frontend/index.html",
                    "backend": "backend/main.py",
                    "adapter": "backend/adapter.py",
                },
                "backend_endpoints": [{"path": "/predict", "method": "POST"}],
                "files": [
                    {"path": "frontend/index.html"},
                    {"path": "frontend/app.js"},
                    {"path": "frontend/styles.css"},
                    {"path": "backend/main.py"},
                    {"path": "backend/adapter.py"},
                    {"path": "requirements.txt"},
                    {"path": "README.md"},
                    {"path": "product_spec.md"},
                ],
            }
            (output_dir / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )
            (output_dir / "frontend" / "index.html").write_text(
                '<main id="app"></main><script type="module" src="./app.js"></script>\n',
                encoding="utf-8",
            )
            (output_dir / "frontend" / "app.js").write_text(
                "const UI_SPEC_MARKERS = { structured_controls: true, result_components: true, state_copy: true };\n"
                "const tabs = ['Summary', 'Evidence & Limits', 'Export'];\n"
                "console.log(UI_SPEC_MARKERS, tabs);\n",
                encoding="utf-8",
            )
            (output_dir / "backend" / "main.py").write_text(
                "from fastapi import FastAPI\napp = FastAPI()\n",
                encoding="utf-8",
            )
            (output_dir / "backend" / "adapter.py").write_text(
                "class ModelAdapter:\n    def __init__(self, mock_mode=True):\n        self.mock_mode = mock_mode\n    def predict(self, payload):\n        return {'mock_mode': self.mock_mode}\n",
                encoding="utf-8",
            )
            (output_dir / "frontend" / "styles.css").write_text(
                ".workspace-grid{}\n.panel{}\n.json-block{}\n",
                encoding="utf-8",
            )
            (output_dir / "README.md").write_text(
                "Run `python -m uvicorn backend.main:app --reload --port 8000` and `python -m http.server 8080 -d frontend`.\n",
                encoding="utf-8",
            )
            (output_dir / "requirements.txt").write_text("fastapi>=0.115,<1\n", encoding="utf-8")
            (output_dir / "product_spec.md").write_text("# Spec\n", encoding="utf-8")

            inspection = inspect_generated_product(output_dir)

            self.assertTrue(inspection["syntax_ok"])
            self.assertFalse((output_dir / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
