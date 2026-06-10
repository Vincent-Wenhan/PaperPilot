"""Generated product test-report agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from tools.llm_client import LLMClient


class ProductTestAgent(BaseAgent):
    """Explain deterministic product inspection results and limitations."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Test Agent",
            prompt_path="product_test_prompt.txt",
            llm_client=llm_client,
        )
