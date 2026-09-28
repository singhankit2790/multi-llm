from typing import Protocol

import anthropic

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


class ClaudeMessagesAPI(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class ClaudeClientLike(Protocol):
    messages: ClaudeMessagesAPI


def to_claude_payload(
    messages: list[Message],
) -> tuple[str | None, list[dict[str, str]]]:
    """Split system instructions from user/assistant turns.

    Anthropic expects system text in the top-level `system` parameter,
    not as a message with role="system".
    """
    system_parts = [
        message.content
        for message in messages
        if message.role == MessageRole.SYSTEM
    ]
    conversation = [
        {"role": message.role.value, "content": message.content}
        for message in messages
        if message.role != MessageRole.SYSTEM
    ]
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, conversation


class ClaudeProvider(BaseLLMProvider):
    provider_name = "claude"
    display_name = "Anthropic Claude"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: ClaudeClientLike | None = None,
        workspace_id: str = "",
    ) -> None:
        super().__init__(api_key, model, timeout_seconds, max_output_tokens)
        self._client = client
        self._workspace_id = workspace_id.strip()

    def _get_client(self) -> ClaudeClientLike:
        if self._client is None:
            headers = {}
            if self._workspace_id:
                headers["anthropic-workspace-id"] = self._workspace_id
            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                timeout=self._timeout_seconds,
                default_headers=headers or None,
            )
        return self._client

    async def _complete(self, messages: list[Message]) -> str:
        system_instruction, conversation = to_claude_payload(messages)
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_output_tokens,
            "messages": conversation,
            "timeout": self._timeout_seconds,
        }
        if system_instruction is not None:
            kwargs["system"] = system_instruction
        response = await self._get_client().messages.create(**kwargs)
        return _extract_claude_text(response)

    def _map_sdk_error(self, exc: BaseException) -> ProviderError:
        if isinstance(exc, anthropic.AuthenticationError):
            return AuthenticationFailureError(
                "Authentication failed for Anthropic Claude"
            )
        if isinstance(exc, anthropic.RateLimitError):
            return RateLimitError("Anthropic Claude rate limit exceeded")
        if isinstance(exc, anthropic.APITimeoutError):
            return ProviderTimeoutError("Anthropic Claude request timed out")
        if isinstance(exc, anthropic.APIConnectionError):
            return ProviderUnavailableError("Anthropic Claude is unavailable")
        if isinstance(exc, anthropic.BadRequestError):
            return InvalidRequestError(_safe_claude_request_error(exc))
        return UnknownProviderFailureError("Anthropic Claude request failed")


def _safe_claude_request_error(exc: anthropic.BadRequestError) -> str:
    """Map Anthropic 400 bodies to a secret-free application message."""
    body = getattr(exc, "body", None)
    raw = ""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            raw = str(error.get("message") or "")
    lowered = raw.lower()
    if "not scoped to a workspace" in lowered:
        return (
            "Anthropic Claude rejected the request: this API key is not "
            "scoped to a workspace. Create a workspace-scoped key in the "
            "Anthropic console."
        )
    if "workspace" in lowered and ("not found" in lowered or "invalid" in lowered):
        return (
            "Anthropic Claude rejected the request: the configured "
            "workspace ID is invalid for this key."
        )
    if "model" in lowered:
        return (
            "Anthropic Claude rejected the request: the configured model "
            "is not available for this key."
        )
    return "Anthropic Claude rejected the request"


def _extract_claude_text(response: object) -> str:
    blocks = getattr(response, "content", None)
    if not blocks:
        return ""
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)
