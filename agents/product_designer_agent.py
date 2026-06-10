"""MVP product design agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from tools.llm_client import LLMClient


class ProductDesignerAgent(BaseAgent):
    """Turn a recommended opportunity into a bounded product specification."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Designer Agent",
            prompt_path="product_designer_prompt.txt",
            llm_client=llm_client,
        )
