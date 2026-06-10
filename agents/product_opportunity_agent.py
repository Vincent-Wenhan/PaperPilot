"""Product opportunity analysis agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from tools.llm_client import LLMClient


class ProductOpportunityAgent(BaseAgent):
    """Identify realistic application opportunities for paper technology."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Opportunity Agent",
            prompt_path="product_opportunity_prompt.txt",
            llm_client=llm_client,
        )
