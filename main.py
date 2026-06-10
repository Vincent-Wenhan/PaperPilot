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

# Goal → (agents to run, human-readable names)
GOAL_PIPELINE_STEPS: dict[str, list[dict[str, Any]]] = {
    "只理解论文": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "跑通官方 demo": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repo Clone Agent", "is_deterministic": True, "deterministic_type": "clone"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "最小训练实验": [
        {"agent_factory": PaperReaderAgent, "step_name": "Paper Reader Agent"},
        {"agent_factory": MethodExtractorAgent, "step_name": "Method Extractor Agent"},
        {"agent_factory": None, "step_name": "Repo Clone Agent", "is_deterministic": True, "deterministic_type": "clone"},
        {"agent_factory": RepoAnalyzerAgent, "step_name": "Repo Analyzer Agent"},
        {"agent_factory": EnvAgent, "step_name": "Environment Agent"},
        {"agent_factory": ExperimentAgent, "step_name": "Experiment Planner Agent"},
        {"agent_factory": ReportAgent, "step_name": "Report Agent"},
    ],
    "复现主实验": [
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
    result["errors"].append(f"{step}：{error}")


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
        _record_error(result, step, "Agent 返回了空结果。")
        return ""
    failure_markers = ("执行失败：", "LLM 调用失败：")
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
        _record_error(result, step, f"Agent 初始化失败：{exc}")
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
        return f"{step_name} 未生成：Agent 初始化失败。"
    return _run_agent(result, step_name, agent, input_data)


def _build_reproduction_plan(result: PipelineResult) -> str:
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- 暂未发现"
    return f"""# Reproduction Plan

## 1. Paper Summary
{result["paper_info"] or "未生成。"}

## 2. Method Breakdown
{result["method_info"] or "未生成。"}

## 3. Repository Analysis
{result["repo_info"] or "未生成。"}

## 4. Environment Setup
{result["env_plan"] or "未生成。"}

## 5. Minimal Reproduction Plan
{result["experiment_plan"] or "未生成。"}

## 6. Commands
- `python --version`
- `pip --version`
- 对识别出的入口文件先运行 `python <entrypoint> --help`
- demo 本体需要用户二次确认后再运行

## 7. Checklist
- [ ] 确认 Python 与依赖环境
- [ ] 阅读论文与仓库分析结果
- [ ] 运行入口文件的 `--help`
- [ ] 准备最小数据与配置
- [ ] 用户确认后再运行 demo 或训练

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
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- 暂无"
    return f"""# PaperPilot Reproduction Report

## Paper Information
{result["paper_info"] or "未生成。"}

## Method Overview
{result["method_info"] or "未生成。"}

## Code Repository
- Local path: {result["repo_path"] or "未生成"}

{result["repo_info"] or "未生成。"}

## Environment
{result["env_plan"] or "未生成。"}

## Data Preparation
请依据论文、仓库 README 和实验计划手动准备数据；系统不会默认下载大型数据集。

## Commands
默认仅执行版本检查。入口 `--help`、demo 和训练命令需要用户审阅。

## Debug Notes
{errors}

## Difference from Original Paper
当前结果是复现规划，不代表已经达到原论文的完整实验设置或指标。

## Next Steps
{result["experiment_plan"] or "请先解决上述错误并重新运行。"}

## Generated Report Draft
{generated_report or "Report Agent 未生成额外内容。"}
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
    msg = "PDF 未提取到文本，文件可能是扫描版，请提供 OCR 版本。"
    _record_error(result, step, msg)
    return ""


def _do_clone(result: PipelineResult, github_url: str) -> str:
    if not is_valid_github_url(github_url):
        _record_error(
            result,
            "GitHub URL 校验失败",
            "仅支持 https://github.com/owner/repo 格式。",
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
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the PaperPilot analysis pipeline while preserving partial results.

    The ``goal`` parameter controls which agents are executed.  When a
    ``progress_callback`` is provided it is called with the Chinese name of
    each agent step before that step begins.
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
            "「Debug 报错」目标下不运行主流程。请在 Debug 区粘贴日志进行分析。"
        )
        return result

    steps = GOAL_PIPELINE_STEPS.get(goal, GOAL_PIPELINE_STEPS["最小训练实验"])
    llm_client = LLMClient()

    # ------------------------------------------------------------------
    # PDF parsing (always needed if a paper was uploaded)
    # ------------------------------------------------------------------
    paper_text = ""
    try:
        if pdf_path and pdf_path.strip():
            paper_text = parse_pdf(pdf_path)
    except Exception as exc:
        _record_error(result, "PDF 解析失败", exc)

    paper_text_available = bool(paper_text.strip())

    # ------------------------------------------------------------------
    # Clone + scan — run early if the goal needs them so the results are
    # available for downstream LLM agents.
    # ------------------------------------------------------------------
    repo_scan: dict[str, Any] | None = None
    needs_repo = any(
        step.get("is_deterministic") for step in steps
    )

    if needs_repo:
        if progress_callback:
            progress_callback("Repo Clone Agent 正在 clone 仓库")
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
            continue  # already handled above

        factory = step["agent_factory"]
        step_name = step["step_name"]

        if progress_callback:
            progress_callback(f"{step_name} 正在分析")

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
            if not result["paper_info"] or "扫描版" in result["paper_info"]:
                result["method_info"] = "方法拆解未生成：论文信息不可用。"
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
                result["repo_info"] = "仓库分析未生成：仓库 clone 或扫描失败。"
                continue
            result["repo_info"] = _run_llm_agent_step(
                result, factory, llm_client, step_name, repo_scan,
            )

        # --- Environment ---
        elif factory is EnvAgent:
            hardware_context = {
                "hardware": hardware or "未提供",
                "gpu_info": gpu_info or "未提供",
                "goal": goal or "未提供",
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
                "hardware": hardware or "未提供",
                "gpu_info": gpu_info or "未提供",
                "goal": goal or "未提供",
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
                "hardware": hardware or "未提供",
                "gpu_info": gpu_info or "未提供",
                "goal": goal or "未提供",
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
                "保存 reproduction_plan.md 失败",
                save_markdown,
                reproduction_plan,
                OUTPUTS_DIR / "reproduction_plan.md",
            )
            _save_output(
                result,
                "保存 run.sh 失败",
                save_shell_script,
                result["run_sh"],
                OUTPUTS_DIR / "run.sh",
            )
            _save_output(
                result,
                "保存 report.md 失败",
                save_markdown,
                result["report"],
                OUTPUTS_DIR / "report.md",
            )

    return result
