"""Read-only generated-code file endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.errors import NotFoundError
from backend.schemas import FileContent, FileNode
from backend.services.file_service import file_service

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{run_id}", response_model=list[FileNode])
def list_files(run_id: str) -> list[FileNode]:
    return file_service.list_files(run_id=run_id)


@router.get("/{run_id}/content", response_model=FileContent)
def read_file_content(run_id: str, path: str = Query(..., min_length=1)) -> FileContent:
    try:
        return file_service.read_content(path, run_id=run_id)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise NotFoundError(str(exc)) from exc

