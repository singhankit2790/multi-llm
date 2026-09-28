"""In-memory chat sessions with independent histories per provider.

Sessions live only in this process. They disappear on restart and are not
shared across multiple backend instances. Redis or a database can replace
this module later without changing Message or provider code.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.services.exceptions import SessionNotFoundError, UnknownProviderError
from app.services.models import ChatSession, Message, ProviderName
from app.services.orchestrator import PROVIDER_ORDER

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = {item.value for item in ProviderName}


class SessionManager:
    """Process-local session store. Does not call LLM providers."""

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._store_lock = asyncio.Lock()

    async def create_session(self) -> ChatSession:
        session = ChatSession(
            session_id=str(uuid4()),
            created_at=datetime.now(timezone.utc),
            histories={name: [] for name in PROVIDER_ORDER},
        )
        async with self._store_lock:
            self._sessions[session.session_id] = session
            self._locks[session.session_id] = asyncio.Lock()
        logger.info("Session created session_id=%s", session.session_id)
        return session.model_copy(deep=True)

    async def get_session(self, session_id: str) -> ChatSession:
        async with self._store_lock:
            session = self._require(session_id)
            return session.model_copy(deep=True)

    async def delete_session(self, session_id: str) -> None:
        async with self.hold(session_id):
            async with self._store_lock:
                self._require(session_id)
                del self._sessions[session_id]
                self._locks.pop(session_id, None)
        logger.info("Session deleted session_id=%s", session_id)

    async def get_history(self, session_id: str, provider: str) -> list[Message]:
        key = _provider_key(provider)
        async with self._store_lock:
            session = self._require(session_id)
            return [message.model_copy() for message in session.histories[key]]

    async def append_message(
        self,
        session_id: str,
        provider: str,
        message: Message,
    ) -> None:
        key = _provider_key(provider)
        async with self._store_lock:
            session = self._require(session_id)
            session.histories[key].append(message.model_copy())
        logger.info(
            "Session message appended session_id=%s provider=%s role=%s",
            session_id,
            key,
            message.role.value,
        )

    async def append_user_to_all(
        self,
        session_id: str,
        message: Message,
    ) -> dict[str, list[Message]]:
        """Add one user turn to every provider and return history copies."""
        async with self._store_lock:
            session = self._require(session_id)
            copied = message.model_copy()
            for name in PROVIDER_ORDER:
                session.histories[name].append(copied.model_copy())
            return {
                name: [item.model_copy() for item in history]
                for name, history in session.histories.items()
            }

    @asynccontextmanager
    async def hold(self, session_id: str) -> AsyncIterator[None]:
        """Serialize compare/continue updates for a single session."""
        lock = await self._lock_for(session_id)
        async with lock:
            yield

    async def _lock_for(self, session_id: str) -> asyncio.Lock:
        async with self._store_lock:
            self._require(session_id)
            lock = self._locks.get(session_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[session_id] = lock
            return lock

    def _require(self, session_id: str) -> ChatSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session


def _provider_key(provider: str) -> str:
    key = provider.strip().lower()
    if key not in _VALID_PROVIDERS:
        raise UnknownProviderError(
            f"Unknown provider '{provider}'. Expected one of: openai, claude, gemini"
        )
    return key


_manager = SessionManager()


def get_session_manager() -> SessionManager:
    return _manager


def reset_session_manager() -> SessionManager:
    global _manager
    _manager = SessionManager()
    return _manager
