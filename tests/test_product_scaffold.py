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
                        product_spec="# Demo Product",
                        adapter_plan="# Adapter Plan",
                        frontend_plan="# Frontend Plan",
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
                    self.assertEqual(model.predict("demo")["type"], template_type)

                    inspection = inspect_generated_product(output_dir)
                    self.assertEqual(inspection["missing_files"], [])
                    self.assertTrue(inspection["syntax_ok"])
                    self.assertTrue(inspection["can_run_mock"])
                    self.assertTrue(inspection["readme_has_run_command"])

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

    def test_inspector_reports_missing_and_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "app.py").write_text("invalid python (", encoding="utf-8")
            inspection = inspect_generated_product(output_dir)
            self.assertIn("adapter.py", inspection["missing_files"])
            self.assertFalse(inspection["syntax_ok"])
            self.assertTrue(inspection["compile_errors"])


if __name__ == "__main__":
    unittest.main()
