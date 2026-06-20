"""Artifact endpoints for generated reports, plans, and product bundles."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.schemas import ArtifactContent, ArtifactSummary
from backend.services.artifact_service import artifact_service
from backend.services.run_service import run_service

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{run_id}", response_model=list[ArtifactSummary])
def list_artifacts(run_id: str) -> list[ArtifactSummary]:
    prefixes: list[str] | None = None
    run = run_service.get_run(run_id)
    if run is not None and run_id != "run_mock_reproduce":
        prefixes = []
        pdf_path = run.inputs.get("pdf_path", "")
        if pdf_path:
            prefixes.append(f"outputs/{Path(pdf_path).stem.replace(' ', '_')[:80]}")
        product_output_dir = str(run.result_summary.get("product_output_dir") or "")
        if product_output_dir:
            prefixes.append(product_output_dir)
    return artifact_service.list_artifacts(run_id=run_id, prefixes=prefixes)


@router.get("/{run_id}/{artifact_id:path}", response_model=ArtifactContent)
def read_artifact(run_id: str, artifact_id: str) -> ArtifactContent:
    del run_id
    try:
        return artifact_service.read_artifact(artifact_id)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
