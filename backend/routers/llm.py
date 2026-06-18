"""LLM configuration checks for the Workbench."""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import LLMConnectionRequest, LLMConnectionResult
from tools.llm_client import LLMClient, LLMClientError

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/test", response_model=LLMConnectionResult)
def test_llm_connection(request: LLMConnectionRequest) -> LLMConnectionResult:
    client = LLMClient(
        api_key=request.api_key or None,
        base_url=request.base_url or None,
        model=request.model or None,
        mock_mode=request.mock_mode,
    )
    try:
        message = client.test_connection()
    except LLMClientError as exc:
        return LLMConnectionResult(
            ok=False,
            message=str(exc),
            endpoint=client.endpoint_label,
            model=client.model,
            mock_mode=client.mock_mode,
        )
    return LLMConnectionResult(
        ok=True,
        message=message,
        endpoint=client.endpoint_label,
        model=client.model,
        mock_mode=client.mock_mode,
    )
