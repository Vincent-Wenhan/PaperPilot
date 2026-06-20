"""Human approval endpoints for reviewed actions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import ActionEditRequest, ActionExecutionResult, ActionRequest
from backend.services.run_service import run_service

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/{action_id}", response_model=ActionRequest)
def get_action(action_id: str) -> ActionRequest:
    action = run_service.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/approve", response_model=ActionRequest)
def approve_action(action_id: str) -> ActionRequest:
    action = run_service.approve_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/execute", response_model=ActionExecutionResult)
def execute_action(action_id: str) -> ActionExecutionResult:
    try:
        result = run_service.execute_action(action_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if result.execution_status == "blocked":
        raise HTTPException(
            status_code=403,
            detail=result.model_dump(mode="json"),
        )
    return result


@router.post("/{action_id}/reject", response_model=ActionRequest)
def reject_action(action_id: str) -> ActionRequest:
    action = run_service.reject_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/edit", response_model=ActionRequest)
def edit_action(action_id: str, request: ActionEditRequest) -> ActionRequest:
    try:
        action = run_service.edit_action(action_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action
