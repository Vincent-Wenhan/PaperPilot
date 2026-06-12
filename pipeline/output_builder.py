"""Build reproduction output artifacts (plan, run script, report)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tools.markdown_writer import save_markdown, save_shell_script


def build_reproduction_plan(result: dict[str, Any]) -> str:
    """Assemble the reproduction plan markdown from pipeline results."""
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- None found."
    smoke_command = (
        result.get("implementation_bundle", {}).get("smoke_test_command")
        or "Not generated."
    )
    download_command = (
        result.get("implementation_bundle", {}).get("data_download_command")
        or "Not generated because no evidence-backed link was found."
    )
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
- Generated data download command: `{download_command}`
- Generated implementation smoke test: `{smoke_command}`
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


def build_run_script(
    repo_scan: dict[str, Any] | None,
    implementation_bundle: dict[str, Any] | None = None,
) -> str:
    """Build a safe run script with TODO placeholders."""
    entrypoints = (repo_scan or {}).get("possible_entrypoints", [])
    help_todos = "\n".join(
        f"# TODO: cd <repository> && python {entrypoint} --help"
        for entrypoint in entrypoints[:5]
    )
    if not help_todos:
        help_todos = "# TODO: locate an entrypoint and run it with --help"
    smoke_command = str(
        (implementation_bundle or {}).get("smoke_test_command") or ""
    ).strip()
    download_command = str(
        (implementation_bundle or {}).get("data_download_command") or ""
    ).strip()
    smoke_todo = (
        f"# TODO: cd <generated-reproduction-directory> && {smoke_command}"
        if smoke_command
        else "# TODO: no generated implementation smoke test is available"
    )
    download_todo = (
        f"# TODO: review URLs, then cd <generated-reproduction-directory> && {download_command}"
        if download_command
        else "# No evidence-backed resource URL was found; no download script generated"
    )

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

# TODO: review and run the generated implementation smoke test
{smoke_todo}

# TODO: review and explicitly run the generated data download script
{download_todo}

# TODO: training commands require explicit user review and confirmation
"""


def build_report(result: dict[str, Any], diagnosis: str = "") -> str:
    """Assemble the final reproduction report."""
    errors = "\n".join(f"- {error}" for error in result["errors"]) or "- None"
    download_command = (
        result.get("implementation_bundle", {}).get("data_download_command")
        or "No evidence-backed dataset or checkpoint link was found."
    )
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
PaperPilot only generates a downloader for exact HTTPS links found near dataset or
checkpoint evidence in the paper or repository documentation. The generated downloader is
dry-run by default and requires manual review plus `--execute`.

- Reviewed download command: `{download_command}`

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
