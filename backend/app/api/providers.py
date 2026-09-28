"""Provider availability endpoint.

Returns which LLM providers are configured (have non-placeholder API keys)
so the frontend can show only available providers without wasting API calls.
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.providers import ProviderInfo, ProvidersResponse

router = APIRouter(tags=["providers"])

_EXACT_PLACEHOLDERS = {
    "placeholder",
    "changeme",
    "xxx",
    "your_key_here",
    "your_api_key_here",
}


def _is_real_key(key: str) -> bool:
    """Return True when a key is non-empty and not an obvious placeholder."""
    stripped = key.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if lower in _EXACT_PLACEHOLDERS:
        return False
    if "your_" in lower and "_here" in lower:
        return False
    return True


@router.get("/providers", response_model=ProvidersResponse, summary="List configured providers")
def get_providers() -> ProvidersResponse:
    """Return the list of LLM providers that have a real API key configured."""
    s = get_settings()
    providers = [
        ProviderInfo(
            name="openai",
            display_name="OpenAI",
            model=s.openai_model,
            available=_is_real_key(s.openai_api_key),
        ),
        ProviderInfo(
            name="claude",
            display_name="Anthropic Claude",
            model=s.anthropic_model,
            available=_is_real_key(s.anthropic_api_key),
        ),
        ProviderInfo(
            name="gemini",
            display_name="Google Gemini",
            model=s.gemini_model,
            available=_is_real_key(s.gemini_api_key),
        ),
    ]
    return ProvidersResponse(providers=providers)
