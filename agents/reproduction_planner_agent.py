"""High-level environment, experiment, and command planning agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.reproduction_schema import RepositoryUnderstanding, ReproductionPlan
from schemas.runner_schema import CommandPlan
from tools.llm_client import LLMClient


class ReproductionPlannerAgent(StructuredAgent[ReproductionPlan]):
    """Merge environment planning, experiment planning, and command planning."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Reproduction Planner Agent",
            prompt_path="reproduction_planner_prompt.txt",
            schema_type=ReproductionPlan,
            guideline_names=("reproduction_checklist.md", "safety_rules.md"),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> ReproductionPlan:
        repository = RepositoryUnderstanding.model_validate(
            input_data.get("repository_understanding") or {}
        )
        goal = str(input_data.get("goal") or "minimal training experiment")
        hardware = str(input_data.get("hardware") or "Not provided")
        commands = [
            CommandPlan(
                command="python --version",
                purpose="Verify the Python runtime.",
                risk_level="low",
            ),
            CommandPlan(
                command="pip --version",
                purpose="Verify package tooling.",
                risk_level="low",
            ),
        ]
        for entrypoint in repository.minimal_runnable_candidates:
            if entrypoint in {
                "train.py",
                "main.py",
                "eval.py",
                "test.py",
                "demo.py",
                "examples/demo.py",
            }:
                commands.append(
                    CommandPlan(
                        command=f"python {entrypoint} --help",
                        purpose="Inspect a candidate entry point without running its body.",
                        risk_level="low",
                    )
                )
        repository_step = (
            "Review deterministic repository scan evidence."
            if repository.repo_path
            else "Obtain or implement a reviewed repository before real execution."
        )
        return ReproductionPlan(
            goal=goal,
            environment_plan=[
                f"Use an isolated Python environment for {hardware}.",
                "Review dependency files before installing packages.",
                "Confirm CUDA and framework compatibility manually when applicable.",
            ],
            data_preparation_plan=[
                "Identify the smallest representative input.",
                "Do not download large datasets automatically.",
            ],
            minimal_reproduction_steps=[
                "Verify paper assumptions and missing information.",
                repository_step,
                "Run only safe version and --help checks first.",
                "Implement or validate one minimal inference path.",
            ],
            full_reproduction_steps=[
                "Resolve datasets, checkpoints, and exact configurations.",
                "Run a small smoke test before full experiments.",
                "Compare outputs and metrics with the paper.",
            ],
            command_plans=commands,
            risks=repository.risk_signals
            or ["Repository and asset availability require verification."],
            fallback_plan=[
                "Use paper-only analysis if repository evidence is unavailable.",
                "Scale down data and compute before attempting full reproduction.",
            ],
        )
