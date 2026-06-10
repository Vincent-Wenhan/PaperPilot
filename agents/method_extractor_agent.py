"""Agent for translating paper methods into engineering modules."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class MethodExtractorAgent(BaseAgent):
    """Produce an implementation-oriented method breakdown."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Method Extractor Agent",
            prompt_path="method_extractor_prompt.txt",
            llm_client=llm_client,
        )
