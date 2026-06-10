"""Unified OpenAI-compatible language model client."""

from __future__ import annotations

import os
from typing import Any


class LLMClient:
    """Generate text through mock mode or an OpenAI-compatible endpoint.

    Config is resolved in priority order:
      1. Constructor kwargs (passed by caller)
      2. Environment variables (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_MOCK_MODE)
      3. Hardcoded defaults
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY", "")
        self.base_url = base_url if base_url is not None else os.getenv("LLM_BASE_URL", "")
        self.model = (
            model
            if model is not None
            else os.getenv("LLM_MODEL", "gpt-4o-mini")
        )
        mock_env = os.getenv("LLM_MOCK_MODE", "true").lower()
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else mock_env in {"1", "true", "yes", "on"}
        )
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Missing openai dependency. Please install requirements.txt."
            ) from exc

        options: dict[str, str] = {"api_key": self.api_key}
        if self.base_url:
            options["base_url"] = self.base_url
        self._client = OpenAI(**options)
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return generated text without failing when credentials are absent."""
        if self.mock_mode:
            return (
                "# PaperPilot Mock Result\n\n"
                "Mock mode is active. The system prompt and user input have been received."
            )
        if not self.api_key:
            return "No LLM API key detected. Please configure it in .env or environment variables."
        if not self.model:
            return "LLM_MODEL is not configured. Please set it in config.py or environment variables."

        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            return f"LLM call failed: {exc}"

        content = response.choices[0].message.content
        return content or "LLM returned empty content."
