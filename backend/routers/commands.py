"""Reviewed command endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.errors import InvalidArgumentError
from backend.schemas import (
    CommandReviewRequest,
    CommandReviewResult,
    CommandRunRequest,
    CommandRunResult,
)
from backend.services.command_service import command_service

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.post("/{run_id}/review", response_model=CommandReviewResult)
def review_command(run_id: str, request: CommandReviewRequest) -> CommandReviewResult:
    try:
        return command_service.review_command(run_id, request)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise InvalidArgumentError(str(exc)) from exc


@router.post("/{run_id}/run", response_model=CommandRunResult)
def run_command(run_id: str, request: CommandRunRequest) -> CommandRunResult:
    try:
        return command_service.run_command(run_id, request)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise InvalidArgumentError(str(exc)) from exc


@router.get("/{run_id}/result", response_model=list[CommandRunResult])
def get_command_results(run_id: str) -> list[CommandRunResult]:
    return command_service.list_results(run_id)

