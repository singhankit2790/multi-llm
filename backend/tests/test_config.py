from app.core.config import Settings


def test_cors_origin_list_splits_and_strips() -> None:
    settings = Settings.model_construct(
        cors_origins="http://localhost:5173, https://demo.vercel.app/"
    )
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://demo.vercel.app",
    ]


def test_environment_overrides_default_cors(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.vercel.app")
    settings = Settings(_env_file=None)
    assert settings.cors_origin_list == ["https://app.example.vercel.app"]


def test_empty_anthropic_workspace_id_stays_empty(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_WORKSPACE_ID", "")
    settings = Settings(_env_file=None)
    assert settings.anthropic_workspace_id.strip() == ""
