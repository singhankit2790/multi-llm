from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_orchestrator
from app.core.config import get_settings
from app.main import app
from app.services.exceptions import ProviderTimeoutError
from app.services.models import MessageRole
from app.services.orchestrator import LLMOrchestrator
from app.services.session_manager import SessionManager, get_session_manager
from tests.test_orchestrator import FakeProvider, _factory_from


@pytest.fixture
def session_manager() -> SessionManager:
    return SessionManager()


@pytest.fixture
def providers() -> dict[str, FakeProvider]:
    return {
        "openai": FakeProvider("openai", model="gpt-4o-mini", content="openai-answer"),
        "claude": FakeProvider(
            "claude", model="claude-sonnet-4-5", content="claude-answer"
        ),
        "gemini": FakeProvider(
            "gemini", model="gemini-3.8-flash", content="gemini-answer"
        ),
    }


@pytest.fixture
def client(
    session_manager: SessionManager,
    providers: dict[str, FakeProvider],
) -> Iterator[TestClient]:
    orchestrator = LLMOrchestrator(provider_factory=_factory_from(providers))
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_session_manager] = lambda: session_manager
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _history_contents(
    session_manager: SessionManager,
    session_id: str,
    provider: str,
) -> list[tuple[str, str]]:
    session = session_manager._sessions[session_id]
    return [(item.role.value, item.content) for item in session.histories[provider]]


