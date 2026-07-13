"""Run and event endpoints for the workbench API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.errors import InvalidArgumentError, NotFoundError
from backend.schemas import (
    ActionRequest,
    CancelRunRequest,
    ProductizeProposalExecuteRequest,
    ResumeRunRequest,
    RevisionRequest,
    RevisionResult,
    RetryRunRequest,
    RunCreateRequest,
    RunRecord,
    WorkbenchEvent,
    WorkbenchSnapshot,
)
from backend.services.event_service import event_service
from backend.services.graph_service import graph_service
from backend.services.run_service import run_service
from backend.services.workbench_mock import build_workbench_snapshot

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/workbench/mock", response_model=WorkbenchSnapshot)
def get_mock_workbench() -> WorkbenchSnapshot:
    return build_workbench_snapshot()


@router.post("/runs", response_model=RunRecord)
def create_run(request: RunCreateRequest) -> RunRecord:
    return run_service.create_run(
        request,
        start_pipeline=request.run_pipeline,
    )


@router.get("/runs/{run_id}", response_model=RunRecord)
def get_run(run_id: str) -> RunRecord:
    run = run_service.get_run(run_id)
    if run is None:
        raise NotFoundError("Run not found")
    return run


@router.get("/runs/{run_id}/events", response_model=list[WorkbenchEvent])
def get_run_events(run_id: str, after: str = Query(default="")) -> list[WorkbenchEvent]:
    if run_service.get_run(run_id) is None:
        raise NotFoundError("Run not found")
    if after:
        return event_service.list_events(run_id, after_id=after)
    return run_service.list_events(run_id)


@router.get("/runs/{run_id}/actions", response_model=list[ActionRequest])
def get_run_actions(run_id: str) -> list[ActionRequest]:
    if run_service.get_run(run_id) is None:
        raise NotFoundError("Run not found")
    return run_service.list_actions(run_id)


@router.get("/runs/{run_id}/result")
def get_run_result(run_id: str) -> dict[str, Any]:
    if run_service.get_run(run_id) is None:
        raise NotFoundError("Run not found")
    result = run_service.get_result(run_id)
    if result is None:
        raise NotFoundError("Run result not available")
    return result


@router.post("/runs/{run_id}/revision", response_model=RevisionResult)
def request_run_revision(run_id: str, request: RevisionRequest) -> RevisionResult:
    try:
        return run_service.request_revision(
            run_id,
            issue_id=request.issue_id,
            action=request.action,
            instruction=request.instruction,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Run not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("/runs/{run_id}/productize/proposals/{proposal_index}/execute")
def execute_productize_proposal(
    run_id: str,
    proposal_index: int,
    request: ProductizeProposalExecuteRequest | None = None,
) -> dict[str, Any]:
    try:
        body = request or ProductizeProposalExecuteRequest()
        return run_service.execute_productize_proposal(
            run_id,
            proposal_index,
            api_key=body.api_key,
            base_url=body.base_url,
            model=body.model,
            mock_mode=body.mock_mode,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Run not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/runs/{run_id}/graph")
def get_run_graph(run_id: str) -> list[dict[str, Any]]:
    run = run_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events = run_service.list_events(run_id)
    return graph_service.build_graph(run.mode, events)


@router.post("/runs/{run_id}/cancel", response_model=RunRecord)
def cancel_run(run_id: str, request: CancelRunRequest | None = None) -> RunRecord:
    body = request or CancelRunRequest()
    try:
        result = run_service.cancel_run(run_id, reason=body.reason)
    except ValueError as exc:
        raise InvalidArgumentError(str(exc)) from exc
    if result is None:
        raise NotFoundError("Run not found")
    return result


@router.post("/runs/{run_id}/retry", response_model=RunRecord)
def retry_run(run_id: str, request: RetryRunRequest | None = None) -> RunRecord:
    body = request or RetryRunRequest()
    try:
        result = run_service.retry_run(run_id, from_step=body.from_step)
    except ValueError as exc:
        raise InvalidArgumentError(str(exc)) from exc
    if result is None:
        raise NotFoundError("Run not found")
    return result


@router.post("/runs/{run_id}/resume", response_model=RunRecord)
def resume_run(run_id: str, request: ResumeRunRequest | None = None) -> RunRecord:
    body = request or ResumeRunRequest()
    try:
        result = run_service.resume_run(run_id, approved=body.approved, feedback=body.feedback)
    except ValueError as exc:
        raise InvalidArgumentError(str(exc)) from exc
    if result is None:
        raise NotFoundError("Run not found")
    return result
