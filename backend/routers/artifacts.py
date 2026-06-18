"""Artifact endpoints for generated reports, plans, and product bundles."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import ArtifactContent, ArtifactSummary
from backend.services.artifact_service import artifact_service

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{run_id}", response_model=list[ArtifactSummary])
def list_artifacts(run_id: str) -> list[ArtifactSummary]:
    return artifact_service.list_artifacts(run_id=run_id)


@router.get("/{run_id}/{artifact_id:path}", response_model=ArtifactContent)
def read_artifact(run_id: str, artifact_id: str) -> ArtifactContent:
    del run_id
    try:
        return artifact_service.read_artifact(artifact_id)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
