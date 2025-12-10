"""
Chat Endpoints

Streaming chat completions with RAG and tool support using DeepSeek function calling
"""
import json
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


def _get_rag_tools() -> List[dict]:
    """Define RAG function calling tools for DeepSeek"""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Search the company's internal knowledge base for information about policies, procedures, guidelines, and documentation. Use this when users ask about company-related information in any language (English, Vietnamese, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query in the user's original language"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 3)",
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False
                }
            }
        }
    ]


async def _execute_tool_call(tool_name: str, tool_args: dict) -> str:
    """Execute RAG tool calls"""
    if tool_name == "search_knowledge_base":
        rag_service = RAGService()
        query = tool_args.get("query", "")
        top_k = tool_args.get("top_k", 3)
        
        logger.info(f"Searching KB: query='{query}', top_k={top_k}")
        
        results = await rag_service.search(
            query=query,
            limit=top_k,
            score_threshold=0.5
        )
        
        if not results:
            return "No relevant information found in the knowledge base."
        
        # Format results for LLM
        formatted = []
        for i, doc in enumerate(results, 1):
            formatted.append(
                f"Document {i} (relevance: {doc['score']:.2f}):\n"
                f"Title: {doc.get('title', 'Unknown')}\n"
                f"Content: {doc.get('content', '')}\n"
                f"Source: {doc.get('source', 'Unknown')}"
            )
        
        return "\n\n".join(formatted)
    
    return f"Unknown tool: {tool_name}"


@router.post("/completions")
async def chat_completions(request: ChatRequest):
    """
    Stream chat completions with DeepSeek function calling for RAG
    
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
        
        # Convert request messages to dict format
        messages = [msg.dict() for msg in request.messages]
        
        # Add RAG tools to request
        rag_tools = _get_rag_tools()
        all_tools = rag_tools + ([tool.dict() for tool in request.tools] if request.tools else [])
        
        logger.info(f"Using {len(all_tools)} tools (including RAG)")
        
        # First LLM call - let it decide if it needs RAG
        first_response = await llm_service.chat_completion_with_tools(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            tools=all_tools,
            stream=False,  # Need full response to check tool calls
        )
        
        # Check if LLM wants to call RAG tool
        if first_response.get("tool_calls"):
            logger.info(f"LLM requested {len(first_response['tool_calls'])} tool calls")
            
            # Execute tool calls
            messages.append({
                "role": "assistant",
                "content": first_response.get("content"),
                "tool_calls": first_response["tool_calls"]
            })
            
            for tool_call in first_response["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                
                logger.info(f"Executing: {tool_name}({tool_args})")
                
                tool_result = await _execute_tool_call(tool_name, tool_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result
                })
            
            # Second LLM call with tool results - always stream
            stream = llm_service.chat_completion(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                tools=None,  # Don't need tools in second call
                stream=True,  # Always stream final response
            )
            
            return StreamingResponse(
                stream,
                media_type="text/event-stream",
            )
        else:
            # No tool calls needed - check if stream requested
            logger.info("No tool calls needed, direct response")
            
            if request.stream:
                # Convert non-streaming response to streaming format
                async def stream_wrapper():
                    content = first_response.get("content", "")
                    if content:
                        data = {
                            "id": "chatcmpl-" + str(hash(content))[:8],
                            "object": "chat.completion.chunk",
                            "created": int(__import__('time').time()),
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    yield "data: [DONE]\n\n"
                
                return StreamingResponse(
                    stream_wrapper(),
                    media_type="text/event-stream",
                )
            else:
                # Return non-streaming response
                return {
                    "id": "chatcmpl-" + str(hash(first_response.get("content", "")))[:8],
                    "object": "chat.completion",
                    "created": int(__import__('time').time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": first_response.get("content", "")
                        },
                        "finish_reason": "stop"
                    }]
                }
        
    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
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
