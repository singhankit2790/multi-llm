from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from the process environment.

    OS environment variables always override values from a local `.env` file.
    On Render there is usually no `.env`; keys come from the service settings.
    """

    model_config = SettingsConfigDict(
        # Load backend/.env only when that file exists (local development).
        # A missing file is normal in production.
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Multi-LLM Custom ChatGPT"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Provider keys may be empty. The app still starts; providers fail at call time.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    # Required only for organization-scoped Anthropic keys. Leave empty for
    # workspace-scoped keys so no workspace header is sent.
    anthropic_workspace_id: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    llm_timeout_seconds: float = 30.0
    llm_max_output_tokens: int = 2048
    max_prompt_length: int = 8000

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
