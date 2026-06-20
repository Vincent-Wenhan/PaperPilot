"""LLM configuration checks for the Workbench."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from backend.schemas import LLMConnectionRequest, LLMConnectionResult
from config import PROJECT_ROOT
from tools.llm_client import LLMClient, LLMClientError

router = APIRouter(prefix="/api/llm", tags=["llm"])

LLM_CONFIG_FILE = PROJECT_ROOT / "llm_config.json"


class LlmConfigData(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    implementation_model: str = ""


@router.get("/config", response_model=LlmConfigData)
def get_llm_config() -> LlmConfigData:
    if LLM_CONFIG_FILE.is_file():
        try:
            import json
            data = json.loads(LLM_CONFIG_FILE.read_text(encoding="utf-8"))
            return LlmConfigData(
                api_key="",
                base_url=data.get("base_url", ""),
                model=data.get("model", ""),
                implementation_model=data.get("implementation_model", ""),
            )
        except Exception:
            pass
    return LlmConfigData()


@router.post("/config", response_model=LlmConfigData)
def save_llm_config(config: LlmConfigData) -> LlmConfigData:
    import json
    LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LLM_CONFIG_FILE.write_text(
        json.dumps({
            "base_url": config.base_url,
            "model": config.model,
            "implementation_model": config.implementation_model,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return config


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
