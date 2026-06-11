"""High-level paper and method understanding agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.reproduction_schema import PaperUnderstanding
from tools.llm_client import LLMClient


class ResearchUnderstandingAgent(StructuredAgent[PaperUnderstanding]):
    """Merge paper reading and method extraction into one reasoning stage."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Research Understanding Agent",
            prompt_path="research_understanding_prompt.txt",
            schema_type=PaperUnderstanding,
            guideline_names=("reproduction_checklist.md", "safety_rules.md"),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> PaperUnderstanding:
        paper_text = str(input_data.get("paper_text") or "").strip()
        excerpt = " ".join(paper_text.split())[:300]
        return PaperUnderstanding(
            title="Paper Under Analysis",
            task=excerpt or "Task requires paper text review.",
            problem="Determine a feasible and evidence-backed reproduction path.",
            contributions=["Paper claims require verification against the full text."],
            method_summary=excerpt or "Method details are unavailable.",
            method_modules=[
                "Input and preprocessing",
                "Core method",
                "Evaluation and reporting",
            ],
            datasets=[],
            metrics=[],
            training_details=[],
            inference_details=["Confirm the paper's inference procedure."],
            reproduction_clues=["Start with a minimal, inspectable workflow."],
            missing_information=["Exact hyperparameters and assets require verification."],
        )
