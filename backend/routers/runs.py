"""Run and event endpoints for the workbench API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.schemas import RunCreateRequest, RunRecord, WorkbenchEvent, WorkbenchSnapshot
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
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/events", response_model=list[WorkbenchEvent])
def get_run_events(run_id: str) -> list[WorkbenchEvent]:
    if run_service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_service.list_events(run_id)


@router.get("/runs/{run_id}/result")
def get_run_result(run_id: str) -> dict[str, Any]:
    if run_service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    result = run_service.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run result not available")
    return result


@router.get("/runs/{run_id}/graph")
def get_run_graph(run_id: str) -> list[dict[str, Any]]:
    run = run_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events = run_service.list_events(run_id)
    return graph_service.build_graph(run.mode, events)
