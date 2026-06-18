"""Static check endpoints for generated files."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.schemas import SyntaxCheckRequest, SyntaxCheckResult
from backend.services.check_service import check_service

router = APIRouter(prefix="/api/checks", tags=["checks"])


@router.post("/{run_id}/syntax", response_model=SyntaxCheckResult)
def syntax_check(run_id: str, request: SyntaxCheckRequest) -> SyntaxCheckResult:
    del run_id
    try:
        return check_service.syntax_check(request)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
