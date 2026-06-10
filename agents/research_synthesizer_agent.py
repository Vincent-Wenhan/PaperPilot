"""High-level multi-paper research synthesis agent."""

from __future__ import annotations

from typing import Any

from agents.structured_product_agent import StructuredProductAgent
from schemas.composition_schema import (
    MethodCompositionPlan,
    PaperCapabilityCard,
    PaperRelationship,
    ResearchSynthesis,
)
from tools.llm_client import LLMClient


def _short_evidence(value: object, fallback: str) -> str:
    text = str(value or "").strip().replace("\n", " ")
    return text[:240] if text else fallback


class ResearchSynthesizerAgent(StructuredProductAgent[ResearchSynthesis]):
    """Create capability cards and an evidence-backed composition plan."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Research Synthesizer Agent",
            prompt_path="research_synthesizer_prompt.txt",
            schema_type=ResearchSynthesis,
            guideline_names=(
                "multi_paper_composition_rules.md",
                "product_design_principles.md",
                "safety_rules.md",
            ),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> ResearchSynthesis:
        papers = input_data.get("papers") or []
        cards: list[PaperCapabilityCard] = []
        for index, paper in enumerate(papers, 1):
            item = paper if isinstance(paper, dict) else {"paper_info": paper}
            paper_id = str(item.get("paper_id") or f"paper-{index}")
            method = _short_evidence(
                item.get("method_info"),
                "Research capability requires manual verification.",
            )
            cards.append(
                PaperCapabilityCard(
                    paper_id=paper_id,
                    title=str(item.get("title") or f"Paper {index}"),
                    task=_short_evidence(item.get("paper_info"), "Unknown task"),
                    core_capability=method,
                    strengths=["Provides an evidence-backed research capability."],
                    limitations=[
                        "Real model behavior and integration require manual review."
                    ],
                    possible_product_roles=[f"Capability stage {index}"],
                    evidence_from_paper=[method],
                )
            )

        relationships = [
            PaperRelationship(
                source_paper_id=cards[index].paper_id,
                target_paper_id=cards[index + 1].paper_id,
                relationship_type="complementary",
                rationale="The capabilities can be demonstrated as adjacent stages.",
                integration_notes=["Keep an explicit adapter boundary between stages."],
            )
            for index in range(max(0, len(cards) - 1))
        ]
        selected = [card.paper_id for card in cards]
        plan = MethodCompositionPlan(
            strategy="pipeline",
            selected_paper_ids=selected,
            combined_capabilities=[card.core_capability for card in cards],
            workflow_steps=[
                f"Use {card.paper_id}: {card.core_capability}" for card in cards
            ],
            relationships=relationships,
            rationale=(
                "Use a bounded pipeline to make capability roles and integration "
                "assumptions explicit."
            ),
            risks=[
                "Combined behavior is a product hypothesis until real adapters are reviewed."
            ],
        )
        return ResearchSynthesis(
            capability_cards=cards,
            capability_map={
                card.paper_id: card.possible_product_roles for card in cards
            },
            composition_plan=plan,
            summary=f"Synthesized {len(cards)} paper capability card(s).",
        )
