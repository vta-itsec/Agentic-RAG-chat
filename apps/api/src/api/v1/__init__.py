"""
API v1 Router

Main router for API v1 endpoints
"""
from fastapi import APIRouter

from src.api.v1.endpoints import chat, documents, models, health

router = APIRouter()

# Include sub-routers
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(models.router, prefix="/models", tags=["Models"])
