from app.core.config import Settings, get_settings
from app.services.base import BaseLLMProvider
from app.services.claude_provider import ClaudeProvider
from app.services.exceptions import UnknownProviderError
from app.services.gemini_provider import GeminiProvider
from app.services.openai_provider import OpenAIProvider

_PROVIDERS = frozenset({"openai", "claude", "gemini"})


def get_provider(
    name: str,
    settings: Settings | None = None,
) -> BaseLLMProvider:
    """Return a provider implementation by name.

    The factory only constructs providers. Concurrent comparison lives in
    LLMOrchestrator.
    """
    resolved = settings or get_settings()
    key = name.strip().lower()
    if key not in _PROVIDERS:
        raise UnknownProviderError(
            f"Unknown provider '{name}'. Expected one of: openai, claude, gemini"
        )
    if key == "openai":
        return OpenAIProvider(
            api_key=resolved.openai_api_key,
            model=resolved.openai_model,
            timeout_seconds=resolved.llm_timeout_seconds,
            max_output_tokens=resolved.llm_max_output_tokens,
        )
    if key == "claude":
        return ClaudeProvider(
            api_key=resolved.anthropic_api_key,
            model=resolved.anthropic_model,
            timeout_seconds=resolved.llm_timeout_seconds,
            max_output_tokens=resolved.llm_max_output_tokens,
            workspace_id=resolved.anthropic_workspace_id,
        )
    return GeminiProvider(
        api_key=resolved.gemini_api_key,
        model=resolved.gemini_model,
        timeout_seconds=resolved.llm_timeout_seconds,
        max_output_tokens=resolved.llm_max_output_tokens,
    )
