from __future__ import annotations

import unittest

from graphs.productize_graph import (
    ProductizeExecutionDependencies,
    ProductizeProposalDependencies,
    build_productize_execution_graph,
    build_productize_proposal_graph,
)
from schemas.composition_schema import (
    MethodCompositionPlan,
    PaperCapabilityCard,
    ResearchSynthesis,
)
from schemas.evaluation_schema import ProductEvaluation
from schemas.product_schema import (
    MVPScope,
    PRD,
    ProductContract,
    ProductOpportunity,
    ProductPlan,
    ProductProposal,
    PrototypePlan,
    ValueProposition,
)


def _card(paper_id: str) -> PaperCapabilityCard:
    return PaperCapabilityCard(
        paper_id=paper_id,
        title=paper_id,
        core_capability=f"Capability {paper_id}",
    )


def _plan() -> ProductPlan:
    opportunities = [
        ProductOpportunity(
            idea_name="Demo",
            target_user="Students",
            core_value="Explain research",
            technical_feasibility=5,
            demo_feasibility=5,
            model_availability=4,
            data_requirement=5,
            integration_risk=2,
            user_value=4,
            course_presentation_value=5,
            paper_faithfulness=4,
            multi_paper_coherence=4,
            mock_first_suitability=5,
            overall_score=4.5,
            reason="Bounded demo",
        ),
        ProductOpportunity(
            idea_name="Explorer",
            target_user="Students",
            core_value="Explore research tradeoffs",
            technical_feasibility=4,
            demo_feasibility=5,
            model_availability=4,
            data_requirement=5,
            integration_risk=2,
            user_value=4,
            course_presentation_value=5,
            paper_faithfulness=4,
            multi_paper_coherence=4,
            mock_first_suitability=5,
            overall_score=4.3,
            reason="Different review workflow",
        ),
    ]
    return ProductPlan(
        jtbd="Understand research",
        value_proposition=ValueProposition(),
        opportunities=opportunities,
        selected_product="Demo",
        selection_reason="Bounded demo",
        prd=PRD(
            product_name="Demo",
            problem_statement="Research is hard to inspect.",
            target_users=["Students"],
            core_features=["Evidence"],
        ),
        mvp_scope=MVPScope(must_have=["Mock-first prototype"]),
    )


def _single_opportunity_plan() -> ProductPlan:
    opportunity = ProductOpportunity(
        idea_name="Demo",
        target_user="Students",
        core_value="Explain research",
        technical_feasibility=5,
        demo_feasibility=5,
        model_availability=4,
        data_requirement=5,
        integration_risk=2,
        user_value=4,
        course_presentation_value=5,
        paper_faithfulness=4,
        multi_paper_coherence=4,
        mock_first_suitability=5,
        overall_score=4.5,
        reason="Bounded demo",
    )
    return ProductPlan(
        jtbd="Understand research",
        value_proposition=ValueProposition(),
        opportunities=[opportunity],
        selected_product="Demo",
        selection_reason="Bounded demo",
        prd=PRD(
            product_name="Demo",
            problem_statement="Research is hard to inspect.",
            target_users=["Students"],
            core_features=["Evidence"],
        ),
        mvp_scope=MVPScope(must_have=["Mock-first prototype"]),
    )


def _proposal() -> ProductProposal:
    plan = _plan()
    return ProductProposal(
        product_name=plan.selected_product,
        target_user="Students",
        product_goal="Explain research",
        jtbd=plan.jtbd,
        opportunities=plan.opportunities,
        value_proposition=plan.value_proposition,
        prd=plan.prd,
        mvp_scope=plan.mvp_scope,
    )


