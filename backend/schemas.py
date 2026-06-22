"""Pydantic contracts for the PaperPilot workbench API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RunMode = Literal["reproduce", "productize"]
WorkflowStatus = Literal[
    "pending",
    "running",
    "success",
    "waiting_review",
    "failed",
    "revised",
]
ActionDecision = Literal["approved", "rejected", "edited"]
ActionStatus = Literal["pending", "approved", "rejected", "edited"]
ActionRisk = Literal["low", "medium", "high", "blocked"]
ActionExecutionStatus = Literal[
    "not_started",
    "running",
    "succeeded",
    "failed",
    "blocked",
]
ActionTool = Literal["run_command", "apply_patch"]
RevisionAction = Literal[
    "revise_prd",
    "reduce_mvp_scope",
    "revise_prototype",
    "accept_with_warning",
]


class RunCreateRequest(BaseModel):
    """Create a workbench run record.

    The initial API facade creates a planned run and event stream shell. Pipeline
    execution can be attached behind this contract without changing the UI.
    """

    mode: RunMode
    project_id: str = "default"
    task: str = ""
    pdf_path: str = ""
    pdf_paths: list[str] = Field(default_factory=list)
    github_url: str = ""
    hardware: str = "CPU only"
    gpu_info: str = ""
    goal: str = "minimal training experiment"
    target_user: str = ""
    product_goal: str = ""
    preferred_type: str = "auto"
    run_pipeline: bool = True
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    implementation_model: str = ""
    mock_mode: bool = False


class RunRecord(BaseModel):
    run_id: str
    project_id: str
    mode: RunMode
    status: WorkflowStatus
    task: str
    created_at: str
    updated_at: str
    summary: str
    inputs: dict[str, str] = Field(default_factory=dict)
    result_summary: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)


class LLMConnectionRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    mock_mode: bool = False


class LLMConnectionResult(BaseModel):
    ok: bool
    message: str
    endpoint: str = ""
    model: str = ""
    mock_mode: bool = False


class ProductizeProposalExecuteRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    mock_mode: bool | None = None


class WorkbenchEvent(BaseModel):
    event_id: str
    run_id: str
    node: str
    agent: str
    event_type: str
    status: WorkflowStatus
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ActionRequest(BaseModel):
    action_id: str
    run_id: str
    agent: str
    tool: ActionTool
    command: str = ""
    cwd: str = "."
    execution_mode: Literal["safe", "review", "sandbox"] = "review"
    patch_id: str = ""
    path: str = ""
    risk: ActionRisk
    reason: str
    status: ActionStatus = "pending"
    edited_command: str = ""
    execution_status: ActionExecutionStatus = "not_started"
    execution_result: dict[str, Any] = Field(default_factory=dict)


class ActionEditRequest(BaseModel):
    edited_command: str
    reason: str = ""


class RevisionRequest(BaseModel):
    issue_id: str
    action: RevisionAction
    instruction: str = ""


class RevisionResult(BaseModel):
    run_id: str
    issue_id: str
    action: RevisionAction
    status: WorkflowStatus = "revised"
    message: str
    revision_history: list[dict[str, Any]] = Field(default_factory=list)


class ArtifactSummary(BaseModel):
    artifact_id: str
    run_id: str
    name: str
    kind: str
    path: str
    size_bytes: int
    status: WorkflowStatus = "success"


class ArtifactContent(BaseModel):
    artifact_id: str
    path: str
    content: str
    truncated: bool = False


class FileNode(BaseModel):
    path: str
    name: str
    kind: Literal["file", "directory"]
    size_bytes: int = 0


class FileContent(BaseModel):
    path: str
    content: str
    truncated: bool = False


class PatchProposeRequest(BaseModel):
    path: str
    new_content: str
    reason: str = ""


class PatchProposal(BaseModel):
    patch_id: str
    run_id: str
    path: str
    old_content: str
    new_content: str
    unified_diff: str
    reason: str = ""
    status: Literal["proposed", "applied", "rejected"] = "proposed"


class PatchApplyResult(BaseModel):
    patch_id: str
    path: str
    applied: bool
    message: str
    syntax_ok: bool = True
    syntax_failures: list[dict[str, str]] = Field(default_factory=list)


class SyntaxCheckRequest(BaseModel):
    path: str
    recursive: bool = False


class SyntaxCheckResult(BaseModel):
    path: str
    success: bool
    failures: list[dict[str, str]] = Field(default_factory=list)
    error: str = ""


class CommandReviewRequest(BaseModel):
    command: str
    cwd: str = "."


class CommandReviewResult(BaseModel):
    run_id: str
    command: str
    cwd: str
    risk_level: str
    requires_confirmation: bool
    blocked_reason: str | None = None


class CommandRunRequest(BaseModel):
    command: str
    cwd: str = "."
    mode: Literal["safe", "review", "sandbox"] = "safe"
    timeout: int = 120


class CommandRunResult(BaseModel):
    run_id: str
    command: str
    cwd: str
    mode: str
    executed: bool
    risk_level: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    blocked_reason: str | None = None


class ActionExecutionResult(BaseModel):
    action: ActionRequest
    message: str
    execution_status: ActionExecutionStatus
    command_result: CommandRunResult | None = None
    patch_result: PatchApplyResult | None = None
    blocked_reason: str | None = None


class WorkbenchSnapshot(BaseModel):
    project_id: str
    active_run: RunRecord
    events: list[WorkbenchEvent]
    actions: list[ActionRequest]
    artifacts: list[ArtifactSummary]
    files: list[FileNode]
