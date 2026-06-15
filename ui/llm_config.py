"""LLM configuration helpers for the Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import toml

from config import LLM_BASE_URL, LLM_MOCK_MODE, LLM_MODEL, PROJECT_ROOT
from tools.llm_client import LLMClient

SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"


def load_secrets() -> dict[str, str]:
    if SECRETS_FILE.is_file():
        try:
            data: dict[str, str] = toml.load(str(SECRETS_FILE))
            return {
                k: (v or "")
                for k, v in data.items()
                if k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
            }
        except Exception:
            pass
    return {}


def save_secrets(api_key: str, base_url: str, model: str) -> None:
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRETS_FILE.write_text(
        toml.dumps(
            {
                "LLM_API_KEY": api_key,
                "LLM_BASE_URL": base_url,
                "LLM_MODEL": model,
            }
        ),
        encoding="utf-8",
    )


def get_llm_client() -> LLMClient:
    api_key = str(st.session_state.get("llm_api_key") or "").strip() or None
    base_url = str(st.session_state.get("llm_base_url") or "").strip() or None
    model = str(st.session_state.get("llm_model") or "").strip() or None
    return LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        mock_mode=st.session_state.get("llm_mock_mode", LLM_MOCK_MODE),
    )


def get_implementation_llm_client() -> LLMClient:
    client = get_llm_client()
    implementation_model = str(
        st.session_state.get("llm_implementation_model") or ""
    ).strip()
    if not implementation_model or implementation_model == client.model:
        return client
    return LLMClient(
        api_key=client.api_key,
        base_url=client.base_url,
        model=implementation_model,
        mock_mode=client.mock_mode,
    )


def init_llm_sidebar_defaults() -> None:
    saved_secrets = load_secrets()
    st.session_state.setdefault("llm_api_key", saved_secrets.get("LLM_API_KEY") or "")
    st.session_state.setdefault(
        "llm_base_url",
        saved_secrets.get("LLM_BASE_URL") or LLM_BASE_URL or "https://api.openai.com/v1",
    )
    st.session_state.setdefault(
        "llm_model",
        saved_secrets.get("LLM_MODEL") or LLM_MODEL,
    )
    st.session_state.setdefault("llm_implementation_model", "")
    st.session_state.setdefault("llm_mock_mode", LLM_MOCK_MODE)
