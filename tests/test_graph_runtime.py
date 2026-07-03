from __future__ import annotations

import unittest
from typing import get_type_hints

from pydantic import ValidationError

from runtime.checkpointing import build_checkpointer, build_graph_config
from runtime.collaboration import ReviewIssue
from runtime.graph_state import ProductizeState, ReproduceState
from runtime.routing import (
    route_after_code_review,
    route_after_evaluation,
    route_after_product_evaluation,
    route_after_second_review,
    route_command_plans,
)


class GraphRuntimeTests(unittest.TestCase):
    def test_graph_states_expose_reducer_channels(self) -> None:
        product_hints = get_type_hints(ProductizeState, include_extras=True)
        reproduce_hints = get_type_hints(ReproduceState, include_extras=True)
        self.assertIn("Annotated", str(product_hints["errors"]))
        self.assertIn("Annotated", str(product_hints["tool_logs"]))
        self.assertIn("Annotated", str(product_hints["capability_cards"]))
        self.assertIn("Annotated", str(reproduce_hints["errors"]))
        self.assertIn("Annotated", str(reproduce_hints["command_results"]))

    def test_evaluation_routing(self) -> None:
        self.assertEqual(
            route_after_evaluation(
                {
                    "evaluation": {"overall_score": 4.2},
                    "revision_count": 0,
                    "max_revisions": 1,
                }
            ),
            "finish",
        )
        self.assertEqual(
            route_after_evaluation(
                {
                    "evaluation": {
                        "overall_score": 2.5,
                        "revision_suggestions": [
                            "Improve adapter and prototype UI"
                        ],
                    },
                    "revision_count": 0,
                    "max_revisions": 1,
                }
            ),
            "revise_prototype",
        )
        self.assertEqual(
            route_after_evaluation(
                {
                    "evaluation": {
                        "overall_score": 2.5,
                        "revision_suggestions": [
                            "Reduce PRD scope and improve paper faithfulness"
                        ],
                    },
                    "revision_count": 0,
                    "max_revisions": 1,
                }
            ),
            "revise_product_plan",
        )
        self.assertEqual(
            route_after_evaluation(
                {
                    "evaluation": {"overall_score": 2.5},
                    "revision_count": 1,
                    "max_revisions": 1,
                }
            ),
            "finish_with_warnings",
        )

    def test_blocking_product_verification_routes_by_issue(self) -> None:
        self.assertEqual(
            route_after_product_evaluation(
                {
                    "product_verification": {
                        "ok": False,
                        "score": 2.5,
                        "issues": [
                            {
                                "blocking": True,
                                "suggested_route": "revise_prototype",
                            }
                        ],
                    },
                    "revision_count": 0,
                    "max_revisions": 2,
                }
            ),
            "revise_prototype",
        )
        self.assertEqual(
            route_after_product_evaluation(
                {
                    "product_verification": {
                        "ok": False,
                        "score": 3.0,
                        "issues": [
                            {
                                "blocking": True,
                                "suggested_route": "reduce_mvp_scope",
                            }
                        ],
                    },
                    "revision_count": 2,
                    "max_revisions": 2,
                }
            ),
            "finish_with_warnings",
        )

    def test_command_routing_uses_highest_risk(self) -> None:
        self.assertEqual(route_command_plans([{"risk_level": "low"}]), "safe")
        self.assertEqual(
            route_command_plans(
                [{"risk_level": "low"}, {"risk_level": "medium"}]
            ),
            "review",
        )
        self.assertEqual(
            route_command_plans(
                [{"risk_level": "low"}, {"risk_level": "blocked"}]
            ),
            "blocked",
        )

    def test_reproduce_code_review_routing_allows_bounded_revisions(self) -> None:
        revise_state = {
            "code_review": {"verdict": "revise"},
            "code_revision_count": 0,
            "code_max_revisions": 3,
        }
        self.assertEqual(route_after_code_review(revise_state), "revise")

        second_revise_state = {
            "code_second_review": {"verdict": "revise"},
            "code_revision_count": 1,
            "code_max_revisions": 3,
        }
        self.assertEqual(route_after_second_review(second_revise_state), "revise")

        exhausted_state = {
            "code_second_review": {"verdict": "revise"},
            "code_revision_count": 3,
            "code_max_revisions": 3,
        }
        self.assertEqual(
            route_after_second_review(exhausted_state),
            "finish_with_warnings",
        )

    def test_checkpoint_helpers(self) -> None:
        self.assertIsNone(build_checkpointer(False))
        self.assertIsNotNone(build_checkpointer(True))
        self.assertEqual(
            build_graph_config("thread-1"),
            {"configurable": {"thread_id": "thread-1"}},
        )
        self.assertEqual(build_graph_config(None), {})

    def test_review_issue_validates_severity(self) -> None:
        issue = ReviewIssue(
            source_agent="Product Evaluator Agent",
            target_agent="Prototype Builder Agent",
            severity="important",
            issue_type="prototype",
            message="Adapter boundary is unclear.",
            required_action="Revise the prototype plan.",
        )
        self.assertEqual(issue.severity, "important")
        with self.assertRaises(ValidationError):
            ReviewIssue(
                source_agent="a",
                target_agent="b",
                severity="unknown",
                issue_type="scope",
                message="bad",
                required_action="fix",
            )


if __name__ == "__main__":
    unittest.main()
