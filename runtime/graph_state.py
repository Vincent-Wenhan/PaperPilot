"""Typed graph states shared by PaperPilot workflows."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class ProductizeState(TypedDict, total=False):
    papers: list[dict[str, Any]]
    target_user: str
    product_goal: str
    user_idea: str
    capability_jobs: list[dict[str, Any]]
    capability_job: dict[str, Any]
    capability_cards: Annotated[list[dict[str, Any]], operator.add]
    research_synthesis: dict[str, Any]
    proposals: list[dict[str, Any]]
    selected_proposal: dict[str, Any]
    product_plan: dict[str, Any]
    prototype_plan: dict[str, Any]
    template_type: str
    scaffold_result: dict[str, Any]
    inspection: dict[str, Any]
    evaluation: dict[str, Any]
    revision_count: int
    max_revisions: int
    revision_history: Annotated[list[dict[str, Any]], operator.add]
    graph_trace: Annotated[list[str], operator.add]
    issues: Annotated[list[dict[str, Any]], operator.add]
    tool_logs: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    result: dict[str, Any]


class ReproduceState(TypedDict, total=False):
    pdf_path: str
    paper_text: str
    paper_name: str
    github_url: str
    hardware: str
    gpu_info: str
    goal: str
    user_idea: str
    generate_code: bool
    implementation_model: str
    repo_path: str
    repo_scan: dict[str, Any]
    research_understanding: dict[str, Any]
    repository_understanding: dict[str, Any]
    reproduction_plan: dict[str, Any]
    command_plans: list[dict[str, Any]]
    command_route: str
    pending_human_review: dict[str, Any] | None
    command_results: Annotated[list[dict[str, Any]], operator.add]
    execution_diagnosis: dict[str, Any]
    implementation_bundle: dict[str, Any]
    code_review: dict[str, Any]
    code_second_review: dict[str, Any]
    code_revision_count: int
    code_max_revisions: int
    code_debate_round: int
    code_max_debate_rounds: int
    sandbox_verification: dict[str, Any]
    report_paths: dict[str, str]
    graph_trace: Annotated[list[str], operator.add]
    issues: Annotated[list[dict[str, Any]], operator.add]
    tool_logs: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    result: dict[str, Any]
