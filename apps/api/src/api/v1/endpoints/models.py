"""Models endpoints"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
            {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
        ]
    }
