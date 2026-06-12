"""Tests for actionable LLM client diagnostics."""

from __future__ import annotations

import unittest

from tools.llm_client import (
    LLMClient,
    LLMConfigurationError,
    LLMConnectionError,
    LLMRequestError,
)


class _Completions:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def create(self, **kwargs: object) -> object:
        del kwargs
        raise self.error


class _FakeOpenAIClient:
    def __init__(self, error: Exception) -> None:
        self.chat = type("Chat", (), {"completions": _Completions(error)})()


class _AuthenticationFailure(Exception):
    status_code = 401


class _BadRequestFailure(Exception):
    status_code = 400
    body = {"error": {"message": "model not found"}}


class LLMClientTests(unittest.TestCase):
    def test_connection_error_reports_endpoint_and_network_guidance(self) -> None:
        client = LLMClient(
            api_key="test-key",
            base_url="https://llm.example.test/v1",
            model="test-model",
        )
        client._client = _FakeOpenAIClient(ConnectionError("network offline"))

        with self.assertRaises(LLMConnectionError) as raised:
            client.test_connection()

        message = str(raised.exception)
        self.assertIn("https://llm.example.test/v1", message)
        self.assertIn("network offline", message)
        self.assertIn("Base URL", message)

    def test_authentication_error_is_not_reported_as_json_error(self) -> None:
        client = LLMClient(api_key="bad-key", model="test-model")
        client._client = _FakeOpenAIClient(_AuthenticationFailure("bad key"))

        with self.assertRaisesRegex(LLMRequestError, "rejected the API key"):
            client.generate("system", "user")

    def test_invalid_base_url_is_reported_before_request(self) -> None:
        client = LLMClient(
            api_key="test-key",
            base_url="api.example.test/v1",
            model="test-model",
        )

        with self.assertRaisesRegex(LLMConfigurationError, "complete HTTP"):
            client.test_connection()

    def test_likely_medium_typo_is_rejected_before_request(self) -> None:
        client = LLMClient(api_key="test-key", model="gpt-5.4-mediem")

        with self.assertRaisesRegex(LLMConfigurationError, "likely typo"):
            client.test_connection()

    def test_bad_request_reports_model_and_provider_body(self) -> None:
        client = LLMClient(api_key="test-key", model="unsupported-model")
        client._client = _FakeOpenAIClient(_BadRequestFailure("bad request"))

        with self.assertRaises(LLMRequestError) as raised:
            client.generate("system", "user")

        message = str(raised.exception)
        self.assertIn("unsupported-model", message)
        self.assertIn("model not found", message)
        self.assertFalse(raised.exception.blocks_client)


if __name__ == "__main__":
    unittest.main()
