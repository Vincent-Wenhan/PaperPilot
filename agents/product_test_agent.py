"""Generated product test-report agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.product_mock_outputs import PRODUCT_TEST_MOCK
from tools.llm_client import LLMClient


class ProductTestAgent(BaseAgent):
    """Explain deterministic product inspection results and limitations."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Test Agent",
            prompt_path="product_test_prompt.txt",
            llm_client=llm_client,
        )

    def run(self, input_data: dict[str, object] | str) -> str:
        """Return a structured mock test report or call the LLM."""
        if self.llm_client.mock_mode:
            try:
                self._format_input(input_data)
            except Exception as exc:
                return f"{self.name} failed: {exc}"
            return PRODUCT_TEST_MOCK
        return super().run(input_data)
