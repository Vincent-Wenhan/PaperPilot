"""Human approval endpoints for reviewed actions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import ActionEditRequest, ActionRequest
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


@router.post("/{action_id}/reject", response_model=ActionRequest)
def reject_action(action_id: str) -> ActionRequest:
    action = run_service.reject_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{action_id}/edit", response_model=ActionRequest)
def edit_action(action_id: str, request: ActionEditRequest) -> ActionRequest:
    action = run_service.edit_action(action_id, request)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action
