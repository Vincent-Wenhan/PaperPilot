from __future__ import annotations

import unittest

from productize.ui_spec import build_product_ui_spec
from schemas.product_schema import PRD, ProductPlan, PrototypePlan


class ProductUISpecTests(unittest.TestCase):
    def test_builds_typed_controls_and_result_components(self) -> None:
        plan = ProductPlan(
            jtbd="Help instructors triage student answers.",
            selected_product="Misconception Triage",
            selection_reason="High classroom value.",
            prd=PRD(
                product_name="Misconception Triage",
                problem_statement="Teachers need fast evidence review.",
                core_features=["Rank weak concepts", "Export intervention checklist"],
                target_users=["Teachers"],
            ),
        )
        prototype = PrototypePlan(
            template_type="file",
            page_structure=["Upload answers", "Review ranked evidence"],
            user_inputs=["Course module selector", "Misconception sensitivity threshold"],
            system_outputs=["Ranked misconception summary", "Teacher intervention checklist"],
            mock_result={"confidence": 0.82, "next_action": "Assign mini lesson"},
            adapter_boundary=["preprocess answers", "postprocess evidence"],
        )

        spec = build_product_ui_spec(plan, prototype)

        self.assertEqual(spec.product_name, "Misconception Triage")
        self.assertTrue(any(control.control_type == "selectbox" for control in spec.input_controls))
        self.assertTrue(any(control.control_type == "slider" for control in spec.input_controls))
        self.assertTrue(any(component.component_type == "metric" for component in spec.result_components))
        self.assertIn("empty", spec.states.model_dump())

    def test_sparse_prototype_gets_conservative_spec(self) -> None:
        plan = ProductPlan(
            jtbd="Explore a paper capability.",
            selected_product="Paper Demo",
            selection_reason="Default mock-first product.",
            prd=PRD(product_name="Paper Demo", problem_statement="Need a demo."),
        )
        spec = build_product_ui_spec(plan, PrototypePlan(template_type="text"))

        self.assertEqual(spec.template_type, "text")
        self.assertGreaterEqual(len(spec.page_sections), 4)
        self.assertTrue(spec.input_controls)
        self.assertTrue(spec.result_components)
        self.assertTrue(spec.visual_rules)


if __name__ == "__main__":
    unittest.main()
