from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from app.services.gemini_provider import GeminiProvider, to_gemini_payload
from app.services.models import Message, MessageRole, ResponseStatus


def test_gemini_converts_messages_and_system_instruction() -> None:
    system_instruction, contents = to_gemini_payload(
        [
            Message(role=MessageRole.SYSTEM, content="You are a tutor."),
            Message(role=MessageRole.USER, content="Explain gravity."),
            Message(role=MessageRole.ASSISTANT, content="Gravity pulls masses together."),
            Message(role=MessageRole.USER, content="Give an example."),
        ]
    )
    assert system_instruction == "You are a tutor."
    assert contents == [
        {"role": "user", "parts": [{"text": "Explain gravity."}]},
        {"role": "model", "parts": [{"text": "Gravity pulls masses together."}]},
        {"role": "user", "parts": [{"text": "Give an example."}]},
    ]
    assert all(item["role"] != "system" for item in contents)
    assert all(item["role"] != "assistant" for item in contents)


@pytest.mark.asyncio
async def test_gemini_missing_api_key_returns_error() -> None:
    provider = GeminiProvider(
        api_key="",
        model="gemini-3.8-flash",
        timeout_seconds=30,
        max_output_tokens=256,
        client=_fake_gemini_client("should not be called"),
    )
    response = await provider.generate(
        [Message(role=MessageRole.USER, content="Hello")]
    )
    assert response.status == ResponseStatus.ERROR
    assert response.error == "Google Gemini API key is not configured"
    assert response.content is None
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_gemini_success_normalizes_response() -> None:
    client = _fake_gemini_client("Gemini answer")
    provider = GeminiProvider(
        api_key="gemini-test",
        model="gemini-3.8-flash",
        timeout_seconds=30,
        max_output_tokens=256,
        client=client,
    )
    response = await provider.generate(
        [
            Message(role=MessageRole.SYSTEM, content="Be precise."),
            Message(role=MessageRole.USER, content="Hello"),
        ]
    )
    assert response.status == ResponseStatus.SUCCESS
    assert response.content == "Gemini answer"
    assert response.provider == "gemini"
    assert response.latency_ms >= 0
    assert client.aio.models.last_kwargs["contents"] == [
        {"role": "user", "parts": [{"text": "Hello"}]}
    ]
    config = client.aio.models.last_kwargs["config"]
    assert getattr(config, "system_instruction") == "Be precise."


@pytest.mark.asyncio
async def test_gemini_sdk_failure_is_safe_application_error() -> None:
    error = genai_errors.ClientError(
        401,
        {"error": {"message": "unauthorized", "status": "UNAUTHENTICATED"}},
        None,
    )
    client = _fake_gemini_client_error(error)
    provider = GeminiProvider(
        api_key="gemini-test",
        model="gemini-3.8-flash",
        timeout_seconds=30,
        max_output_tokens=256,
        client=client,
    )
    response = await provider.generate(
        [Message(role=MessageRole.USER, content="Hello")]
    )
    assert response.status == ResponseStatus.ERROR
    assert response.error == "Authentication failed for Google Gemini"
    assert "gemini-test" not in (response.error or "")
    assert "unauthorized" not in (response.error or "").lower()


class _FakeGeminiModels:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.last_kwargs: dict[str, object] = {}

    async def generate_content(self, **kwargs: object) -> object:
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


class _FakeGeminiAsync:
    def __init__(self, models: _FakeGeminiModels) -> None:
        self.models = models


class _FakeGeminiClient:
    def __init__(self, models: _FakeGeminiModels) -> None:
        self.aio = _FakeGeminiAsync(models)


def _fake_gemini_client(text: str) -> _FakeGeminiClient:
    return _FakeGeminiClient(_FakeGeminiModels(text=text))


def _fake_gemini_client_error(error: Exception) -> _FakeGeminiClient:
    return _FakeGeminiClient(_FakeGeminiModels(error=error))
