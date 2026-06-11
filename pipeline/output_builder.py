"""Build reproduction output artifacts (plan, run script, report)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tools.markdown_writer import save_markdown, save_shell_script


def build_reproduction_plan(result: dict[str, Any]) -> str:
    """Assemble the reproduction plan markdown from pipeline results."""
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- None found."
    return f"""# Reproduction Plan

## 1. Paper Summary
{result["paper_info"] or "Not generated."}

## 2. Method Breakdown
{result["method_info"] or "Not generated."}

## 3. Code Source
- Source: {result["repo_source"] or "Not generated."}
- Local path: {result["repo_path"] or "Not generated."}

{result["code_info"] or "No additional code context."}

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


def build_run_script(repo_scan: dict[str, Any] | None) -> str:
    """Build a safe run script with TODO placeholders."""
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


def build_report(result: dict[str, Any], diagnosis: str = "") -> str:
    """Assemble the final reproduction report."""
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

{diagnosis or "No commands have been executed yet."}

## Difference from Original Paper
The current output is a reproduction plan. It does not demonstrate alignment with the paper's reported metrics.

## Next Steps
{result["experiment_plan"] or "Please resolve the errors above and re-run."}

## Report Builder
This report was assembled deterministically from structured Reproduce artifacts.
"""


def save_output(
    result: dict[str, Any],
    step: str,
    writer: Callable[[str, str | Path], None],
    content: str,
    path: Path,
) -> None:
    """Save an output artifact, recording errors in the result."""
    try:
        writer(content, path)
    except Exception as exc:
        result["errors"].append(f"[{step}] {exc}")
