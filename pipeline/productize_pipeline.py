"""Resilient orchestration for PaperPilot Productize Mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from agents import (
    FrontendBuilderAgent,
    ProductDesignerAgent,
    ProductOpportunityAgent,
    ProductTestAgent,
    TechAdapterAgent,
)
from productize import scaffold_product, select_product_template, inspect_generated_product
from tools.llm_client import LLMClient

ProductResult = dict[str, Any]

_FAILURE_MARKERS = (" failed:", "LLM call failed:")


def _record_error(result: ProductResult, stage: str, error: object) -> None:
    result["errors"].append(f"[{stage}] {error}")


def _run_agent_stage(
    result: ProductResult,
    stage: str,
    agent_factory: Callable[[LLMClient], Any],
    llm_client: LLMClient,
    input_data: dict[str, Any],
) -> str:
    try:
        agent = agent_factory(llm_client)
        output = agent.run(input_data)
    except Exception as exc:
        _record_error(result, stage, exc)
        return ""
    if not isinstance(output, str) or not output.strip():
        _record_error(result, stage, "Agent returned an empty result.")
        return ""
    if any(marker in output for marker in _FAILURE_MARKERS):
        _record_error(result, stage, output)
        return ""
    return output.strip()


def _fallback_product_spec(
    target_user: str,
    product_goal: str,
) -> str:
    return f"""# Generated Product Specification

## Product Name
Research File Analysis Prototype

## One-line Description
A mock-first Streamlit prototype that demonstrates a bounded research
technology workflow without assuming the original model is integrated.

## Target User
{target_user or "Course project reviewers and research learners"}

## User Problem
Research code is difficult to demonstrate as a simple user-facing workflow.

## Core Function
Accept one input, call a unified ModelAdapter, and present a structured result.

## Product Goal
{product_goal or "Demonstrate a safe paper-to-product workflow"}

## MVP Boundary
The generated application uses mock mode by default and does not execute,
train, download, or modify the source repository.

## Risks and Limitations
Real model inputs, checkpoints, dependencies, and output conversion require
manual review and implementation.
"""


def run_productize_pipeline(
    paper_info: str,
    method_info: str,
    repo_info: str,
    repo_path: str,
    target_user: str,
    product_goal: str,
    llm_client: LLMClient | None = None,
    preferred_type: str = "auto",
    output_dir: str | Path = "generated_product",
    progress_callback: Callable[[str], None] | None = None,
    user_idea: str = "",
) -> ProductResult:
    """Generate a product prototype while preserving partial stage results."""
    result: ProductResult = {
        "opportunities": "",
        "product_spec": "",
        "template_type": "",
        "adapter_plan": "",
        "frontend_plan": "",
        "scaffold_result": {},
        "inspection": {},
        "test_report": "",
        "errors": [],
    }
    client = llm_client or LLMClient()

    def progress(stage: str) -> None:
        if progress_callback:
            progress_callback(stage)

    progress("Product Opportunity Agent analyzing")
    result["opportunities"] = _run_agent_stage(
        result,
        "Product Opportunity Agent",
        ProductOpportunityAgent,
        client,
        {
            "paper_info": paper_info,
            "method_info": method_info,
            "repo_info": repo_info,
            "target_user": target_user,
            "product_goal": product_goal,
            **({"user_idea": user_idea} if user_idea else {}),
        }
    )
    if user_idea:
        result["opportunities_input"] = result["opportunities"]
        result["opportunities"] += f"\n\n## User's Own Idea\n{user_idea}"

    if result["opportunities"]:
        progress("Product Designer Agent designing MVP")
        result["product_spec"] = _run_agent_stage(
            result,
            "Product Designer Agent",
            ProductDesignerAgent,
            client,
            {
                "opportunities": result["opportunities"],
                "paper_info": paper_info,
                "method_info": method_info,
                "repo_info": repo_info,
                **({"user_idea": user_idea} if user_idea else {}),
            },
        )
    if not result["product_spec"]:
        result["product_spec"] = _fallback_product_spec(target_user, product_goal)

    progress("Selecting product template")
    try:
        result["template_type"] = select_product_template(
            paper_info,
            method_info,
            repo_info,
            result["product_spec"],
            preferred_type,
        )
    except Exception as exc:
        _record_error(result, "Product Template Selection", exc)
        result["template_type"] = "file"

    progress("Tech Adapter Agent planning integration")
    result["adapter_plan"] = _run_agent_stage(
        result,
        "Tech Adapter Agent",
        TechAdapterAgent,
        client,
        {
            "repo_info": repo_info,
            "repo_path": repo_path,
            "product_spec": result["product_spec"],
            "template_type": result["template_type"],
        },
    )

    progress("Frontend Builder Agent planning interface")
    result["frontend_plan"] = _run_agent_stage(
        result,
        "Frontend Builder Agent",
        FrontendBuilderAgent,
        client,
        {
            "product_spec": result["product_spec"],
            "template_type": result["template_type"],
            "adapter_plan": result["adapter_plan"],
        },
    )

    progress("Generating product scaffold")
    try:
        result["scaffold_result"] = scaffold_product(
            template_type=result["template_type"],
            product_spec=result["product_spec"],
            adapter_plan=result["adapter_plan"],
            frontend_plan=result["frontend_plan"],
            repo_path=repo_path,
            output_dir=output_dir,
        )
    except Exception as exc:
        _record_error(result, "Product Scaffold", exc)
        result["scaffold_result"] = {
            "output_dir": str(output_dir),
            "files": [],
            "backup_dir": "",
            "success": False,
            "message": str(exc),
        }

    progress("Inspecting generated product")
    try:
        result["inspection"] = inspect_generated_product(output_dir)
    except Exception as exc:
        _record_error(result, "Product Inspector", exc)
        result["inspection"] = {
            "exists": False,
            "missing_files": [],
            "files": [],
            "can_run_mock": False,
            "readme_has_run_command": False,
            "syntax_ok": False,
            "compile_errors": [str(exc)],
            "notes": ["Product inspection failed."],
        }

    progress("Product Test Agent reviewing prototype")
    result["test_report"] = _run_agent_stage(
        result,
        "Product Test Agent",
        ProductTestAgent,
        client,
        {
            "generated_product_dir": result["scaffold_result"].get(
                "output_dir",
                str(output_dir),
            ),
            "template_type": result["template_type"],
            "files": result["scaffold_result"].get("files", []),
            "inspection": result["inspection"],
        },
    )
    return result
