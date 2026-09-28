import asyncio
import logging
import time
from abc import ABC, abstractmethod

from app.services.exceptions import (
    InvalidRequestError,
    MissingAPIKeyError,
    ProviderError,
    ProviderTimeoutError,
)
from app.services.models import LLMResponse, Message, MessageRole, ResponseStatus

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Common async interface for all LLM providers."""

    provider_name: str
    display_name: str

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, messages: list[Message]) -> LLMResponse:
        started = time.perf_counter()
        logger.info(
            "Provider request started provider=%s model=%s message_count=%s",
            self.provider_name,
            self._model,
            len(messages),
        )
        try:
            self._validate_messages(messages)
            self._require_api_key()
            content = await asyncio.wait_for(
                self._complete(messages),
                timeout=self._timeout_seconds,
            )
            latency_ms = _elapsed_ms(started)
            logger.info(
                "Provider request completed provider=%s model=%s latency_ms=%s",
                self.provider_name,
                self._model,
                latency_ms,
            )
            return LLMResponse(
                provider=self.provider_name,
                model=self._model,
                content=content,
                status=ResponseStatus.SUCCESS,
                latency_ms=latency_ms,
                error=None,
            )
        except ProviderError as exc:
            return self._failure_response(started, exc)
        except asyncio.TimeoutError:
            return self._failure_response(
                started,
                ProviderTimeoutError(f"{self.display_name} request timed out"),
            )
        except Exception as exc:
            return self._failure_response(started, self._map_sdk_error(exc))

    def _require_api_key(self) -> None:
        if not self._api_key.strip():
            raise MissingAPIKeyError(
                f"{self.display_name} API key is not configured"
            )

    def _validate_messages(self, messages: list[Message]) -> None:
        if not messages:
            raise InvalidRequestError("At least one message is required")
        if not any(message.role == MessageRole.USER for message in messages):
            raise InvalidRequestError("At least one user message is required")

    def _failure_response(
        self,
        started: float,
        error: ProviderError,
    ) -> LLMResponse:
        latency_ms = _elapsed_ms(started)
        logger.warning(
            "Provider request failed provider=%s model=%s category=%s latency_ms=%s",
            self.provider_name,
            self._model,
            error.category,
            latency_ms,
        )
        return LLMResponse(
            provider=self.provider_name,
            model=self._model,
            content=None,
            status=ResponseStatus.ERROR,
            latency_ms=latency_ms,
            error=error.message,
        )

    @abstractmethod
    async def _complete(self, messages: list[Message]) -> str:
        """Call the vendor SDK and return generated text."""

    @abstractmethod
    def _map_sdk_error(self, exc: BaseException) -> ProviderError:
        """Convert a vendor SDK exception into a safe application error."""


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
