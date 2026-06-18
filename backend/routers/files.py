"""Read-only generated-code file endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.schemas import FileContent, FileNode
from backend.services.file_service import file_service

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{run_id}", response_model=list[FileNode])
def list_files(run_id: str) -> list[FileNode]:
    del run_id
    return file_service.list_files()


@router.get("/{run_id}/content", response_model=FileContent)
def read_file_content(run_id: str, path: str = Query(..., min_length=1)) -> FileContent:
    del run_id
    try:
        return file_service.read_content(path)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
