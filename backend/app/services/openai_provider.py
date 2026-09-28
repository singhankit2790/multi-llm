from typing import Protocol

import openai

from app.services.base import BaseLLMProvider
from app.services.exceptions import (
    AuthenticationFailureError,
    InvalidRequestError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    UnknownProviderFailureError,
)
from app.services.models import Message


class OpenAICompletionsAPI(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class OpenAIChatAPI(Protocol):
    completions: OpenAICompletionsAPI


class OpenAIClientLike(Protocol):
    chat: OpenAIChatAPI


def to_openai_messages(messages: list[Message]) -> list[dict[str, str]]:
    return [
        {"role": message.role.value, "content": message.content}
        for message in messages
    ]


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    display_name = "OpenAI"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: OpenAIClientLike | None = None,
    ) -> None:
        super().__init__(api_key, model, timeout_seconds, max_output_tokens)
        self._client = client

    def _get_client(self) -> OpenAIClientLike:
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                timeout=self._timeout_seconds,
            )
        return self._client

    async def _complete(self, messages: list[Message]) -> str:
        response = await self._get_client().chat.completions.create(
            model=self._model,
            messages=to_openai_messages(messages),
            timeout=self._timeout_seconds,
        )
        return _extract_openai_text(response)

    def _map_sdk_error(self, exc: BaseException) -> ProviderError:
        if isinstance(exc, openai.AuthenticationError):
            return AuthenticationFailureError("Authentication failed for OpenAI")
        if isinstance(exc, openai.RateLimitError):
            return RateLimitError("OpenAI rate limit exceeded")
        if isinstance(exc, openai.APITimeoutError):
            return ProviderTimeoutError("OpenAI request timed out")
        if isinstance(exc, openai.APIConnectionError):
            return ProviderUnavailableError("OpenAI is unavailable")
        if isinstance(exc, openai.BadRequestError):
            return InvalidRequestError("OpenAI rejected the request")
        return UnknownProviderFailureError("OpenAI request failed")


def _extract_openai_text(response: object) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise InvalidRequestError("OpenAI returned no choices")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if content is None:
        return ""
    if not isinstance(content, str):
        raise InvalidRequestError("OpenAI returned a non-text response")
    return content
