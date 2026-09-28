import pytest

from app.services.exceptions import SessionNotFoundError, UnknownProviderError
from app.services.models import Message, MessageRole
from app.services.session_manager import SessionManager


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


@pytest.mark.asyncio
async def test_create_session_has_uuid_and_empty_histories(
    manager: SessionManager,
) -> None:
    session = await manager.create_session()
    assert session.session_id
    assert "-" in session.session_id
    assert session.histories["openai"] == []
    assert session.histories["claude"] == []
    assert session.histories["gemini"] == []


@pytest.mark.asyncio
async def test_session_ids_are_unique(manager: SessionManager) -> None:
    first = await manager.create_session()
    second = await manager.create_session()
    assert first.session_id != second.session_id


@pytest.mark.asyncio
async def test_get_existing_session(manager: SessionManager) -> None:
    created = await manager.create_session()
    loaded = await manager.get_session(created.session_id)
    assert loaded.session_id == created.session_id


@pytest.mark.asyncio
async def test_missing_session_raises(manager: SessionManager) -> None:
    with pytest.raises(SessionNotFoundError):
        await manager.get_session("missing-session")


@pytest.mark.asyncio
async def test_delete_session(manager: SessionManager) -> None:
    created = await manager.create_session()
    await manager.delete_session(created.session_id)
    with pytest.raises(SessionNotFoundError):
        await manager.get_session(created.session_id)


@pytest.mark.asyncio
async def test_delete_missing_session_raises(manager: SessionManager) -> None:
    with pytest.raises(SessionNotFoundError):
        await manager.delete_session("missing-session")


@pytest.mark.asyncio
async def test_append_messages_are_independent(manager: SessionManager) -> None:
    session = await manager.create_session()
    openai_message = Message(role=MessageRole.USER, content="openai only")
    claude_message = Message(role=MessageRole.USER, content="claude only")
    gemini_message = Message(role=MessageRole.USER, content="gemini only")

    await manager.append_message(session.session_id, "openai", openai_message)
    await manager.append_message(session.session_id, "claude", claude_message)
    await manager.append_message(session.session_id, "gemini", gemini_message)

    openai_history = await manager.get_history(session.session_id, "openai")
    claude_history = await manager.get_history(session.session_id, "claude")
    gemini_history = await manager.get_history(session.session_id, "gemini")

    assert [item.content for item in openai_history] == ["openai only"]
    assert [item.content for item in claude_history] == ["claude only"]
    assert [item.content for item in gemini_history] == ["gemini only"]


@pytest.mark.asyncio
async def test_append_claude_does_not_change_other_histories(
    manager: SessionManager,
) -> None:
    session = await manager.create_session()
    await manager.append_message(
        session.session_id,
        "claude",
        Message(role=MessageRole.USER, content="only claude"),
    )
    assert await manager.get_history(session.session_id, "openai") == []
    assert await manager.get_history(session.session_id, "gemini") == []
    claude_history = await manager.get_history(session.session_id, "claude")
    assert len(claude_history) == 1
    assert claude_history[0].content == "only claude"


@pytest.mark.asyncio
async def test_append_unknown_provider_raises(manager: SessionManager) -> None:
    session = await manager.create_session()
    with pytest.raises(UnknownProviderError):
        await manager.append_message(
            session.session_id,
            "unknown",
            Message(role=MessageRole.USER, content="nope"),
        )


@pytest.mark.asyncio
async def test_append_user_to_all(manager: SessionManager) -> None:
    session = await manager.create_session()
    histories = await manager.append_user_to_all(
        session.session_id,
        Message(role=MessageRole.USER, content="shared question"),
    )
    for name in ("openai", "claude", "gemini"):
        assert [item.content for item in histories[name]] == ["shared question"]
