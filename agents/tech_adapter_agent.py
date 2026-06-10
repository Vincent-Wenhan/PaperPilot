"""Research repository adapter planning agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.product_mock_outputs import TECH_ADAPTER_MOCK
from tools.llm_client import LLMClient


class TechAdapterAgent(BaseAgent):
    """Plan a reviewed ModelAdapter integration with a mock fallback."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Tech Adapter Agent",
            prompt_path="tech_adapter_prompt.txt",
            llm_client=llm_client,
        )

    def run(self, input_data: dict[str, object] | str) -> str:
        """Return a conservative mock adapter plan or call the LLM."""
        if self.llm_client.mock_mode:
            try:
                self._format_input(input_data)
            except Exception as exc:
                return f"{self.name} failed: {exc}"
            return TECH_ADAPTER_MOCK
        return super().run(input_data)
