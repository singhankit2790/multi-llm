from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ProviderName(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"


class Message(BaseModel):
    role: MessageRole
    content: str = Field(min_length=1)


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str | None = None
    status: ResponseStatus
    latency_ms: int = Field(ge=0)
    error: str | None = None


class ComparisonOutcome(BaseModel):
    request_id: str
    prompt: str
    results: list[LLMResponse]
    total_latency_ms: int = Field(ge=0)


class ContinueOutcome(BaseModel):
    request_id: str
    result: LLMResponse


class ChatSession(BaseModel):
    session_id: str
    created_at: datetime
    histories: dict[str, list[Message]]
