"""Main orchestration pipeline for PaperPilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from agents import (
    EnvAgent,
    ExperimentAgent,
    MethodExtractorAgent,
    PaperReaderAgent,
    RepoAnalyzerAgent,
    RepoCloneAgent,
    ReportAgent,
)
from config import MAIN_GOAL_DEBUG, OUTPUTS_DIR
from tools.github_tool import is_valid_github_url
from tools.llm_client import LLMClient
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import parse_pdf
from tools.repo_scanner import scan_repo

PipelineResult = dict[str, Any]

# Goal mapping controls which agents are executed per goal.
GOAL_PIPELINE_STEPS: dict[str, list[dict[str, Any]]] = {
    "understand paper": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "run official demo": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repo Clone Agent", "is_deterministic": True, "deterministic_type": "clone"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "minimal training experiment": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repo Clone Agent", "is_deterministic": True, "deterministic_type": "clone"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ExperimentAgent, "step_name": "Experiment Planner Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "reproduce main experiments": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repo Clone Agent", "is_deterministic": True, "deterministic_type": "clone"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ExperimentAgent, "step_name": "Experiment Planner Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
}

_DEBUG_GOAL = MAIN_GOAL_DEBUG


def _record_error(result: PipelineResult, step: str, error: object) -> None:
    result["errors"].append(f"[{step}] {error}")


def _run_agent(
    result: PipelineResult,
    step: str,
    agent: Any,
    input_data: dict[str, Any] | str,
) -> str:
    try:
        output = agent.run(input_data)
    except Exception as exc:
        _record_error(result, step, exc)
        return ""
    if not isinstance(output, str) or not output.strip():
        _record_error(result, step, "Agent returned an empty result.")
        return ""
    failure_markers = ("failed:", "LLM call failed:")
    if any(marker in output for marker in failure_markers):
        _record_error(result, step, output)
    return output


def _create_agent(
    result: PipelineResult,
    step: str,
    factory: Callable[[LLMClient], Any],
    llm_client: LLMClient,
) -> Any | None:
    try:
        return factory(llm_client)
    except Exception as exc:
        _record_error(result, step, f"Agent initialization failed: {exc}")
        return None


def _run_llm_agent_step(
    result: PipelineResult,
    factory: Callable[[LLMClient], Any],
    llm_client: LLMClient,
    step_name: str,
    input_data: dict[str, Any] | str,
) -> str:
    agent = _create_agent(result, step_name, factory, llm_client)
    if agent is None:
        return f"{step_name}: Agent initialization failed."
    return _run_agent(result, step_name, agent, input_data)


def _build_reproduction_plan(result: PipelineResult) -> str:
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- None found."
    return f"""# Reproduction Plan

## 1. Paper Summary
{result["paper_info"] or "Not generated."}

## 2. Method Breakdown
{result["method_info"] or "Not generated."}

## 3. Repository Analysis
{result["repo_info"] or "Not generated."}

## 4. Environment Setup
{result["env_plan"] or "Not generated."}

## 5. Minimal Reproduction Plan
{result["experiment_plan"] or "Not generated."}

## 6. Commands
- `python --version`
- `pip --version`
- Run `python <entrypoint> --help` on detected entry points
- Demo execution requires explicit user confirmation

## 7. Checklist
- [ ] Verify Python and dependency environment
- [ ] Read paper and repository analysis
- [ ] Run `--help` on entry points
- [ ] Prepare minimal data and configuration
- [ ] Confirm before running demo or training

## 8. Risks
{errors}
"""


def _build_run_script(repo_scan: dict[str, Any] | None) -> str:
    entrypoints = (repo_scan or {}).get("possible_entrypoints", [])
    help_todos = "\n".join(
        f"# TODO: cd <cloned-repo> && python {entrypoint} --help"
        for entrypoint in entrypoints[:5]
    )
    if not help_todos:
        help_todos = "# TODO: locate an entrypoint and run it with --help"

    return f"""#!/usr/bin/env bash
