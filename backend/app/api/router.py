from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.providers import router as providers_router
from app.api.session import router as session_router

api_router = APIRouter()
api_router.include_router(providers_router)
api_router.include_router(session_router)
api_router.include_router(chat_router)
