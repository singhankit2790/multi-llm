import asyncio
import time
from collections.abc import Callable

import pytest

from app.services.exceptions import RateLimitError
from app.services.models import LLMResponse, Message, MessageRole, ResponseStatus
from app.services.orchestrator import LLMOrchestrator, PROVIDER_ORDER


class FakeProvider:
    def __init__(
        self,
        name: str,
        model: str = "fake-model",
        *,
        delay_s: float = 0.0,
        content: str | None = "ok",
        error: str | None = None,
        raise_exc: BaseException | None = None,
        started_events: dict[str, asyncio.Event] | None = None,
        completion_log: list[str] | None = None,
    ) -> None:
        self.provider_name = name
        self.display_name = {
            "openai": "OpenAI",
            "claude": "Anthropic Claude",
            "gemini": "Google Gemini",
        }.get(name, name)
        self._model = model
        self._delay_s = delay_s
        self._content = content
        self._error = error
        self._raise_exc = raise_exc
        self._started_events = started_events
        self._completion_log = completion_log
        self.calls: list[list[Message]] = []

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, messages: list[Message]) -> LLMResponse:
        started = time.perf_counter()
        self.calls.append([message.model_copy() for message in messages])
        assert messages[-1].role == MessageRole.USER
        if self._started_events is not None:
            self._started_events[self.provider_name].set()
            await asyncio.wait_for(
                asyncio.gather(
                    *[event.wait() for event in self._started_events.values()]
                ),
                timeout=1.0,
            )
        if self._delay_s:
            await asyncio.sleep(self._delay_s)
        if self._completion_log is not None:
            self._completion_log.append(self.provider_name)
        if self._raise_exc is not None:
            raise self._raise_exc
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        if self._error is not None:
            return LLMResponse(
                provider=self.provider_name,
                model=self._model,
                content=None,
                status=ResponseStatus.ERROR,
                latency_ms=latency_ms,
                error=self._error,
            )
        return LLMResponse(
            provider=self.provider_name,
            model=self._model,
            content=self._content,
            status=ResponseStatus.SUCCESS,
            latency_ms=latency_ms,
            error=None,
        )


def _factory_from(
    providers: dict[str, FakeProvider],
) -> Callable[[str], FakeProvider]:
    def factory(name: str) -> FakeProvider:
        return providers[name]

    return factory


@pytest.mark.asyncio
async def test_providers_execute_concurrently() -> None:
    started_events = {
        "openai": asyncio.Event(),
        "claude": asyncio.Event(),
        "gemini": asyncio.Event(),
    }
    providers = {
        name: FakeProvider(name, delay_s=0.05, started_events=started_events)
        for name in PROVIDER_ORDER
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))

    started = time.perf_counter()
    response = await orchestrator.compare("Explain recursion")
    elapsed_s = time.perf_counter() - started

    assert all(event.is_set() for event in started_events.values())
    assert elapsed_s < 0.2
    assert len(response.results) == 3
    assert [item.provider for item in response.results] == list(PROVIDER_ORDER)


@pytest.mark.asyncio
async def test_provider_error_is_isolated() -> None:
    providers = {
        "openai": FakeProvider("openai", content="openai-ok"),
        "claude": FakeProvider(
            "claude",
            raise_exc=RateLimitError("Anthropic Claude rate limit exceeded"),
        ),
        "gemini": FakeProvider("gemini", content="gemini-ok"),
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    response = await orchestrator.compare("What is a binary tree?")

    assert [item.provider for item in response.results] == list(PROVIDER_ORDER)
    assert response.results[0].status == ResponseStatus.SUCCESS
    assert response.results[0].content == "openai-ok"
    assert response.results[1].status == ResponseStatus.ERROR
    assert response.results[1].content is None
    assert response.results[1].error == "Anthropic Claude rate limit exceeded"
    assert response.results[2].status == ResponseStatus.SUCCESS
    assert response.results[2].content == "gemini-ok"


@pytest.mark.asyncio
async def test_timeout_is_isolated() -> None:
    providers = {
        "openai": FakeProvider("openai", raise_exc=asyncio.TimeoutError()),
        "claude": FakeProvider("claude", content="claude-ok"),
        "gemini": FakeProvider("gemini", content="gemini-ok"),
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    response = await orchestrator.compare("Explain hashing")

    assert response.results[0].status == ResponseStatus.ERROR
    assert response.results[0].error == "OpenAI request timed out"
    assert response.results[1].status == ResponseStatus.SUCCESS
    assert response.results[2].status == ResponseStatus.SUCCESS


@pytest.mark.asyncio
async def test_all_providers_fail_still_returns_comparison() -> None:
    providers = {
        "openai": FakeProvider("openai", error="OpenAI API key is not configured"),
        "claude": FakeProvider(
            "claude", error="Anthropic Claude API key is not configured"
        ),
        "gemini": FakeProvider(
            "gemini", error="Google Gemini API key is not configured"
        ),
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    response = await orchestrator.compare("Hello")

    assert len(response.results) == 3
    assert all(item.status == ResponseStatus.ERROR for item in response.results)
    assert all(item.content is None for item in response.results)
    assert "ok" not in " ".join(item.error or "" for item in response.results).lower()


@pytest.mark.asyncio
async def test_results_keep_stable_order_regardless_of_completion() -> None:
    completion_log: list[str] = []
    providers = {
        "openai": FakeProvider(
            "openai", delay_s=0.08, content="openai", completion_log=completion_log
        ),
        "claude": FakeProvider(
            "claude", delay_s=0.04, content="claude", completion_log=completion_log
        ),
        "gemini": FakeProvider(
            "gemini", delay_s=0.01, content="gemini", completion_log=completion_log
        ),
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    response = await orchestrator.compare("Order test")

    assert completion_log == ["gemini", "claude", "openai"]
    assert [item.provider for item in response.results] == [
        "openai",
        "claude",
        "gemini",
    ]


@pytest.mark.asyncio
async def test_total_latency_is_wall_clock_not_sum() -> None:
    delay_s = 0.15
    providers = {
        name: FakeProvider(name, delay_s=delay_s, content=name) for name in PROVIDER_ORDER
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    response = await orchestrator.compare("Latency test")

    individual_sum = sum(item.latency_ms for item in response.results)
    assert individual_sum >= int(delay_s * 3 * 1000 * 0.5)
    assert response.total_latency_ms < individual_sum
    assert response.total_latency_ms < int(delay_s * 3 * 1000 * 0.8)
    assert response.total_latency_ms >= int(delay_s * 1000 * 0.5)


@pytest.mark.asyncio
async def test_compare_response_includes_request_id_and_prompt() -> None:
    providers = {
        name: FakeProvider(name, content=name) for name in PROVIDER_ORDER
    }
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    response = await orchestrator.compare("  What is a binary tree?  ".strip())

    assert response.request_id
    assert "-" in response.request_id
    assert response.prompt == "What is a binary tree?"
    assert response.total_latency_ms >= 0