def test_compare_valid_prompt_returns_structured_success(client: TestClient) -> None:
    response = client.post(
        "/api/chat/compare",
        json={"prompt": "What is a binary tree?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt"] == "What is a binary tree?"
    assert payload["request_id"]
    assert payload["session_id"]
    assert payload["total_latency_ms"] >= 0
    assert len(payload["results"]) == 3
    assert [item["provider"] for item in payload["results"]] == [
        "openai",
        "claude",
        "gemini",
    ]
    assert payload["results"][0]["content"] == "openai-answer"
    assert payload["results"][1]["content"] == "claude-answer"
    assert payload["results"][2]["content"] == "gemini-answer"
    assert all(item["status"] == "success" for item in payload["results"])
    assert all(item["error"] is None for item in payload["results"])
    assert "OPENAI_API_KEY" not in response.text


def test_compare_creates_session_when_omitted(
    client: TestClient,
    session_manager: SessionManager,
) -> None:
    response = client.post("/api/chat/compare", json={"prompt": "Explain recursion"})
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    for provider in ("openai", "claude", "gemini"):
        assert _history_contents(session_manager, session_id, provider) == [
            (MessageRole.USER.value, "Explain recursion"),
            (MessageRole.ASSISTANT.value, f"{provider}-answer"),
        ]


def test_compare_trims_prompt(client: TestClient) -> None:
    response = client.post(
        "/api/chat/compare",
        json={"prompt": "  Explain recursion simply  "},
    )
    assert response.status_code == 200
    assert response.json()["prompt"] == "Explain recursion simply"


def test_compare_partial_provider_failure_returns_http_200(
    session_manager: SessionManager,
) -> None:
    providers = {
        "openai": FakeProvider("openai", content="openai-ok"),
        "claude": FakeProvider(
            "claude",
            raise_exc=ProviderTimeoutError("Anthropic Claude request timed out"),
        ),
        "gemini": FakeProvider("gemini", content="gemini-ok"),
    }
    app.dependency_overrides[get_orchestrator] = lambda: LLMOrchestrator(
        provider_factory=_factory_from(providers)
    )
    app.dependency_overrides[get_session_manager] = lambda: session_manager
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat/compare",
                json={"prompt": "Explain hashing"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    session_id = payload["session_id"]
    assert payload["results"][0]["status"] == "success"
    assert payload["results"][1]["status"] == "error"
    assert payload["results"][1]["content"] is None
    assert payload["results"][1]["error"] == "Anthropic Claude request timed out"
    assert payload["results"][2]["status"] == "success"
    assert _history_contents(session_manager, session_id, "openai") == [
        ("user", "Explain hashing"),
        ("assistant", "openai-ok"),
    ]
    assert _history_contents(session_manager, session_id, "claude") == [
        ("user", "Explain hashing"),
    ]
    assert _history_contents(session_manager, session_id, "gemini") == [
        ("user", "Explain hashing"),
        ("assistant", "gemini-ok"),
    ]


def test_compare_empty_prompt_is_rejected(client: TestClient) -> None:
    response = client.post("/api/chat/compare", json={"prompt": ""})
    assert response.status_code == 422


def test_compare_whitespace_only_prompt_is_rejected(client: TestClient) -> None:
    response = client.post("/api/chat/compare", json={"prompt": "   \n\t  "})
    assert response.status_code == 422


def test_compare_missing_prompt_is_rejected(client: TestClient) -> None:
    response = client.post("/api/chat/compare", json={})
    assert response.status_code == 422


def test_compare_wrong_prompt_type_is_rejected(client: TestClient) -> None:
    response = client.post("/api/chat/compare", json={"prompt": 123})
    assert response.status_code == 422


def test_compare_excessively_long_prompt_is_rejected(client: TestClient) -> None:
    too_long = "a" * (get_settings().max_prompt_length + 1)
    response = client.post("/api/chat/compare", json={"prompt": too_long})
    assert response.status_code == 422


def test_compare_missing_keys_return_structured_errors(
    session_manager: SessionManager,
) -> None:
    from app.core.config import Settings
    from app.services.factory import get_provider

    settings = Settings.model_construct(
        openai_api_key="",
        openai_model="gpt-4o-mini",
        anthropic_api_key="",
        anthropic_model="claude-sonnet-4-5",
        gemini_api_key="",
        gemini_model="gemini-3.8-flash",
        llm_timeout_seconds=30.0,
        llm_max_output_tokens=256,
    )

    app.dependency_overrides[get_orchestrator] = lambda: LLMOrchestrator(
        provider_factory=lambda name: get_provider(name, settings)
    )
    app.dependency_overrides[get_session_manager] = lambda: session_manager
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/chat/compare",
                json={"prompt": "Explain recursion in simple terms."},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert all(item["status"] == "error" for item in payload["results"])
    assert all(item["content"] is None for item in payload["results"])
    session_id = payload["session_id"]
    for provider in ("openai", "claude", "gemini"):
        assert _history_contents(session_manager, session_id, provider) == [
            ("user", "Explain recursion in simple terms."),
        ]


def test_openapi_includes_expected_routes(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "post" in paths["/api/chat/compare"]
    assert "post" in paths["/api/chat/continue"]
    assert "post" in paths["/api/session"]
    assert "delete" in paths["/api/session/{session_id}"]


def test_create_and_delete_session(client: TestClient) -> None:
    created = client.post("/api/session")
    assert created.status_code == 201
    session_id = created.json()["session_id"]
    assert created.json()["created_at"]
    deleted = client.delete(f"/api/session/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    follow_up = client.post(
        "/api/chat/continue",
        json={"session_id": session_id, "model": "claude", "prompt": "Hello"},
    )
    assert follow_up.status_code == 404


def test_compare_invalid_session_id_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/chat/compare",
        json={"prompt": "Hello", "session_id": "missing-session"},
    )
    assert response.status_code == 404


def test_continue_invalid_session_id_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/chat/continue",
        json={
            "session_id": "missing-session",
            "model": "claude",
            "prompt": "Hello",
        },
    )
    assert response.status_code == 404


def test_continue_rejects_invalid_model(client: TestClient) -> None:
    session_id = client.post("/api/session").json()["session_id"]
    response = client.post(
        "/api/chat/continue",
        json={"session_id": session_id, "model": "gpt", "prompt": "Hello"},
    )
    assert response.status_code == 422


def test_continue_invokes_only_selected_provider(
    client: TestClient,
    providers: dict[str, FakeProvider],
    session_manager: SessionManager,
) -> None:
    compare = client.post("/api/chat/compare", json={"prompt": "What is recursion?"})
    session_id = compare.json()["session_id"]
    for provider in providers.values():
        provider.calls.clear()

    response = client.post(
        "/api/chat/continue",
        json={
            "session_id": session_id,
            "model": "claude",
            "prompt": "Give a C++ example.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["result"]["provider"] == "claude"
    assert payload["result"]["content"] == "claude-answer"
    assert "results" not in payload
    assert len(providers["claude"].calls) == 1
    assert providers["openai"].calls == []
    assert providers["gemini"].calls == []
    assert [item.content for item in providers["claude"].calls[0]] == [
        "What is recursion?",
        "claude-answer",
        "Give a C++ example.",
    ]
    assert "openai-answer" not in [
        item.content for item in providers["claude"].calls[0]
    ]
    assert "gemini-answer" not in [
        item.content for item in providers["claude"].calls[0]
    ]
    assert _history_contents(session_manager, session_id, "openai") == [
        ("user", "What is recursion?"),
        ("assistant", "openai-answer"),
    ]
    assert _history_contents(session_manager, session_id, "claude") == [
        ("user", "What is recursion?"),
        ("assistant", "claude-answer"),
        ("user", "Give a C++ example."),
        ("assistant", "claude-answer"),
    ]
    assert _history_contents(session_manager, session_id, "gemini") == [
        ("user", "What is recursion?"),
        ("assistant", "gemini-answer"),
    ]


def test_continue_failure_keeps_user_message_and_other_histories(
    session_manager: SessionManager,
) -> None:
    providers = {
        "openai": FakeProvider("openai", content="openai-ok"),
        "claude": FakeProvider("claude", content="claude-ok"),
        "gemini": FakeProvider("gemini", content="gemini-ok"),
    }
    app.dependency_overrides[get_orchestrator] = lambda: LLMOrchestrator(
        provider_factory=_factory_from(providers)
    )
    app.dependency_overrides[get_session_manager] = lambda: session_manager
    try:
        with TestClient(app) as client:
            session_id = client.post(
                "/api/chat/compare", json={"prompt": "What is recursion?"}
            ).json()["session_id"]
            providers["claude"] = FakeProvider(
                "claude", error="Anthropic Claude rate limit exceeded"
            )
            app.dependency_overrides[get_orchestrator] = lambda: LLMOrchestrator(
                provider_factory=_factory_from(providers)
            )
            response = client.post(
                "/api/chat/continue",
                json={
                    "session_id": session_id,
                    "model": "claude",
                    "prompt": "Give a C++ example.",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"] == "error"
    assert payload["result"]["content"] is None
    assert _history_contents(session_manager, session_id, "claude") == [
        ("user", "What is recursion?"),
        ("assistant", "claude-ok"),
        ("user", "Give a C++ example."),
    ]
    assert _history_contents(session_manager, session_id, "openai") == [
        ("user", "What is recursion?"),
        ("assistant", "openai-ok"),
    ]
    assert _history_contents(session_manager, session_id, "gemini") == [
        ("user", "What is recursion?"),
        ("assistant", "gemini-ok"),
    ]


def test_compare_after_continue_uses_divergent_histories(
    client: TestClient,
    providers: dict[str, FakeProvider],
    session_manager: SessionManager,
) -> None:
    session_id = client.post(
        "/api/chat/compare", json={"prompt": "What is recursion?"}
    ).json()["session_id"]
    client.post(
        "/api/chat/continue",
        json={
            "session_id": session_id,
            "model": "claude",
            "prompt": "Give a C++ example.",
        },
    )
    for provider in providers.values():
        provider.calls.clear()

    response = client.post(
        "/api/chat/compare",
        json={
            "session_id": session_id,
            "prompt": "What are the common mistakes?",
        },
    )
    assert response.status_code == 200
    assert [item.content for item in providers["openai"].calls[-1]] == [
        "What is recursion?",
        "openai-answer",
        "What are the common mistakes?",
    ]
    assert [item.content for item in providers["claude"].calls[-1]] == [
        "What is recursion?",
        "claude-answer",
        "Give a C++ example.",
        "claude-answer",
        "What are the common mistakes?",
    ]
    assert [item.content for item in providers["gemini"].calls[-1]] == [
        "What is recursion?",
        "gemini-answer",
        "What are the common mistakes?",
    ]
    assert _history_contents(session_manager, session_id, "openai")[-2:] == [
        ("user", "What are the common mistakes?"),
        ("assistant", "openai-answer"),
    ]


def test_compare_existing_session_second_turn(
    client: TestClient,
    providers: dict[str, FakeProvider],
) -> None:
    created = client.post("/api/session")
    session_id = created.json()["session_id"]
    client.post(
        "/api/chat/compare",
        json={"prompt": "Q1", "session_id": session_id},
    )
    for provider in providers.values():
        provider.calls.clear()
    response = client.post(
        "/api/chat/compare",
        json={"prompt": "Q2", "session_id": session_id},
    )
    assert response.status_code == 200
    for name in ("openai", "claude", "gemini"):
        assert [item.content for item in providers[name].calls[-1]] == [
            "Q1",
            f"{name}-answer",
            "Q2",
        ]


def test_delete_missing_session_returns_404(client: TestClient) -> None:
    response = client.delete("/api/session/missing-session")
    assert response.status_code == 404
