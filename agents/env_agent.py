"""Agent for producing reproducible environment setup guidance."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class EnvironmentAgent(BaseAgent):
    """Create environment advice from repository evidence and hardware."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Environment Agent",
            prompt_path="env_prompt.txt",
            llm_client=llm_client,
        )


EnvAgent = EnvironmentAgent
