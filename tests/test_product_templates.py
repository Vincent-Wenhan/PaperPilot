from __future__ import annotations

import unittest

from productize.product_templates import (
    build_adapter_source,
    build_client_source,
    build_index_source,
    build_static_bundle_sources,
    select_product_template,
)


class ProductTemplateTests(unittest.TestCase):
    def test_explicit_preference_wins(self) -> None:
        self.assertEqual(
            select_product_template("", "", "", "", "Image"),
            "image",
        )

    def test_auto_selects_supported_template_keywords(self) -> None:
        cases = [
            ("image segmentation and OCR", "image"),
            ("question answering and text classification", "text"),
            ("object tracking in video", "video"),
            ("unknown scientific method", "file"),
        ]
        for method_info, expected in cases:
            with self.subTest(method_info=method_info):
                self.assertEqual(
                    select_product_template("", method_info, "", ""),
                    expected,
                )

    def test_invalid_preference_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "preferred_type"):
            select_product_template("", "", "", "", "audio")

    def test_generated_sources_contain_template_specific_static_ui_and_adapter(self) -> None:
        expected_components = {
            "image": '"accept": "image/*"',
            "text": '"type": "textarea"',
            "video": '"accept": "video/*"',
            "file": '"type": "file"',
        }
        for template_type, component in expected_components.items():
            with self.subTest(template_type=template_type):
                index_source = build_index_source(template_type)
                client_source = build_client_source(template_type)
                adapter_source = build_adapter_source(template_type, "../workspace")
                self.assertIn('<main id="app"', index_source)
                self.assertIn(component, client_source)
                self.assertIn("ModelAdapter", client_source)
                self.assertIn("mockMode = true", adapter_source)
                self.assertIn("class ModelAdapter", adapter_source)
                self.assertIn(f'"type": "{template_type}"', adapter_source)
                self.assertNotIn("streamlit", index_source.lower())
                self.assertNotIn("streamlit", client_source.lower())
                self.assertNotIn("streamlit", adapter_source.lower())

    def test_static_bundle_has_manifest_driven_frontend_and_backend_files(self) -> None:
        bundle = build_static_bundle_sources(
            "text",
            product_spec="# Product\n\n## Product Name\n\nEvidence Console",
            frontend_plan="# Frontend\n\nUse a focused review workflow.",
        )

        self.assertIn("frontend/index.html", bundle)
        self.assertIn("frontend/app.js", bundle)
        self.assertIn("frontend/adapter.js", bundle)
        self.assertIn("backend/main.py", bundle)
        self.assertIn("backend/adapter.py", bundle)
        self.assertIn("requirements.txt", bundle)
        self.assertIn("Evidence Console", bundle["frontend/index.html"])
        self.assertIn("Use a focused review workflow.", bundle["frontend/app.js"])
        self.assertIn("FastAPI", bundle["backend/main.py"])
        for source in bundle.values():
            self.assertNotIn("streamlit", source.lower())


if __name__ == "__main__":
    unittest.main()