set -e

# TODO: activate environment
# conda activate paperpilot

# TODO: install dependencies after reviewing the repository files
# python -m pip install -r requirements.txt

python --version
pip --version

# TODO: run minimal demo or help command
{help_todos}

# TODO: training commands require explicit user review and confirmation
"""


def _build_report(result: PipelineResult, generated_report: str) -> str:
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- None"
    return f"""# PaperPilot Reproduction Report

## Paper Information
{result["paper_info"] or "Not generated."}

## Method Overview
{result["method_info"] or "Not generated."}

## Code Repository
- Local path: {result["repo_path"] or "Not generated"}

{result["repo_info"] or "Not generated."}

## Environment
{result["env_plan"] or "Not generated."}

## Data Preparation
Prepare data manually based on the paper, repository README, and experiment plan. The system will not download large datasets by default.

## Commands
By default only version checks are executed. Entry point `--help`, demo, and training commands require user review.

## Debug Notes
{errors}

## Difference from Original Paper
The current output is a reproduction plan and does not represent full alignment with the original paper's experimental setup or metrics.

## Next Steps
{result["experiment_plan"] or "Please resolve the errors above and re-run."}

## Generated Report Draft
{generated_report or "Report Agent did not generate additional content."}
"""


def _save_output(
    result: PipelineResult,
    step: str,
    writer: Callable[[str, str | Path], None],
    content: str,
    path: Path,
) -> None:
    try:
        writer(content, path)
    except Exception as exc:
        _record_error(result, step, exc)


def _reject_scanned_pdf(result: PipelineResult, step: str) -> str:
    msg = "No text could be extracted from the PDF. It may be a scanned document. Please provide an OCR version."
    _record_error(result, step, msg)
    return ""


def _do_clone(result: PipelineResult, github_url: str) -> str:
    if not is_valid_github_url(github_url):
        _record_error(
            result,
            "GitHub URL validation failed",
            "Only https://github.com/owner/repo format is supported.",
        )
        return ""
    try:
        repo_clone_agent = RepoCloneAgent()
        repo_path = repo_clone_agent.clone(github_url)
        result["repo_path"] = str(repo_path)
        return str(repo_path)
    except Exception as exc:
        _record_error(result, "Repo Clone Agent", exc)
        return ""


def run_paperpilot(
    pdf_path: str,
    github_url: str,
    hardware: str,
    gpu_info: str,
    goal: str,
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the PaperPilot analysis pipeline while preserving partial results.

    The ``goal`` parameter controls which agents are executed.  When a
    ``progress_callback`` is provided it is called with the name of
    each agent step before that step begins.

    If ``llm_client`` is not provided a default one is created from
    environment variables.
    """
    result: PipelineResult = {
        "paper_info": "",
        "method_info": "",
        "repo_path": "",
        "repo_info": "",
        "env_plan": "",
        "experiment_plan": "",
        "report": "",
        "run_sh": "",
        "errors": [],
    }

    if goal == _DEBUG_GOAL:
        result["errors"].append(
            "Pipeline skipped under debug goal. Please paste logs in the Debug section for analysis."
        )
        return result

    steps = GOAL_PIPELINE_STEPS.get(goal, GOAL_PIPELINE_STEPS["minimal training experiment"])
    if llm_client is None:
        llm_client = LLMClient()

    # ------------------------------------------------------------------
    # PDF parsing
    # ------------------------------------------------------------------
    paper_text = ""
    try:
        if pdf_path and pdf_path.strip():
            paper_text = parse_pdf(pdf_path)
    except Exception as exc:
        _record_error(result, "PDF parsing failed", exc)

    paper_text_available = bool(paper_text.strip())

    # ------------------------------------------------------------------
    # Clone + scan — run early if the goal needs them
    # ------------------------------------------------------------------
    repo_scan: dict[str, Any] | None = None
    needs_repo = any(
        step.get("is_deterministic") for step in steps
    )

    if needs_repo:
        if progress_callback:
            progress_callback("Repo Clone Agent cloning repository")
        repo_path = _do_clone(result, github_url)
        if result["repo_path"]:
            try:
                repo_scan = scan_repo(result["repo_path"])
            except Exception as exc:
                _record_error(result, "Repo Scanner", exc)

    # ------------------------------------------------------------------
    # Agent steps
    # ------------------------------------------------------------------
    for step in steps:
        if step.get("is_deterministic"):
            continue

        factory = step["agent_factory"]
        step_name = step["step_name"]

        if progress_callback:
            progress_callback(f"{step_name} analyzing")

        # --- Paper Reader ---
        if factory is PaperReaderAgent:
            if not paper_text_available:
                result["paper_info"] = _reject_scanned_pdf(result, step_name)
                continue
            result["paper_info"] = _run_llm_agent_step(
                result, factory, llm_client, step_name, paper_text,
            )

        # --- Method Extractor ---
        elif factory is MethodExtractorAgent:
            if not result["paper_info"] or "scanned" in result["paper_info"].lower():
                result["method_info"] = "Method extraction skipped: paper information is unavailable."
                continue
            method_input = {
                "paper_info": result["paper_info"],
                "paper_text_available": paper_text_available,
            }
            result["method_info"] = _run_llm_agent_step(
                result, factory, llm_client, step_name, method_input,
            )

        # --- Repo Analyzer ---
        elif factory is RepoAnalyzerAgent:
            if not repo_scan:
                result["repo_info"] = "Repository analysis skipped: clone or scan failed."
                continue
            result["repo_info"] = _run_llm_agent_step(
                result, factory, llm_client, step_name, repo_scan,
            )

        # --- Environment ---
        elif factory is EnvAgent:
            hardware_context = {
                "hardware": hardware or "Not provided",
                "gpu_info": gpu_info or "Not provided",
                "goal": goal or "Not provided",
                "repository_scan": repo_scan or {},
                "repository_analysis": result["repo_info"],
            }
            result["env_plan"] = _run_llm_agent_step(
                result, factory, llm_client, step_name, hardware_context,
            )

        # --- Experiment Planner ---
        elif factory is ExperimentAgent:
            experiment_context = {
                "paper_info": result["paper_info"],
                "method_info": result["method_info"],
                "repo_info": result["repo_info"],
                "env_plan": result["env_plan"],
                "hardware": hardware or "Not provided",
                "gpu_info": gpu_info or "Not provided",
                "goal": goal or "Not provided",
            }
            result["experiment_plan"] = _run_llm_agent_step(
                result, factory, llm_client, step_name, experiment_context,
            )

        # --- Report ---
        elif factory is ReportAgent:
            report_context = {
                "paper_info": result["paper_info"],
                "method_info": result["method_info"],
                "repo_info": result["repo_info"],
                "env_plan": result["env_plan"],
                "experiment_plan": result["experiment_plan"],
                "hardware": hardware or "Not provided",
                "gpu_info": gpu_info or "Not provided",
                "goal": goal or "Not provided",
                "repo_path": result["repo_path"],
                "errors": result["errors"],
            }
            report_draft = _run_llm_agent_step(
                result, factory, llm_client, step_name, report_context,
            )

            # Build final outputs
            reproduction_plan = _build_reproduction_plan(result)
            result["run_sh"] = _build_run_script(repo_scan)
            result["report"] = _build_report(result, report_draft)

            _save_output(
                result,
                "Failed to save reproduction_plan.md",
                save_markdown,
                reproduction_plan,
                OUTPUTS_DIR / "reproduction_plan.md",
            )
            _save_output(
                result,
                "Failed to save run.sh",
                save_shell_script,
                result["run_sh"],
                OUTPUTS_DIR / "run.sh",
            )
            _save_output(
                result,
                "Failed to save report.md",
                save_markdown,
                result["report"],
                OUTPUTS_DIR / "report.md",
            )

    return result
