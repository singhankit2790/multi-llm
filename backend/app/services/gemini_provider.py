from typing import Protocol

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

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
from app.services.models import Message, MessageRole


class GeminiModelsAPI(Protocol):
    async def generate_content(self, **kwargs: object) -> object: ...


class GeminiAsyncAPI(Protocol):
    models: GeminiModelsAPI


class GeminiClientLike(Protocol):
    aio: GeminiAsyncAPI


def to_gemini_payload(
    messages: list[Message],
) -> tuple[str | None, list[dict[str, object]]]:
    """Convert internal messages to Gemini contents plus system instruction.

    Gemini uses role="model" for assistant turns and a separate
    system_instruction field for system prompts.
    """
    system_parts = [
        message.content
        for message in messages
        if message.role == MessageRole.SYSTEM
    ]
    contents: list[dict[str, object]] = []
    for message in messages:
        if message.role == MessageRole.SYSTEM:
            continue
        role = "user" if message.role == MessageRole.USER else "model"
        contents.append(
            {
                "role": role,
                "parts": [{"text": message.content}],
            }
        )
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"
    display_name = "Google Gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: GeminiClientLike | None = None,
    ) -> None:
        super().__init__(api_key, model, timeout_seconds, max_output_tokens)
        self._client = client

    def _get_client(self) -> GeminiClientLike:
        if self._client is None:
            timeout_ms = int(self._timeout_seconds * 1000)
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
        return self._client

    async def _complete(self, messages: list[Message]) -> str:
        system_instruction, contents = to_gemini_payload(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=self._max_output_tokens,
        )
        response = await self._get_client().aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        return _extract_gemini_text(response)

    def _map_sdk_error(self, exc: BaseException) -> ProviderError:
        if isinstance(exc, genai_errors.ClientError):
            code = getattr(exc, "code", None)
            if code in {401, 403}:
                return AuthenticationFailureError(
                    "Authentication failed for Google Gemini"
                )
            if code == 429:
                return RateLimitError("Google Gemini rate limit exceeded")
            if code == 408:
                return ProviderTimeoutError("Google Gemini request timed out")
            if code in {400, 404}:
                return InvalidRequestError("Google Gemini rejected the request")
            return InvalidRequestError("Google Gemini request failed")
        if isinstance(exc, genai_errors.ServerError):
            return ProviderUnavailableError("Google Gemini is unavailable")
        if isinstance(exc, genai_errors.APIError):
            return UnknownProviderFailureError("Google Gemini request failed")
        return UnknownProviderFailureError("Google Gemini request failed")


def _extract_gemini_text(response: object) -> str:
    text = getattr(response, "text", None)
    if text is None:
        return ""
    if not isinstance(text, str):
        raise InvalidRequestError("Google Gemini returned a non-text response")
    return text
