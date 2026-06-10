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
from config import OUTPUTS_DIR
from tools.github_tool import is_valid_github_url
from tools.llm_client import LLMClient
from tools.markdown_writer import save_markdown, save_shell_script
from tools.pdf_parser import parse_pdf
from tools.repo_scanner import scan_repo


PipelineResult = dict[str, Any]


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


def run_paperpilot(
    pdf_path: str,
    github_url: str,
    hardware: str,
    gpu_info: str,
    goal: str,
) -> dict[str, Any]:
    """Run the PaperPilot analysis pipeline while preserving partial results."""
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
    llm_client = LLMClient()

    paper_text = ""
    try:
        if not pdf_path or not pdf_path.strip():
            raise ValueError("未提供 PDF 文件路径。")
        paper_text = parse_pdf(pdf_path)
    except Exception as exc:
        _record_error(result, "PDF 解析失败", exc)

    paper_agent = _create_agent(
        result,
        "Paper Reader Agent",
        PaperReaderAgent,
        llm_client,
    )
    if paper_text and paper_agent is not None:
        result["paper_info"] = _run_agent(
            result,
            "Paper Reader Agent",
            paper_agent,
            paper_text,
        )
    else:
        result["paper_info"] = "论文信息未生成：PDF 解析失败或未提供。"

    method_agent = _create_agent(
        result,
        "Method Extractor Agent",
        MethodExtractorAgent,
        llm_client,
    )
    method_input = {
        "paper_info": result["paper_info"],
        "paper_text_available": bool(paper_text),
    }
    if method_agent is not None:
        result["method_info"] = _run_agent(
            result,
            "Method Extractor Agent",
            method_agent,
            method_input,
        )
    else:
        result["method_info"] = "方法拆解未生成：Agent 初始化失败。"

    repo_scan: dict[str, Any] | None = None
    try:
        repo_clone_agent = RepoCloneAgent()
    except Exception as exc:
        repo_clone_agent = None
        _record_error(result, "Repo Clone Agent", f"Agent 初始化失败：{exc}")
    if not is_valid_github_url(github_url):
        _record_error(
            result,
            "GitHub URL 校验失败",
            "仅支持 https://github.com/owner/repo 格式。",
        )
    elif repo_clone_agent is not None:
        try:
            repo_path = repo_clone_agent.clone(github_url)
            result["repo_path"] = str(repo_path)
        except Exception as exc:
            _record_error(result, "Repo Clone Agent", exc)

    if result["repo_path"]:
        try:
            repo_scan = scan_repo(result["repo_path"])
        except Exception as exc:
            _record_error(result, "Repo Scanner", exc)

    repo_agent = _create_agent(
        result,
        "Repo Analyzer Agent",
        RepoAnalyzerAgent,
        llm_client,
    )
    if repo_scan and repo_agent is not None:
        result["repo_info"] = _run_agent(
            result,
            "Repo Analyzer Agent",
            repo_agent,
            repo_scan,
        )
    else:
        result["repo_info"] = "仓库分析未生成：仓库 clone 或扫描失败。"

    hardware_context = {
        "hardware": hardware or "未提供",
        "gpu_info": gpu_info or "未提供",
        "goal": goal or "未提供",
        "repository_scan": repo_scan or {},
        "repository_analysis": result["repo_info"],
    }
    env_agent = _create_agent(
        result,
        "Environment Agent",
        EnvAgent,
        llm_client,
    )
    if env_agent is not None:
        result["env_plan"] = _run_agent(
            result,
            "Environment Agent",
            env_agent,
            hardware_context,
        )
    else:
        result["env_plan"] = "环境计划未生成：Agent 初始化失败。"

    experiment_context = {
        "paper_info": result["paper_info"],
        "method_info": result["method_info"],
        "repo_info": result["repo_info"],
        "env_plan": result["env_plan"],
        "hardware": hardware or "未提供",
        "gpu_info": gpu_info or "未提供",
        "goal": goal or "未提供",
    }
    experiment_agent = _create_agent(
        result,
        "Experiment Planner Agent",
        ExperimentAgent,
        llm_client,
    )
    if experiment_agent is not None:
        result["experiment_plan"] = _run_agent(
            result,
            "Experiment Planner Agent",
            experiment_agent,
            experiment_context,
        )
    else:
        result["experiment_plan"] = "实验计划未生成：Agent 初始化失败。"

    report_context = {
        **experiment_context,
        "experiment_plan": result["experiment_plan"],
        "repo_path": result["repo_path"],
        "errors": result["errors"],
    }
    report_agent = _create_agent(
        result,
        "Report Agent",
        ReportAgent,
        llm_client,
    )
    if report_agent is not None:
        report_draft = _run_agent(
            result,
            "Report Agent",
            report_agent,
            report_context,
        )
    else:
        report_draft = "Report Agent 未生成内容：初始化失败。"

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
