from fastapi import APIRouter, Depends, status

from app.schemas.chat import CreateSessionResponse, DeleteSessionResponse
from app.services.session_manager import SessionManager, get_session_manager

router = APIRouter(prefix="/session", tags=["session"])


@router.post(
    "",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create chat session",
    description=(
        "Create an empty in-memory session with independent OpenAI, Claude, "
        "and Gemini histories. Sessions are not persisted across restarts."
    ),
)
async def create_session(
    sessions: SessionManager = Depends(get_session_manager),
) -> CreateSessionResponse:
    session = await sessions.create_session()
    return CreateSessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
    )


@router.delete(
    "/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete chat session",
    description="Remove a session and all provider histories. Missing IDs return HTTP 404.",
)
async def delete_session(
    session_id: str,
    sessions: SessionManager = Depends(get_session_manager),
) -> DeleteSessionResponse:
    await sessions.delete_session(session_id)
    return DeleteSessionResponse(session_id=session_id, deleted=True)
