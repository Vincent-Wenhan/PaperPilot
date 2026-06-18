"""Unified OpenAI-compatible language model client."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit


class LLMClientError(RuntimeError):
    """Base error for actionable LLM configuration or request failures."""

    def __init__(self, message: str, *, blocks_client: bool = False) -> None:
        super().__init__(message)
        self.blocks_client = blocks_client


class LLMConfigurationError(LLMClientError):
    """The local LLM client configuration is incomplete or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message, blocks_client=True)


class LLMConnectionError(LLMClientError):
    """The configured LLM endpoint could not be reached."""

    def __init__(self, message: str) -> None:
        super().__init__(message, blocks_client=True)


class LLMRequestError(LLMClientError):
    """The endpoint rejected or failed an LLM request."""


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
        mock_env = os.getenv("LLM_MOCK_MODE", "false").lower()
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
            raise LLMConfigurationError(
                "The `openai` package is not installed in the Python environment "
                "running PaperPilot. Install requirements.txt in that environment."
            ) from exc

        options: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": 90.0,
            "max_retries": 2,
        }
        if self.base_url:
            options["base_url"] = self.base_url
        self._client = OpenAI(**options)
        return self._client

    @property
    def endpoint_label(self) -> str:
        """Return the endpoint without exposing credentials."""
        raw = self.base_url.rstrip("/") if self.base_url else "https://api.openai.com/v1"
        parsed = urlsplit(raw)
        host = parsed.hostname or ""
        if parsed.port:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))

    @staticmethod
    def _root_cause(exc: Exception) -> str:
        current: BaseException = exc
        seen: set[int] = set()
        while (
            (current.__cause__ is not None or current.__context__ is not None)
            and id(current) not in seen
        ):
            seen.add(id(current))
            current = current.__cause__ or current.__context__ or current
        detail = " ".join(str(current).split())
        return detail[:400]

    @staticmethod
    def _response_detail(exc: Exception) -> str:
        """Extract an API error body before falling back to the transport cause."""
        details: list[str] = []
        body = getattr(exc, "body", None)
        if body:
            details.append(str(body))
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                response_body = response.json()
            except Exception:
                response_body = getattr(response, "text", "")
            if response_body:
                details.append(str(response_body))
        if not details:
            details.append(LLMClient._root_cause(exc))
        return " ".join(" ".join(item.split()) for item in details if item)[:700]

    def _request_error(self, exc: Exception) -> LLMClientError:
        error_name = type(exc).__name__
        status_code = getattr(exc, "status_code", None)
        detail_text = self._response_detail(exc)
        endpoint = self.endpoint_label
        if "socksio" in detail_text.lower():
            return LLMConfigurationError(
                "The Python environment is using a SOCKS proxy for LLM requests, "
                "but the optional `socksio` dependency is not installed. Run "
                "`python -m pip install -r requirements.txt` in the active "
                "PaperPilot environment, or remove the SOCKS proxy environment "
                "variable if it is not needed."
            )
        if error_name == "APIConnectionError" or isinstance(exc, ConnectionError):
            proxy_note = (
                " A system HTTP(S)/SOCKS proxy is configured; verify that it is running "
                "and permits this endpoint."
                if any(os.getenv(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"))
                else ""
            )
            detail = f" Underlying cause: {detail_text}." if detail_text else ""
            return LLMConnectionError(
                f"Could not connect to LLM endpoint `{endpoint}`.{detail}{proxy_note} "
                "Check Base URL, network/proxy settings, TLS certificates, and firewall."
            )
        if status_code == 401 or error_name == "AuthenticationError":
            return LLMRequestError(
                f"LLM endpoint `{endpoint}` rejected the API key (HTTP 401).",
                blocks_client=True,
            )
        if status_code == 429 or error_name == "RateLimitError":
            return LLMRequestError(
                f"LLM endpoint `{endpoint}` rate-limited the request or has no available quota "
                "(HTTP 429).",
                blocks_client=True,
            )
        if status_code == 400 or error_name == "BadRequestError":
            detail = f" Provider response: {detail_text}" if detail_text else ""
            return LLMRequestError(
                f"LLM endpoint `{endpoint}` rejected model `{self.model}` or the request "
                f"format (HTTP 400). Verify the exact model identifier supported by the "
                f"proxy and its Chat Completions compatibility.{detail}"
            )
        status = f"HTTP {status_code}" if status_code else error_name
        detail = f": {detail_text}" if detail_text else ""
        return LLMRequestError(
            f"LLM request to `{endpoint}` failed ({status}){detail}"
        )

    @staticmethod
    def _uses_max_completion_tokens(model: str) -> bool:
        """Recent o-series models use max_completion_tokens instead of max_tokens."""
        known_prefixes = ("o1", "o3", "o4", "gpt-5")
        return any(model.startswith(prefix) for prefix in known_prefixes)

    def _create_completion(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
    ) -> Any:
        options: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if max_tokens is not None:
            if self._uses_max_completion_tokens(self.model):
                options["max_completion_tokens"] = max_tokens
            else:
                options["max_tokens"] = max_tokens
        try:
            return self._get_client().chat.completions.create(**options)
        except LLMClientError:
            raise
        except Exception as exc:
            raise self._request_error(exc) from exc

    def test_connection(self) -> str:
        """Perform a tiny explicit request to validate endpoint, key, and model."""
        if self.mock_mode:
            return "Mock Mode is enabled; no endpoint request was made."
        self._validate_configuration()
        response = self._create_completion(
            [{"role": "user", "content": "Reply with OK."}],
            max_tokens=4,
        )
        content = response.choices[0].message.content
        return (content or "Connected, but the model returned empty content.").strip()

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise LLMConfigurationError(
                "No LLM API key is configured. Add one in the sidebar or enable Mock Mode."
            )
        if not self.model:
            raise LLMConfigurationError(
                "No LLM model is configured. Set the Model field in the sidebar."
            )
        if "mediem" in self.model.lower():
            raise LLMConfigurationError(
                f"Model `{self.model}` contains the likely typo `mediem`. "
                "Use the exact model identifier from your proxy provider; if intended, "
                "check whether it should be `medium`."
            )
        if self.base_url:
            parsed = urlsplit(self.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise LLMConfigurationError(
                    "Base URL must be a complete HTTP(S) endpoint, for example "
                    "`https://api.openai.com/v1`."
                )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return generated text or raise an actionable client error."""
        if self.mock_mode:
            return (
                "# PaperPilot Mock Result\n\n"
                "Mock mode is active. The system prompt and user input have been received."
            )
        self._validate_configuration()
        response = self._create_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        content = response.choices[0].message.content
        if not content:
            raise LLMRequestError("LLM returned empty content.")
        return content
