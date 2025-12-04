"""
Chat Endpoints

Streaming chat completions with RAG and tool support
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.services.llm_service import LLMService
from src.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


# Models
class ChatMessage(BaseModel):
    role: str
    content: str


class Tool(BaseModel):
    type: str
    function: dict


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    user: Optional[str] = "default_user"
    stream: bool = True
    temperature: Optional[float] = 0.7
    tools: Optional[List[Tool]] = None


@router.post("/completions")
async def chat_completions(request: ChatRequest):
    """
    Stream chat completions with optional RAG and tools
    
    - **model**: Model name (e.g., deepseek-chat)
    - **messages**: Conversation history
    - **stream**: Enable streaming response
    - **tools**: Optional function calling tools
    """
    logger.info(
        f"Chat request: user={request.user}, model={request.model}, "
        f"tools={len(request.tools) if request.tools else 0}"
    )
    
    try:
        # Initialize services
        llm_service = LLMService()
        
        # Get LLM response with streaming
        stream = await llm_service.chat_completion(
            model=request.model,
            messages=[msg.dict() for msg in request.messages],
            temperature=request.temperature,
            tools=[tool.dict() for tool in request.tools] if request.tools else None,
            stream=request.stream,
        )
        
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
        )
        
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(
    user_id: str,
    limit: int = 50,
    skip: int = 0,
):
    """Get chat history for a user"""
    # TODO: Implement chat history retrieval
    return {
        "conversations": [],
        "total": 0,
    }


@router.delete("/{chat_id}")
async def delete_conversation(chat_id: str):
    """Delete a conversation"""
    # TODO: Implement conversation deletion
    return {"message": "Conversation deleted", "chat_id": chat_id}
