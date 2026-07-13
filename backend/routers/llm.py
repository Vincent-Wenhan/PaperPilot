"""LLM configuration checks for the Workbench.

The API key is treated as a secret: it is read from the environment or an
OS keyring, persisted outside the repository, and never returned by the API.
Only a masked hint and ``configured`` flag are exposed to clients.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.schemas import LLMConnectionRequest, LLMConnectionResult
from config import PROJECT_ROOT
from tools.llm_client import LLMClient, LLMClientError

router = APIRouter(prefix="/api/llm", tags=["llm"])

LLM_CONFIG_FILE = PROJECT_ROOT / "llm_config.json"


class LlmConfigData(BaseModel):
    """Public view of the LLM configuration.

    ``api_key`` is kept for backward-compatible shape but is always returned
    as a masked hint.  ``configured`` is the authoritative flag clients should
    use to decide whether model calls can be made.
    """

    configured: bool = False
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    implementation_model: str = ""


def _load_config() -> dict[str, Any]:
    if LLM_CONFIG_FILE.is_file():
        try:
            return json.loads(LLM_CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _resolve_api_key() -> str:
    """Resolve the API key from env or keyring, never from the repo file."""

    env_key = os.environ.get("LLM_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        import keyring  # type: ignore

        value = keyring.get_password("paperpilot", "llm_api_key")
        if value:
            return value
    except Exception:
        pass

    config = _load_config()
    legacy = str(config.get("api_key", "")).strip()
    return legacy


def _persist_api_key(api_key: str) -> None:
    """Persist the API key via OS keyring; fall back to env-only."""

    api_key = (api_key or "").strip()
    try:
        import keyring  # type: ignore

        if api_key:
            keyring.set_password("paperpilot", "llm_api_key", api_key)
        else:
            try:
                keyring.delete_password("paperpilot", "llm_api_key")
            except Exception:
                pass
        return
    except Exception:
        pass

    # No keyring available: callers should use LLM_API_KEY env var instead.
    # We deliberately do NOT write the key to llm_config.json.


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return f"••••{value[-4:]}"


def _public_view() -> LlmConfigData:
    config = _load_config()
    api_key = _resolve_api_key()
    base_url = str(config.get("base_url", "") or os.environ.get("LLM_BASE_URL", ""))
    model = str(config.get("model", "") or os.environ.get("LLM_MODEL", ""))
    implementation_model = str(config.get("implementation_model", ""))
    return LlmConfigData(
        configured=bool(api_key),
        api_key=_mask(api_key),
        base_url=base_url,
        model=model,
        implementation_model=implementation_model,
    )


@router.get("/config", response_model=LlmConfigData)
def get_llm_config() -> LlmConfigData:
    return _public_view()


@router.post("/config", response_model=LlmConfigData)
def save_llm_config(config: LlmConfigData) -> LlmConfigData:
    existing = _load_config()
    payload: dict[str, Any] = {
        "base_url": config.base_url,
        "model": config.model,
        "implementation_model": config.implementation_model,
    }
    # Persist non-secret fields to the repo-local config file so that the
    # UI can reload them.  The API key is stored via keyring (or env var).
    LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LLM_CONFIG_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Only overwrite the stored key when a new key is supplied.  An empty
    # value means "leave the existing key alone" so a redacted reload does
    # not clobber the secret.
    if config.api_key and not config.api_key.startswith("•"):
        _persist_api_key(config.api_key)
    elif "api_key" in existing and existing["api_key"]:
        # Keep existing key
        pass

    return _public_view()


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
