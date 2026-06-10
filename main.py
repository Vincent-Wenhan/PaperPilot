"""Main orchestration pipeline for PaperPilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from agents import (
    CodeAgent,
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
        {"agent_factory": None, "step_name": "Repository Source", "is_deterministic": True, "deterministic_type": "repository"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "minimal training experiment": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repository Source", "is_deterministic": True, "deterministic_type": "repository"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ExperimentAgent, "step_name": "Experiment Planner Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "reproduce main experiments": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repository Source", "is_deterministic": True, "deterministic_type": "repository"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ExperimentAgent, "step_name": "Experiment Planner Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
}

_DEBUG_GOAL = MAIN_GOAL_DEBUG
MAX_CODE_AGENT_PAPER_CHARS = 60_000


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

## 3. Code Source
- Source: {result["repo_source"] or "Not generated."}
- Local path: {result["repo_path"] or "Not generated."}

{result["code_info"] or "No Code Agent output."}

## 4. Repository Analysis
{result["repo_info"] or "Not generated."}

## 5. Environment Setup
{result["env_plan"] or "Not generated."}

## 6. Minimal Reproduction Plan
{result["experiment_plan"] or "Not generated."}

## 7. Commands
- `python --version`
- `pip --version`
- Run `python <entrypoint> --help` on detected entry points
- Demo execution requires explicit user confirmation

## 8. Checklist
- [ ] Verify Python and dependency environment
- [ ] Review generated code assumptions or repository analysis
- [ ] Run `--help` on entry points
- [ ] Prepare minimal data and configuration
- [ ] Confirm before running demo or training

## 9. Risks
{errors}
"""


def _build_run_script(repo_scan: dict[str, Any] | None) -> str:
    entrypoints = (repo_scan or {}).get("possible_entrypoints", [])
    help_todos = "\n".join(
        f"# TODO: cd <repository> && python {entrypoint} --help"
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
- Source: {result["repo_source"] or "Not generated"}
- Local path: {result["repo_path"] or "Not generated"}

{result["code_info"] or "No code-generation notes."}

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
The current output is a reproduction plan. Model-generated code is an independent approximation, not the official implementation, and does not demonstrate alignment with the paper's reported metrics.

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


def _do_generate_code(
    result: PipelineResult,
    llm_client: LLMClient,
    context: dict[str, Any],
) -> str:
    try:
        generated = CodeAgent(llm_client).generate_repository(context)
        result["repo_path"] = str(generated["repo_path"])
        result["repo_source"] = "Generated by Code Agent"
        generated_files = "\n".join(
            f"- `{path}`" for path in generated.get("files", [])
        )
        result["code_info"] = (
            f"{generated.get('summary', 'Code Agent generated a reproduction project.')}"
            f"\n\nGenerated files:\n{generated_files}"
        )
        return result["repo_path"]
    except Exception as exc:
        _record_error(result, "Code Agent", exc)
        return ""


def _prepare_repository(
    result: PipelineResult,
    github_url: str,
    llm_client: LLMClient,
    code_context: dict[str, Any],
    progress_callback: Callable[[str], None] | None,
) -> dict[str, Any] | None:
    if github_url.strip():
        if progress_callback:
            progress_callback("Repo Clone Agent cloning repository")
        repo_path = _do_clone(result, github_url.strip())
        if repo_path:
            result["repo_source"] = "GitHub repository"
    else:
        if progress_callback:
            progress_callback("Code Agent generating reproduction code")
        repo_path = _do_generate_code(result, llm_client, code_context)

    if not repo_path:
        return None
    try:
        repo_scan = scan_repo(repo_path)
    except Exception as exc:
        _record_error(result, "Repo Scanner", exc)
        return None
    repo_scan["repository_source"] = result["repo_source"]
    if result["code_info"]:
        repo_scan["code_generation"] = result["code_info"]
    return repo_scan


def run_paperpilot(
    pdf_path: str,
    github_url: str = "",
    hardware: str = "Not provided",
    gpu_info: str = "",
    goal: str = "minimal training experiment",
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the PaperPilot analysis pipeline while preserving partial results.

    The ``github_url`` parameter is optional. If omitted, Code Agent generates
    a minimal reproduction repository from the paper analysis.

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
        "repo_source": "",
        "code_info": "",
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
    # Repository acquisition runs after paper and method analysis.
    # ------------------------------------------------------------------
    repo_scan: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Agent steps
    # ------------------------------------------------------------------
    for step in steps:
        if step.get("is_deterministic"):
            if step.get("deterministic_type") == "repository":
                code_context = {
                    "paper_info": result["paper_info"],
                    "method_info": result["method_info"],
                    "paper_text_excerpt": paper_text[:MAX_CODE_AGENT_PAPER_CHARS],
                    "hardware": hardware or "Not provided",
                    "gpu_info": gpu_info or "Not provided",
                    "goal": goal or "Not provided",
                }
                repo_scan = _prepare_repository(
                    result,
                    github_url,
                    llm_client,
                    code_context,
                    progress_callback,
                )
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
                result["repo_info"] = "Repository analysis skipped: code acquisition or scan failed."
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
                "repository_source": result["repo_source"],
                "code_generation": result["code_info"],
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
                "repo_source": result["repo_source"],
                "code_info": result["code_info"],
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
                "repo_source": result["repo_source"],
                "code_info": result["code_info"],
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
