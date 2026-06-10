"""Unified OpenAI-compatible language model client."""

from __future__ import annotations

from typing import Any

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MOCK_MODE, LLM_MODEL


class LLMClient:
    """Generate text through mock mode or an OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        self.api_key = LLM_API_KEY if api_key is None else api_key
        self.base_url = LLM_BASE_URL if base_url is None else base_url
        self.model = LLM_MODEL if model is None else model
        self.mock_mode = LLM_MOCK_MODE if mock_mode is None else mock_mode
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "缺少 openai 依赖，请先安装 requirements.txt。"
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
                "当前为 mock mode，已接收系统提示和用户输入。"
            )
        if not self.api_key:
            return "未检测到 LLM API key，请在 .env 或环境变量中配置。"
        if not self.model:
            return "未配置 LLM_MODEL，请在 config.py 或环境变量中配置。"

        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            return f"LLM 调用失败：{exc}"

        content = response.choices[0].message.content
        return content or "LLM 返回了空内容。"
