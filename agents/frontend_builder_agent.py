"""Generated product frontend planning agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from tools.llm_client import LLMClient


class FrontendBuilderAgent(BaseAgent):
    """Describe a simple Streamlit interaction for the chosen template."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Frontend Builder Agent",
            prompt_path="frontend_builder_prompt.txt",
            llm_client=llm_client,
        )
