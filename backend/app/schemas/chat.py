from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.services.models import LLMResponse, ProviderName, ResponseStatus


def normalize_prompt(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("prompt must not be empty")
    limit = get_settings().max_prompt_length
    if len(stripped) > limit:
        raise ValueError(f"prompt must be at most {limit} characters")
    return stripped


class CompareRequest(BaseModel):
    """User prompt sent to OpenAI, Claude, and Gemini in parallel."""

    prompt: str = Field(
        ...,
        description="The question to send to all configured LLM providers.",
        examples=["Explain binary search to a beginner"],
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Existing chat session. If omitted, a new session is created. "
            "A supplied ID that does not exist returns HTTP 404."
        ),
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        return normalize_prompt(value)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ComparisonResult(LLMResponse):
    """Normalized result from a single LLM provider."""

    status: ResponseStatus = Field(
        description="success when the provider returned text, otherwise error."
    )


class CompareResponse(BaseModel):
    """Aggregate result of a concurrent multi-LLM comparison."""

    request_id: str = Field(
        description="Unique identifier for this comparison request."
    )
    session_id: str = Field(
        description="Chat session that stores independent provider histories."
    )
    prompt: str = Field(description="The normalized prompt that was compared.")
    results: list[ComparisonResult] = Field(
        description="Provider results in stable order: OpenAI, Claude, Gemini."
    )
    total_latency_ms: int = Field(
        ge=0,
        description=(
            "Wall-clock orchestration time in milliseconds. Because providers "
            "run concurrently, this is close to the slowest provider, not the "
            "sum of individual latencies."
        ),
    )


class ContinueRequest(BaseModel):
    """Follow-up prompt sent to a single selected model."""

    session_id: str = Field(description="Existing chat session.")
    model: ProviderName = Field(
        description="Provider to continue with: openai, claude, or gemini."
    )
    prompt: str = Field(description="Follow-up question for the selected model.")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("session_id must not be empty")
        return stripped

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        return normalize_prompt(value)


class ContinueResponse(BaseModel):
    """Result of continuing a conversation with one model."""

    request_id: str
    session_id: str
    result: ComparisonResult


class CreateSessionResponse(BaseModel):
    session_id: str
    created_at: datetime


class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted: bool = True
