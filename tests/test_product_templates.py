from __future__ import annotations

import unittest

from productize.product_templates import (
    build_adapter_source,
    build_app_source,
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

    def test_generated_sources_contain_template_specific_ui_and_adapter(self) -> None:
        expected_components = {
            "image": 'st.file_uploader("Upload an image"',
            "text": 'st.text_area("Input text"',
            "video": 'st.file_uploader("Upload a video"',
            "file": 'st.file_uploader("Upload a file"',
        }
        for template_type, component in expected_components.items():
            with self.subTest(template_type=template_type):
                app_source = build_app_source(template_type)
                adapter_source = build_adapter_source(template_type, "../workspace")
                self.assertIn(component, app_source)
                self.assertIn("ModelAdapter", app_source)
                self.assertIn("mock_mode=True", app_source)
                self.assertIn("class ModelAdapter", adapter_source)
                self.assertIn(f'"type": "{template_type}"', adapter_source)
                compile(app_source, "app.py", "exec")
                compile(adapter_source, "adapter.py", "exec")


if __name__ == "__main__":
    unittest.main()
