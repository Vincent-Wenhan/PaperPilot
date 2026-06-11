"""Generated product frontend planning agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.legacy.product_mock_outputs import FRONTEND_BUILDER_MOCK
from tools.llm_client import LLMClient


class FrontendBuilderAgent(BaseAgent):
    """Describe a simple Streamlit interaction for the chosen template."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Frontend Builder Agent",
            prompt_path="frontend_builder_prompt.txt",
            llm_client=llm_client,
        )

    def run(self, input_data: dict[str, object] | str) -> str:
        """Return a template-oriented mock frontend plan or call the LLM."""
        if self.llm_client.mock_mode:
            try:
                self._format_input(input_data)
            except Exception as exc:
                return f"{self.name} failed: {exc}"
            return FRONTEND_BUILDER_MOCK
        return super().run(input_data)
