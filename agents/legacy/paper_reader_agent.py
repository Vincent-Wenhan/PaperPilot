"""Agent for extracting reproduction details from paper text."""

from __future__ import annotations

from typing import Any

from agents.legacy.schema_display import paper_summary_to_markdown
from schemas.paper_schema import PaperSummary
from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class PaperReaderAgent(BaseAgent):
    """Summarize paper text with a reproduction-oriented prompt."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Paper Reader Agent",
            prompt_path="paper_reader_prompt.txt",
            llm_client=llm_client,
        )

    def run(self, input_data: dict[str, Any] | str) -> str:
        raw = super().run(input_data)
        model, error = self.repair_json_output(raw, PaperSummary)
        if model is not None:
            return paper_summary_to_markdown(model)
        # Retry once with a repair instruction
        repair_suffix = (
            f"\n\nYour previous output could not be parsed as JSON ({error}). "
            "Output ONLY valid JSON matching the required schema."
        )
        raw2 = self.llm_client.generate(
            self.system_prompt + repair_suffix,
            self._format_input(input_data),
        )
        model2, _ = self.repair_json_output(raw2, PaperSummary)
        if model2 is not None:
            return paper_summary_to_markdown(model2)
        return raw
