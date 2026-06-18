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

    def test_duplicate_sluggable_labels_get_unique_control_ids(self) -> None:
        plan = ProductPlan(
            jtbd="Compare scoring settings.",
            selected_product="Score Demo",
            selection_reason="Tests control collisions.",
            prd=PRD(product_name="Score Demo", problem_statement="Need unique controls."),
        )
        prototype = PrototypePlan(user_inputs=["Score", "Score!", "Score"])

        spec = build_product_ui_spec(plan, prototype)
        control_ids = [control.control_id for control in spec.input_controls]

        self.assertEqual(len(control_ids), len(set(control_ids)))
        self.assertEqual(control_ids, ["score", "score_2", "score_3"])

    def test_output_mode_collision_gets_unique_result_component_id(self) -> None:
        plan = ProductPlan(
            jtbd="Review mode outputs.",
            selected_product="Mode Demo",
            selection_reason="Tests result collisions.",
            prd=PRD(product_name="Mode Demo", problem_statement="Need unique results."),
        )
        prototype = PrototypePlan(system_outputs=["Mode", "Mode!"])

        spec = build_product_ui_spec(plan, prototype)
        component_ids = [component.component_id for component in spec.result_components]

        self.assertEqual(len(component_ids), len(set(component_ids)))
        self.assertEqual(component_ids[:3], ["mode", "mode_2", "mode_3"])

    def test_blank_list_entries_are_treated_as_absent(self) -> None:
        plan = ProductPlan(
            jtbd="Explore sparse content.",
            selected_product="Blank Demo",
            selection_reason="Tests blank fallback behavior.",
            prd=PRD(product_name="Blank Demo", problem_statement="Need fallbacks."),
        )
        prototype = PrototypePlan(
            page_structure=[" ", "\t"],
            user_inputs=["", "  "],
            system_outputs=["\n"],
        )

        spec = build_product_ui_spec(plan, prototype)

        self.assertGreaterEqual(len(spec.page_sections), 4)
        self.assertNotIn("", spec.page_sections)
        self.assertEqual([control.label for control in spec.input_controls], ["file input", "Decision context"])
        self.assertEqual(
            [component.label for component in spec.result_components[1:]],
            ["Structured mock result", "Downloadable JSON"],
        )


if __name__ == "__main__":
    unittest.main()