class ProductizeProposalGraphTests(unittest.TestCase):
    def test_fanout_preserves_successful_cards_and_trace(self) -> None:
        calls: list[str] = []

        def extract(paper: dict[str, object]) -> PaperCapabilityCard:
            paper_id = str(paper["paper_id"])
            calls.append(paper_id)
            if paper_id == "bad":
                raise RuntimeError("paper unavailable")
            return _card(paper_id)

        def synthesize(
            papers: list[dict[str, object]],
            cards: list[dict[str, object]],
        ) -> ResearchSynthesis:
            del papers
            parsed = [PaperCapabilityCard.model_validate(card) for card in cards]
            return ResearchSynthesis(
                capability_cards=parsed,
                capability_map={card.paper_id: [] for card in parsed},
                composition_plan=MethodCompositionPlan(
                    selected_paper_ids=[card.paper_id for card in parsed]
                ),
            )

        graph = build_productize_proposal_graph(
            ProductizeProposalDependencies(
                extract_capability=extract,
                synthesize_research=synthesize,
                plan_product=lambda synthesis, target_user, product_goal, user_idea: _plan(),
            )
        )
        state = graph.invoke(
            {
                "papers": [
                    {"paper_id": "good", "title": "Good"},
                    {"paper_id": "bad", "title": "Bad"},
                ],
                "target_user": "Students",
                "product_goal": "Demo",
                "user_idea": "",
                "capability_cards": [],
                "errors": [],
                "graph_trace": [],
            }
        )

        self.assertCountEqual(calls, ["good", "bad"])
        self.assertEqual(
            [card["paper_id"] for card in state["capability_cards"]],
            ["good"],
        )
        self.assertTrue(any("paper unavailable" in error for error in state["errors"]))
        self.assertEqual(
            ProductProposal.model_validate(state["proposals"][0]).product_name,
            "Demo",
        )
        self.assertEqual(len(state["proposals"]), 2)
        trace = state["graph_trace"]
        for node in (
            "normalize_inputs",
            "prepare_capability_jobs",
            "extract_capability_card",
            "synthesize_research",
            "plan_product",
            "build_proposals",
        ):
            self.assertIn(node, trace)

    def test_single_opportunity_plan_is_exposed_without_synthetic_alternatives(self) -> None:
        graph = build_productize_proposal_graph(
            ProductizeProposalDependencies(
                extract_capability=lambda paper: _card(str(paper["paper_id"])),
                synthesize_research=lambda papers, cards: ResearchSynthesis(),
                plan_product=lambda synthesis, target_user, product_goal, user_idea: _single_opportunity_plan(),
            )
        )

        state = graph.invoke(
            {
                "papers": [{"paper_id": "paper-1", "title": "Paper"}],
                "target_user": "Students",
                "product_goal": "Demo",
                "user_idea": "",
                "capability_cards": [],
                "errors": [],
                "graph_trace": [],
            }
        )

        proposals = [
            ProductProposal.model_validate(proposal)
            for proposal in state["proposals"]
        ]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].product_name, "Demo")


