from types import SimpleNamespace

import httpx
import openai
import pytest

from app.services.exceptions import (
    AuthenticationFailureError,
    RateLimitError,
)
from app.services.models import Message, MessageRole, ResponseStatus
from app.services.openai_provider import OpenAIProvider, to_openai_messages


def test_openai_converts_internal_messages() -> None:
    converted = to_openai_messages(
        [
            Message(role=MessageRole.SYSTEM, content="Be concise."),
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi"),
            Message(role=MessageRole.USER, content="Follow up"),
        ]
    )
    assert converted == [
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Follow up"},
    ]


@pytest.mark.asyncio
async def test_openai_missing_api_key_returns_error() -> None:
    provider = OpenAIProvider(
        api_key="",
        model="gpt-4o-mini",
        timeout_seconds=30,
        max_output_tokens=256,
        client=_fake_openai_client("should not be called"),
    )
    response = await provider.generate(
        [Message(role=MessageRole.USER, content="Hello")]
    )
    assert response.status == ResponseStatus.ERROR
    assert response.content is None
    assert response.error == "OpenAI API key is not configured"
    assert response.latency_ms >= 0
    assert response.provider == "openai"
    assert response.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_openai_success_normalizes_response() -> None:
    client = _fake_openai_client("Generated answer")
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        timeout_seconds=30,
        max_output_tokens=256,
        client=client,
    )
    messages = [Message(role=MessageRole.USER, content="Hello")]
    response = await provider.generate(messages)
    assert response.status == ResponseStatus.SUCCESS
    assert response.content == "Generated answer"
    assert response.error is None
    assert response.latency_ms >= 0
    assert client.chat.completions.last_kwargs["messages"] == [
        {"role": "user", "content": "Hello"}
    ]
    assert client.chat.completions.last_kwargs["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_openai_timeout_is_recorded_as_error() -> None:
    client = _FakeOpenAIClient(_SlowCompletions())
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        timeout_seconds=0.05,
        max_output_tokens=256,
        client=client,
    )
    response = await provider.generate(
        [Message(role=MessageRole.USER, content="Hello")]
    )
    assert response.status == ResponseStatus.ERROR
    assert response.error == "OpenAI request timed out"
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_openai_sdk_failure_is_safe_application_error() -> None:
    client = _fake_openai_client_error(_openai_status_error(openai.AuthenticationError))
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        timeout_seconds=30,
        max_output_tokens=256,
        client=client,
    )
    response = await provider.generate(
        [Message(role=MessageRole.USER, content="Hello")]
    )
    assert response.status == ResponseStatus.ERROR
    assert response.content is None
    assert response.error == "Authentication failed for OpenAI"
    assert "sk-test" not in (response.error or "")


def test_openai_maps_rate_limit_error() -> None:
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        timeout_seconds=30,
        max_output_tokens=256,
    )
    mapped = provider._map_sdk_error(_openai_status_error(openai.RateLimitError))
    assert isinstance(mapped, RateLimitError)
    assert "sk-" not in mapped.message


def test_openai_maps_authentication_error() -> None:
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        timeout_seconds=30,
        max_output_tokens=256,
    )
    mapped = provider._map_sdk_error(
        _openai_status_error(openai.AuthenticationError)
    )
    assert isinstance(mapped, AuthenticationFailureError)


class _SlowCompletions:
    async def create(self, **kwargs: object) -> object:
        import asyncio

        await asyncio.sleep(1)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="late"))]
        )


class _FakeCompletions:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.last_kwargs: dict[str, object] = {}

    async def create(self, **kwargs: object) -> object:
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))]
        )


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeOpenAIClient:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.chat = _FakeChat(completions)


def _fake_openai_client(text: str) -> _FakeOpenAIClient:
    return _FakeOpenAIClient(_FakeCompletions(text=text))


def _fake_openai_client_error(error: Exception) -> _FakeOpenAIClient:
    return _FakeOpenAIClient(_FakeCompletions(error=error))


def _openai_status_error(error_cls: type[openai.APIStatusError]) -> openai.APIStatusError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(401, request=request)
    return error_cls("request failed", response=response, body=None)
