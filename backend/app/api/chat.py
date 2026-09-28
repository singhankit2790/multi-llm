from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat import (
    CompareRequest,
    CompareResponse,
    ComparisonResult,
    ContinueRequest,
    ContinueResponse,
)
from app.services.models import LLMResponse, Message, MessageRole, ResponseStatus
from app.services.orchestrator import LLMOrchestrator
from app.services.session_manager import SessionManager, get_session_manager

router = APIRouter(prefix="/chat", tags=["chat"])


def get_orchestrator() -> LLMOrchestrator:
    """Always compare OpenAI, Claude, and Gemini. Missing keys become card errors."""
    return LLMOrchestrator()


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Compare LLM responses",
    description=(
        "Send one prompt to all configured LLM providers at the same time. "
        "Each provider receives only its own session history. "
        "If session_id is omitted, a new session is created. "
        "The comparison request returns HTTP 200 even if individual providers fail."
    ),
)
async def compare_prompt(
    payload: CompareRequest,
    orchestrator: LLMOrchestrator = Depends(get_orchestrator),
    sessions: SessionManager = Depends(get_session_manager),
) -> CompareResponse:
    # Guard: orchestrator has no providers (works under both real config and test DI)
    if not orchestrator._provider_names:
        raise HTTPException(
            status_code=400,
            detail="No LLM providers are configured. Add at least one API key to backend/.env.",
        )

    if payload.session_id is None:
        session = await sessions.create_session()
        session_id = session.session_id
    else:
        session_id = payload.session_id

    user_message = Message(role=MessageRole.USER, content=payload.prompt)
    async with sessions.hold(session_id):
        histories = await sessions.append_user_to_all(session_id, user_message)
        outcome = await orchestrator.compare_messages(
            histories,
            prompt=payload.prompt,
        )
        for result in outcome.results:
            assistant = _assistant_message(result)
            if assistant is not None:
                await sessions.append_message(session_id, result.provider, assistant)

    return CompareResponse(
        request_id=outcome.request_id,
        session_id=session_id,
        prompt=outcome.prompt,
        results=[
            ComparisonResult.model_validate(item.model_dump())
            for item in outcome.results
        ],
        total_latency_ms=outcome.total_latency_ms,
    )


@router.post(
    "/continue",
    response_model=ContinueResponse,
    summary="Continue with one model",
    description=(
        "Send a follow-up prompt to a single provider using only that "
        "provider's conversation history. Provider histories stay independent."
    ),
)
async def continue_prompt(
    payload: ContinueRequest,
    orchestrator: LLMOrchestrator = Depends(get_orchestrator),
    sessions: SessionManager = Depends(get_session_manager),
) -> ContinueResponse:
    provider_name = payload.model.value
    # Guard: check the orchestrator's own provider list (works with test DI overrides)
    if orchestrator._provider_names and provider_name not in orchestrator._provider_names:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider_name}' is not configured. Add its API key to backend/.env.",
        )
    user_message = Message(role=MessageRole.USER, content=payload.prompt)
    async with sessions.hold(payload.session_id):
        await sessions.append_message(payload.session_id, provider_name, user_message)
        history = await sessions.get_history(payload.session_id, provider_name)
        outcome = await orchestrator.generate_one(provider_name, history)
        assistant = _assistant_message(outcome.result)
        if assistant is not None:
            await sessions.append_message(
                payload.session_id,
                provider_name,
                assistant,
            )

    return ContinueResponse(
        request_id=outcome.request_id,
        session_id=payload.session_id,
        result=ComparisonResult.model_validate(outcome.result.model_dump()),
    )


def _assistant_message(result: LLMResponse) -> Message | None:
    if result.status != ResponseStatus.SUCCESS:
        return None
    if not result.content or not result.content.strip():
        return None
    return Message(role=MessageRole.ASSISTANT, content=result.content)
