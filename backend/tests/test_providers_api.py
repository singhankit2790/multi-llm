"""Tests for the /api/providers endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_settings(monkeypatch: pytest.MonkeyPatch, **kwargs: str) -> None:
    """Patch get_settings() to return a Settings with the given field overrides."""
    defaults = dict(
        openai_api_key="",
        openai_model="gpt-4o-mini",
        anthropic_api_key="",
        anthropic_model="claude-sonnet-4-5",
        gemini_api_key="",
        gemini_model="gemini-3.8-flash",
        app_name="Test",
        app_version="0.0.0",
        api_prefix="/api",
        cors_origins="http://localhost:5173",
        llm_timeout_seconds=30.0,
        llm_max_output_tokens=256,
        max_prompt_length=8000,
    )
    defaults.update(kwargs)
    fake = Settings.model_construct(**defaults)
    monkeypatch.setattr("app.api.providers.get_settings", lambda: fake)


# ---------------------------------------------------------------------------
# Endpoint shape
# ---------------------------------------------------------------------------

def test_providers_returns_200(client: TestClient) -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200


def test_providers_returns_three_entries(client: TestClient) -> None:
    response = client.get("/api/providers")
    payload = response.json()
    assert "providers" in payload
    assert len(payload["providers"]) == 3


def test_providers_entries_have_required_fields(client: TestClient) -> None:
    providers = client.get("/api/providers").json()["providers"]
    for entry in providers:
        assert "name" in entry
        assert "display_name" in entry
        assert "model" in entry
        assert "available" in entry
        assert isinstance(entry["available"], bool)


def test_providers_stable_order(client: TestClient) -> None:
    names = [p["name"] for p in client.get("/api/providers").json()["providers"]]
    assert names == ["openai", "claude", "gemini"]


# ---------------------------------------------------------------------------
# available=false when keys are empty or placeholders
# ---------------------------------------------------------------------------

def test_all_unavailable_with_empty_keys(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    _override_settings(monkeypatch)
    providers = client.get("/api/providers").json()["providers"]
    assert all(not p["available"] for p in providers)


@pytest.mark.parametrize("placeholder", [
    "your_openai_api_key_here",
    "your_gemini_api_key_here",
    "placeholder",
    "changeme",
    "xxx",
    "YOUR_KEY_HERE",
    "PLACEHOLDER",
])
def test_placeholder_key_is_not_available(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, placeholder: str
) -> None:
    _override_settings(monkeypatch, openai_api_key=placeholder)
    providers = client.get("/api/providers").json()["providers"]
    openai_entry = next(p for p in providers if p["name"] == "openai")
    assert openai_entry["available"] is False


# ---------------------------------------------------------------------------
# available=true when real keys are present
# ---------------------------------------------------------------------------

def test_real_gemini_key_marks_gemini_available(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    _override_settings(monkeypatch, gemini_api_key="AIzaSyFakeButRealLookingKey12345")
    providers = client.get("/api/providers").json()["providers"]
    gemini = next(p for p in providers if p["name"] == "gemini")
    openai = next(p for p in providers if p["name"] == "openai")
    claude = next(p for p in providers if p["name"] == "claude")
    assert gemini["available"] is True
    assert openai["available"] is False
    assert claude["available"] is False


def test_real_openai_key_marks_openai_available(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    _override_settings(monkeypatch, openai_api_key="sk-proj-FakeButRealLookingKey12345")
    providers = client.get("/api/providers").json()["providers"]
    openai = next(p for p in providers if p["name"] == "openai")
    assert openai["available"] is True


def test_all_real_keys_all_available(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    _override_settings(
        monkeypatch,
        openai_api_key="sk-proj-FakeOpenAIKey",
        anthropic_api_key="sk-ant-FakeAnthropicKey",
        gemini_api_key="AIzaSyFakeGeminiKey",
    )
    providers = client.get("/api/providers").json()["providers"]
    assert all(p["available"] for p in providers)


# ---------------------------------------------------------------------------
# Model names are reflected correctly
# ---------------------------------------------------------------------------

def test_model_names_match_config(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    _override_settings(
        monkeypatch,
        openai_model="gpt-4o",
        anthropic_model="claude-opus-4-5",
        gemini_model="gemini-1.5-pro",
    )
    providers = client.get("/api/providers").json()["providers"]
    by_name = {p["name"]: p for p in providers}
    assert by_name["openai"]["model"] == "gpt-4o"
    assert by_name["claude"]["model"] == "claude-opus-4-5"
    assert by_name["gemini"]["model"] == "gemini-1.5-pro"


# ---------------------------------------------------------------------------
# No providers configured → compare returns 400
# ---------------------------------------------------------------------------

def test_compare_returns_400_when_no_providers_configured(client: TestClient) -> None:
    """When get_orchestrator() is NOT overridden and no keys are set, compare must 400."""
    from app.api.chat import get_orchestrator
    from app.services.orchestrator import LLMOrchestrator

    # Override orchestrator to have zero providers (simulates no keys)
    app.dependency_overrides[get_orchestrator] = lambda: LLMOrchestrator(
        provider_names=[]
    )
    try:
        response = client.post(
            "/api/chat/compare", json={"prompt": "Hello"}
        )
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)

    assert response.status_code == 400
    assert "No LLM providers" in response.json()["detail"]
