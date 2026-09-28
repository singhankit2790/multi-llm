"""Concurrent multi-LLM comparison.

Providers are executed with asyncio.gather so their work overlaps in time.
Total comparison latency is therefore close to the slowest provider, plus a
small amount of orchestration overhead, rather than OpenAI + Claude + Gemini.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol
from uuid import uuid4

from app.services.exceptions import ProviderError
from app.services.factory import get_provider as default_get_provider
from app.services.models import (
    ComparisonOutcome,
    ContinueOutcome,
    LLMResponse,
    Message,
    MessageRole,
    ResponseStatus,
)

logger = logging.getLogger(__name__)

PROVIDER_ORDER: tuple[str, ...] = ("openai", "claude", "gemini")


class LLMProvider(Protocol):
    provider_name: str

    @property
    def model(self) -> str: ...

    async def generate(self, messages: list[Message]) -> LLMResponse: ...


ProviderFactory = Callable[[str], LLMProvider]


class LLMOrchestrator:
    """Fan one prompt out to OpenAI, Claude, and Gemini concurrently."""

    def __init__(
        self,
        provider_factory: ProviderFactory = default_get_provider,
        provider_names: Sequence[str] = PROVIDER_ORDER,
    ) -> None:
        self._provider_factory = provider_factory
        self._provider_names = tuple(provider_names)

    async def compare(self, prompt: str) -> ComparisonOutcome:
        messages = [Message(role=MessageRole.USER, content=prompt)]
        histories = {name: list(messages) for name in self._provider_names}
        return await self.compare_messages(histories, prompt=prompt)

    async def compare_messages(
        self,
        messages_by_provider: Mapping[str, Sequence[Message]],
        *,
        prompt: str,
    ) -> ComparisonOutcome:
        request_id = str(uuid4())
        started = time.perf_counter()
        logger.info(
            "Comparison request started request_id=%s prompt_length=%s providers=%s",
            request_id,
            len(prompt),
            ",".join(self._provider_names),
        )

        providers = [self._provider_factory(name) for name in self._provider_names]
        gathered = await asyncio.gather(
            *[
                self._invoke(
                    request_id,
                    provider,
                    list(messages_by_provider.get(provider.provider_name, ())),
                )
                for provider in providers
            ],
            return_exceptions=True,
        )

        results = [
            self._normalize_result(provider, item)
            for provider, item in zip(providers, gathered, strict=True)
        ]
        total_latency_ms = _elapsed_ms(started)
        logger.info(
            "Comparison request completed request_id=%s total_latency_ms=%s",
            request_id,
            total_latency_ms,
        )
        return ComparisonOutcome(
            request_id=request_id,
            prompt=prompt,
            results=results,
            total_latency_ms=total_latency_ms,
        )

    async def generate_one(
        self,
        provider_name: str,
        messages: Sequence[Message],
    ) -> ContinueOutcome:
        request_id = str(uuid4())
        logger.info(
            "Continuation started request_id=%s provider=%s message_count=%s",
            request_id,
            provider_name,
            len(messages),
        )
        provider = self._provider_factory(provider_name)
        result = await self._invoke(request_id, provider, list(messages))
        normalized = self._normalize_result(provider, result)
        logger.info(
            "Continuation completed request_id=%s provider=%s status=%s latency_ms=%s",
            request_id,
            provider_name,
            normalized.status.value,
            normalized.latency_ms,
        )
        return ContinueOutcome(request_id=request_id, result=normalized)

    async def _invoke(
        self,
        request_id: str,
        provider: LLMProvider,
        messages: list[Message],
    ) -> LLMResponse:
        started = time.perf_counter()
        logger.info(
            "Provider execution started request_id=%s provider=%s",
            request_id,
            provider.provider_name,
        )
        try:
            result = await provider.generate(messages)
            logger.info(
                "Provider execution completed request_id=%s provider=%s status=%s latency_ms=%s",
                request_id,
                provider.provider_name,
                result.status.value,
                result.latency_ms,
            )
            if result.status == ResponseStatus.ERROR:
                logger.warning(
                    "Provider returned error request_id=%s provider=%s",
                    request_id,
                    provider.provider_name,
                )
            return result
        except asyncio.TimeoutError:
            return self._isolated_error(
                request_id,
                provider,
                started,
                category="timeout",
                message=f"{_label(provider)} request timed out",
            )
        except ProviderError as exc:
            return self._isolated_error(
                request_id,
                provider,
                started,
                category=exc.category,
                message=exc.message,
            )

    def _isolated_error(
        self,
        request_id: str,
        provider: LLMProvider,
        started: float,
        category: str,
        message: str,
    ) -> LLMResponse:
        latency_ms = _elapsed_ms(started)
        logger.warning(
            "Provider execution failed request_id=%s provider=%s category=%s latency_ms=%s",
            request_id,
            provider.provider_name,
            category,
            latency_ms,
        )
        return LLMResponse(
            provider=provider.provider_name,
            model=provider.model,
            content=None,
            status=ResponseStatus.ERROR,
            latency_ms=latency_ms,
            error=message,
        )

    def _normalize_result(
        self,
        provider: LLMProvider,
        result: LLMResponse | BaseException,
    ) -> LLMResponse:
        if isinstance(result, LLMResponse):
            return result
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result
        if isinstance(result, asyncio.TimeoutError):
            message = f"{_label(provider)} request timed out"
            category = "timeout"
        elif isinstance(result, ProviderError):
            message = result.message
            category = result.category
        else:
            logger.warning(
                "Unexpected provider exception provider=%s error_type=%s",
                provider.provider_name,
                type(result).__name__,
            )
            message = f"{_label(provider)} request failed"
            category = "unknown"
        logger.warning(
            "Provider gather exception isolated provider=%s category=%s",
            provider.provider_name,
            category,
        )
        return LLMResponse(
            provider=provider.provider_name,
            model=provider.model,
            content=None,
            status=ResponseStatus.ERROR,
            latency_ms=0,
            error=message,
        )


def _label(provider: LLMProvider) -> str:
    display_name = getattr(provider, "display_name", None)
    if isinstance(display_name, str) and display_name:
        return display_name
    return provider.provider_name


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
