import inspect

import pytest
from pydantic import ValidationError

from app.services.base import BaseLLMProvider
from app.services.claude_provider import ClaudeProvider
from app.services.exceptions import UnknownProviderError
from app.services.factory import get_provider
from app.services.gemini_provider import GeminiProvider
from app.services.models import LLMResponse, Message, MessageRole, ResponseStatus
from app.services.openai_provider import OpenAIProvider


def test_message_requires_known_role() -> None:
    with pytest.raises(ValidationError):
        Message(role="narrator", content="Hello")  # type: ignore[arg-type]


def test_message_requires_non_empty_content() -> None:
    with pytest.raises(ValidationError):
        Message(role=MessageRole.USER, content="")


def test_llm_response_success_shape() -> None:
    response = LLMResponse(
        provider="openai",
        model="gpt-4o-mini",
        content="Hello",
        status=ResponseStatus.SUCCESS,
        latency_ms=12,
        error=None,
    )
    assert response.model_dump() == {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "content": "Hello",
        "status": ResponseStatus.SUCCESS,
        "latency_ms": 12,
        "error": None,
    }


def test_llm_response_error_shape() -> None:
    response = LLMResponse(
        provider="claude",
        model="claude-sonnet-4-5",
        content=None,
        status=ResponseStatus.ERROR,
        latency_ms=8,
        error="Anthropic Claude API key is not configured",
    )
    dumped = response.model_dump()
    assert dumped["content"] is None
    assert dumped["status"] == ResponseStatus.ERROR
    assert dumped["error"] is not None


def test_providers_share_async_generate_interface() -> None:
    for provider_cls in (OpenAIProvider, ClaudeProvider, GeminiProvider):
        assert issubclass(provider_cls, BaseLLMProvider)
        assert inspect.iscoroutinefunction(provider_cls.generate)


def test_factory_returns_expected_providers() -> None:
    settings = _test_settings()
    assert isinstance(get_provider("openai", settings), OpenAIProvider)
    assert isinstance(get_provider("claude", settings), ClaudeProvider)
    assert isinstance(get_provider("gemini", settings), GeminiProvider)


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(UnknownProviderError, match="Unknown provider"):
        get_provider("unknown", _test_settings())


def _test_settings():  # type: ignore[no-untyped-def]
    from app.core.config import Settings

    return Settings.model_construct(
        openai_api_key="test-openai",
        openai_model="gpt-4o-mini",
        anthropic_api_key="test-anthropic",
        anthropic_model="claude-sonnet-4-5",
        gemini_api_key="test-gemini",
        gemini_model="gemini-3.8-flash",
        llm_timeout_seconds=30.0,
        llm_max_output_tokens=2048,
    )