class ProductizeExecutionGraphTests(unittest.TestCase):
    def _run(
        self,
        evaluations: list[ProductEvaluation],
        *,
        max_revisions: int = 1,
    ) -> tuple[dict[str, object], dict[str, int]]:
        counts = {"scaffold": 0, "inspect": 0}
        queue = list(evaluations)

        def evaluate(
            synthesis: dict[str, object],
            product_plan: dict[str, object],
            prototype_plan: dict[str, object],
            inspection: dict[str, object],
        ) -> ProductEvaluation:
            del synthesis, product_plan, prototype_plan, inspection
            return queue.pop(0)

        def scaffold(state: dict[str, object]) -> dict[str, object]:
            del state
            counts["scaffold"] += 1
            return {"success": True}

        def inspect(state: dict[str, object]) -> dict[str, object]:
            del state
            counts["inspect"] += 1
            return {"syntax_ok": True, "can_run_mock": True}

        graph = build_productize_execution_graph(
            ProductizeExecutionDependencies(
                select_template=lambda state: "text",
                build_prototype=lambda plan, template, feedback: PrototypePlan(
                    template_type=template
                ),
                evaluate_product=evaluate,
                revise_product_plan=lambda plan, evaluation: {
                    **plan,
                    "selection_reason": "Revised product scope",
                },
                revise_prototype=lambda plan, prototype, evaluation: {
                    **prototype,
                    "page_structure": ["Revised UI"],
                },
                scaffold_product=scaffold,
                inspect_product=inspect,
            )
        )
        state = graph.invoke(
            {
                "selected_proposal": _proposal().model_dump(mode="json"),
                "research_synthesis": {},
                "papers": [{"paper_id": "paper-1"}],
                "max_revisions": max_revisions,
                "revision_count": 0,
                "revision_history": [],
                "errors": [],
                "graph_trace": [],
            }
        )
        return state, counts

    def test_high_score_finishes_without_revision(self) -> None:
        score = ProductEvaluation(overall_score=4.5)
        state, counts = self._run([score, score])
        self.assertEqual(state["revision_count"], 0)
        self.assertEqual(counts, {"scaffold": 1, "inspect": 1})

    def test_adapter_feedback_revises_prototype_once(self) -> None:
        low = ProductEvaluation(
            overall_score=3,
            revision_suggestions=["Improve the UI adapter boundary."],
        )
        high = ProductEvaluation(overall_score=4.5)
        state, counts = self._run([low, high, high])
        self.assertEqual(state["revision_count"], 1)
        self.assertEqual(state["revision_history"][0]["route"], "revise_prototype")
        self.assertEqual(counts, {"scaffold": 1, "inspect": 1})

    def test_scope_feedback_revises_plan_and_stops_at_limit(self) -> None:
        low = ProductEvaluation(
            overall_score=3,
            revision_suggestions=["Narrow scope and improve paper faithfulness."],
        )
        state, counts = self._run([low, low, low], max_revisions=1)
        self.assertEqual(state["revision_count"], 1)
        self.assertEqual(
            state["revision_history"][0]["route"],
            "revise_product_plan",
        )
        self.assertIn("finish_with_warnings", state["graph_trace"])
        self.assertEqual(counts, {"scaffold": 1, "inspect": 1})

    def test_execution_graph_carries_product_contract_to_scaffold_and_inspection(self) -> None:
        seen: dict[str, object] = {}
        score = ProductEvaluation(overall_score=4.5)

        def scaffold(state: dict[str, object]) -> dict[str, object]:
            contract = ProductContract.model_validate(state["product_contract"])
            seen["scaffold_contract"] = contract.product_name
            seen["ui_spec_controls"] = [
                item["control_id"]
                for item in state["ui_spec"]["input_controls"]
            ]
            return {"success": True}

        def inspect(state: dict[str, object]) -> dict[str, object]:
            contract = ProductContract.model_validate(state["product_contract"])
            seen["inspect_contract"] = contract.product_name
            return {"syntax_ok": True, "can_run_mock": True, "contract_ok": True}

        graph = build_productize_execution_graph(
            ProductizeExecutionDependencies(
                select_template=lambda state: "text",
                build_prototype=lambda plan, template, feedback: PrototypePlan(
                    template_type=template,
                    user_inputs=["Paper claim"],
                    system_outputs=["Evidence score"],
                    mock_result={"evidence_score": 0.8},
                ),
                evaluate_product=lambda synthesis, product_plan, prototype_plan, inspection: score,
                revise_product_plan=lambda plan, evaluation: plan,
                revise_prototype=lambda plan, prototype, evaluation: prototype,
                scaffold_product=scaffold,
                inspect_product=inspect,
            )
        )

        state = graph.invoke(
            {
                "selected_proposal": _proposal().model_dump(mode="json"),
                "research_synthesis": {},
                "papers": [{"paper_id": "paper-1"}],
                "max_revisions": 1,
                "revision_count": 0,
                "revision_history": [],
                "errors": [],
                "graph_trace": [],
            }
        )

        self.assertEqual(seen["scaffold_contract"], "Demo")
        self.assertEqual(seen["inspect_contract"], "Demo")
        self.assertEqual(seen["ui_spec_controls"], ["paper_claim"])
        self.assertEqual(state["product_contract"]["io"]["output_fields"], ["evidence_score"])
        self.assertEqual(state["product_verification"]["ok"], True)


if __name__ == "__main__":
    unittest.main()
