"""Structured error envelopes for the workbench API.

All non-2xx responses use the shape::

    {
      "error": {
        "code": "not_found",
        "message": "Run not found",
        ...optional fields...
      }
    }

This makes error handling on the client deterministic and lets the UI
branch on error codes rather than parsing prose.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class WorkbenchError(Exception):
    """Base class for structured workbench errors."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.extra = extra


class NotFoundError(WorkbenchError):
    code = "not_found"
    status_code = 404


class InvalidArgumentError(WorkbenchError):
    code = "invalid_argument"
    status_code = 400


class PermissionDeniedError(WorkbenchError):
    code = "permission_denied"
    status_code = 403


async def workbench_error_handler(_: Request, exc: WorkbenchError) -> JSONResponse:
    payload: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
        }
    }
    if exc.extra:
        payload["error"].update(exc.extra)
    return JSONResponse(status_code=exc.status_code, content=payload)


async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "invalid_argument",
                "message": str(exc) or "Invalid argument",
            }
        },
    )


async def file_not_found_handler(_: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "not_found",
                "message": str(exc) or "File not found",
            }
        },
    )
