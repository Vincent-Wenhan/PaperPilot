"""MVP product design agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.product_mock_outputs import PRODUCT_DESIGNER_MOCK
from tools.llm_client import LLMClient


class ProductDesignerAgent(BaseAgent):
    """Turn a recommended opportunity into a bounded product specification."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Designer Agent",
            prompt_path="product_designer_prompt.txt",
            llm_client=llm_client,
        )

    def run(self, input_data: dict[str, object] | str) -> str:
        """Return a bounded mock specification or call the LLM."""
        if self.llm_client.mock_mode:
            try:
                self._format_input(input_data)
            except Exception as exc:
                return f"{self.name} failed: {exc}"
            return PRODUCT_DESIGNER_MOCK
        return super().run(input_data)
