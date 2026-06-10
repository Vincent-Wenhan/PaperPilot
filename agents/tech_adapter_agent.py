"""Research repository adapter planning agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from tools.llm_client import LLMClient


class TechAdapterAgent(BaseAgent):
    """Plan a reviewed ModelAdapter integration with a mock fallback."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Tech Adapter Agent",
            prompt_path="tech_adapter_prompt.txt",
            llm_client=llm_client,
        )
