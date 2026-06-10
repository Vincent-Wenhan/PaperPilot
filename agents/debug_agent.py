"""Agent for diagnosing reproduction command failures."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class DebugAgent(BaseAgent):
    """Analyze command, output, errors, and environment information."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Debug Agent",
            prompt_path="debug_prompt.txt",
            llm_client=llm_client,
        )
