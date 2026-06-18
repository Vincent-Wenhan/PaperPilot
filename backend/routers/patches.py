"""Patch proposal and apply endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import PatchApplyResult, PatchProposal, PatchProposeRequest
from backend.services.patch_service import patch_service

router = APIRouter(prefix="/api/patches", tags=["patches"])


@router.post("/{run_id}/propose", response_model=PatchProposal)
def propose_patch(run_id: str, request: PatchProposeRequest) -> PatchProposal:
    try:
        return patch_service.propose_patch(run_id, request)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{run_id}/{patch_id}", response_model=PatchProposal)
def get_patch(run_id: str, patch_id: str) -> PatchProposal:
    del run_id
    patch = patch_service.get_patch(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post("/{run_id}/apply/{patch_id}", response_model=PatchApplyResult)
def apply_patch(run_id: str, patch_id: str) -> PatchApplyResult:
    del run_id
    try:
        result = patch_service.apply_patch(patch_id)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return result
