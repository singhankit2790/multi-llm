import pytest

from app.services.models import Message, MessageRole
from app.services.orchestrator import LLMOrchestrator, PROVIDER_ORDER
from tests.test_orchestrator import FakeProvider, _factory_from


@pytest.mark.asyncio
async def test_compare_messages_uses_independent_histories() -> None:
    providers = {name: FakeProvider(name, content=f"{name}-answer") for name in PROVIDER_ORDER}
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    histories = {
        "openai": [
            Message(role=MessageRole.USER, content="Q1"),
            Message(role=MessageRole.ASSISTANT, content="openai-A1"),
            Message(role=MessageRole.USER, content="Q3"),
        ],
        "claude": [
            Message(role=MessageRole.USER, content="Q1"),
            Message(role=MessageRole.ASSISTANT, content="claude-A1"),
            Message(role=MessageRole.USER, content="Q2"),
            Message(role=MessageRole.ASSISTANT, content="claude-A2"),
            Message(role=MessageRole.USER, content="Q3"),
        ],
        "gemini": [
            Message(role=MessageRole.USER, content="Q1"),
            Message(role=MessageRole.ASSISTANT, content="gemini-A1"),
            Message(role=MessageRole.USER, content="Q3"),
        ],
    }

    outcome = await orchestrator.compare_messages(histories, prompt="Q3")
    assert [item.provider for item in outcome.results] == list(PROVIDER_ORDER)
    assert [item.content for item in providers["openai"].calls[-1]] == [
        "Q1",
        "openai-A1",
        "Q3",
    ]
    assert [item.content for item in providers["claude"].calls[-1]] == [
        "Q1",
        "claude-A1",
        "Q2",
        "claude-A2",
        "Q3",
    ]
    assert [item.content for item in providers["gemini"].calls[-1]] == [
        "Q1",
        "gemini-A1",
        "Q3",
    ]


@pytest.mark.asyncio
async def test_generate_one_calls_only_selected_provider() -> None:
    providers = {name: FakeProvider(name, content=f"{name}-answer") for name in PROVIDER_ORDER}
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    messages = [
        Message(role=MessageRole.USER, content="Q1"),
        Message(role=MessageRole.ASSISTANT, content="claude-A1"),
        Message(role=MessageRole.USER, content="Q2"),
    ]
    outcome = await orchestrator.generate_one("claude", messages)

    assert outcome.result.provider == "claude"
    assert outcome.result.content == "claude-answer"
    assert len(providers["claude"].calls) == 1
    assert providers["openai"].calls == []
    assert providers["gemini"].calls == []
    assert [item.content for item in providers["claude"].calls[0]] == [
        "Q1",
        "claude-A1",
        "Q2",
    ]
