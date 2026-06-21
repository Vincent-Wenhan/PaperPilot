"""Patch proposal and apply endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import ActionRequest, PatchProposal, PatchProposeRequest
from backend.services.patch_service import patch_service
from backend.services.run_service import run_service

router = APIRouter(prefix="/api/patches", tags=["patches"])


@router.get("/{run_id}", response_model=list[PatchProposal])
def list_patches(run_id: str) -> list[PatchProposal]:
    return patch_service.list_patches(run_id=run_id)


@router.post("/{run_id}/propose", response_model=PatchProposal)
def propose_patch(run_id: str, request: PatchProposeRequest) -> PatchProposal:
    try:
        return patch_service.propose_patch(run_id, request)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{run_id}/{patch_id}", response_model=PatchProposal)
def get_patch(run_id: str, patch_id: str) -> PatchProposal:
    patch = patch_service.get_patch(patch_id)
    if patch is None or patch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post("/{run_id}/apply/{patch_id}", response_model=ActionRequest)
def request_apply_patch(run_id: str, patch_id: str) -> ActionRequest:
    patch = patch_service.get_patch(patch_id)
    if patch is None or patch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Patch not found")
    try:
        return run_service.create_patch_action(run_id, patch_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
