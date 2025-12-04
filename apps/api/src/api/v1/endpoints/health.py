"""Health check endpoints"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness probe for K8s"""
    # Check dependencies: DB, Qdrant, Redis, etc.
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness probe for K8s"""
    return {"status": "alive"}
