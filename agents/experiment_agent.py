"""Agent for planning progressive paper reproduction experiments."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class ExperimentPlannerAgent(BaseAgent):
    """Generate a resource-aware, level-based reproduction plan."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Experiment Planner Agent",
            prompt_path="experiment_prompt.txt",
            llm_client=llm_client,
        )


ExperimentAgent = ExperimentPlannerAgent
