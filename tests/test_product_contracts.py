from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from productize.product_scaffold import scaffold_product
from productize.product_tester import inspect_generated_product
from productize.ui_spec import build_product_contract, build_product_ui_spec
from schemas.product_schema import PRD, ProductPlan, ProductVerificationReport, PrototypePlan


class ProductContractTests(unittest.TestCase):
    def test_product_contract_drives_ui_spec_controls_and_outputs(self) -> None:
        plan = ProductPlan(
            jtbd="Help researchers triage evidence.",
            selected_product="Evidence Console",
            selection_reason="High product value.",
            prd=PRD(
                product_name="Evidence Console",
                problem_statement="Researchers need grounded summaries.",
                target_users=["Researcher"],
                limitations=["Mock mode only."],
            ),
        )
        prototype = PrototypePlan(
            template_type="text",
            user_inputs=["Paper claim", "Confidence threshold"],
            system_outputs=["Evidence score", "Grounded rationale"],
            mock_result={"evidence_score": 0.84, "grounded_rationale": "Supported by abstract."},
        )

        contract = build_product_contract(plan, prototype)
        spec = build_product_ui_spec(plan, prototype, product_contract=contract)

        self.assertEqual(contract.product_name, "Evidence Console")
        self.assertEqual(contract.io.input_fields, ["paper_claim", "confidence_threshold"])
        self.assertEqual(contract.io.output_fields, ["evidence_score", "grounded_rationale"])
        self.assertEqual(
            [control.control_id for control in spec.input_controls[:2]],
            contract.io.input_fields,
        )
        self.assertTrue(
            set(contract.io.output_fields).issubset(
                {component.source_key for component in spec.result_components}
            )
        )

    def test_product_tester_blocks_contract_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            contract = {
                "product_name": "Evidence Console",
                "target_user": "Researcher",
                "job_to_be_done": "Review grounded evidence.",
                "io": {
                    "input_type": "text",
                    "input_fields": ["paper_claim", "confidence_threshold"],
                    "output_fields": ["evidence_score", "grounded_rationale"],
                    "example_input": {"paper_claim": "Claim", "confidence_threshold": 0.6},
                    "example_output": {"evidence_score": 0.8, "grounded_rationale": "Grounded."},
                },
                "ux": {
                    "primary_user_action": "Analyze evidence",
                    "required_controls": ["paper_claim", "confidence_threshold"],
                    "required_result_cards": ["evidence_score", "grounded_rationale"],
                    "empty_state": "Paste a claim.",
                    "loading_state": "Analyzing.",
                    "error_state": "Could not analyze.",
                },
                "safety": {
                    "forbidden_claims": ["guaranteed SOTA"],
                    "required_disclaimers": ["mock mode"],
                    "mock_mode_boundary": "Mock evidence only.",
                },
                "acceptance_tests": ["Submit example input and see evidence fields."],
            }
            scaffold_product(
                template_type="text",
                product_spec="# Product\n\n## Product Name\n\nEvidence Console",
                adapter_plan="# Adapter",
                frontend_plan="# Frontend",
                repo_path="../workspace",
                output_dir=output_dir,
                ui_spec={
                    "product_name": "Evidence Console",
                    "template_type": "text",
                    "input_controls": [
                        {
                            "control_id": "paper_claim",
                            "label": "Paper claim",
                            "control_type": "textarea",
                        },
                    ],
                    "result_components": [
                        {
                            "component_id": "evidence_score",
                            "label": "Evidence score",
                            "source_key": "evidence_score",
                        }
                    ],
                    "mock_result_schema": {"evidence_score": "float"},
                },
            )
            (output_dir / "README.md").write_text(
                "This prototype is mock mode only, but offers guaranteed SOTA results.\n",
                encoding="utf-8",
            )

            inspection = inspect_generated_product(output_dir, product_contract=contract)

            self.assertFalse(inspection["contract_ok"])
            self.assertIn("confidence_threshold", inspection["contract_missing_controls"])
            self.assertIn("grounded_rationale", inspection["contract_missing_outputs"])
            self.assertTrue(inspection["contract_forbidden_claims"])

    def test_product_verification_report_routes_blocking_issues(self) -> None:
        report = ProductVerificationReport(
            ok=False,
            score=2.4,
            issues=[
                {
                    "issue_id": "issue-1",
                    "category": "ui_usability",
                    "severity": "high",
                    "blocking": True,
                    "message": "Missing required result card.",
                    "suggested_route": "revise_prototype",
                }
            ],
            revision_route="revise_prototype",
        )

        self.assertFalse(report.ok)
        self.assertEqual(report.issues[0].suggested_route, "revise_prototype")


if __name__ == "__main__":
    unittest.main()
