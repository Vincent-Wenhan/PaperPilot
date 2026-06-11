"""Main orchestration entry point for PaperPilot.

Delegates to pipeline modules for specific workflows.
"""

from __future__ import annotations

from typing import Any, Callable

from config import MAIN_GOAL_DEBUG
from pipeline.reproduce_pipeline import run_reproduce_pipeline
from tools.llm_client import LLMClient


PipelineResult = dict[str, Any]


def run_paperpilot(
    pdf_path: str,
    github_url: str = "",
    hardware: str = "Not provided",
    gpu_info: str = "",
    goal: str = "minimal training experiment",
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
    user_idea: str = "",
) -> dict[str, Any]:
    """Run the PaperPilot analysis pipeline.

    Dispatches to the reproduce pipeline based on goal.
    """
    if goal == MAIN_GOAL_DEBUG:
        result: PipelineResult = {
            "research_understanding": {},
            "repository_understanding": {},
            "reproduction_plan": {},
            "execution_diagnosis": {},
            "paper_info": "",
            "method_info": "",
            "repo_path": "",
            "repo_source": "",
            "code_info": "",
            "repo_info": "",
            "env_plan": "",
            "experiment_plan": "",
            "report": "",
            "run_sh": "",
            "errors": [
                "Pipeline skipped under debug goal. Please paste logs in the Debug section for analysis."
            ],
        }
        return result

    if llm_client is None:
        llm_client = LLMClient()

    return run_reproduce_pipeline(
        pdf_path=pdf_path,
        github_url=github_url,
        hardware=hardware,
        gpu_info=gpu_info,
        goal=goal,
        llm_client=llm_client,
        progress_callback=progress_callback,
        user_idea=user_idea,
    )
