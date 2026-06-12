"""High-level paper and method understanding agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.reproduction_schema import MethodModule, PaperUnderstanding
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
        mock_mode = self.llm_client.mock_mode
        unavailable_reason = (
            "Mock Mode is enabled, so no LLM reviewed the paper."
            if mock_mode
            else "No valid structured LLM analysis was available."
        )
        return PaperUnderstanding(
            title=(
                "Mock analysis - LLM not called"
                if mock_mode
                else "Fallback analysis - valid LLM result unavailable"
            ),
            task=excerpt or "Paper text was unavailable to the mock analysis.",
            problem=f"{unavailable_reason} The research problem remains unverified.",
            contributions=[
                f"{unavailable_reason} Review the recorded pipeline error before retrying."
            ],
            method_summary=(
                f"{unavailable_reason} Extracted opening text: {excerpt}"
                if excerpt
                else f"{unavailable_reason} No paper text was received."
            ),
            method_modules=[
                MethodModule(
                    name="Unavailable",
                    purpose="No valid LLM paper analysis is available.",
                    evidence=[
                        f"{unavailable_reason} PDF extraction status is shown in the task field."
                    ],
                ),
            ],
            end_to_end_dataflow=["Not analyzed."],
            implementation_blueprint=[
                "Obtain a valid evidence-backed paper analysis before implementation."
            ],
            datasets=[],
            metrics=[],
            training_details=[],
            inference_details=[],
            reproduction_clues=["Obtain a valid LLM analysis before planning reproduction."],
            evidence=[f"{unavailable_reason} PDF extraction status is shown in the task field."],
            missing_information=["All semantic paper details remain unverified."],
        )

    def validate_structured_result(
        self,
        result: PaperUnderstanding,
        input_data: dict[str, Any],
    ) -> str | None:
        del input_data
        missing_core = [
            name
            for name, value in (
                ("title", result.title),
                ("task", result.task),
                ("problem", result.problem),
                ("method_summary", result.method_summary),
            )
            if not value.strip()
        ]
        if missing_core:
            return f"missing core paper fields: {', '.join(missing_core)}"
        if not result.contributions:
            return "no paper contributions were extracted"
        if not result.method_modules:
            return "no method modules were extracted"
        incomplete_modules = [
            module.name or "<unnamed>"
            for module in result.method_modules
            if (
                not module.name.strip()
                or not module.purpose.strip()
                or not module.inputs
                or not module.outputs
                or not module.mechanism
                or not any("[Page " in item for item in module.evidence)
            )
        ]
        if incomplete_modules:
            return (
                "method modules lack purpose, data contracts, mechanism, or "
                f"page evidence: {', '.join(incomplete_modules)}"
            )
        if not result.end_to_end_dataflow:
            return "end-to-end method dataflow was not reconstructed"
        if not result.implementation_blueprint:
            return "implementation blueprint is empty"
        if not result.evidence:
            return "no page-specific paper evidence was extracted"
        if not any("[Page " in item for item in result.evidence):
            return "paper evidence does not cite any provided [Page N] marker"
        return None
