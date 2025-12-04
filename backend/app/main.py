import os
import json
import time
import uuid
import shutil
import logging
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
import yaml

# MCP Imports
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent

# Import modules nội bộ
from app.rag import get_vector_store, process_file, get_all_files
from app.llm_factory import get_llm_client
from qdrant_client.http import models as qdrant_models
from langchain_core.messages import SystemMessage, HumanMessage

# Cấu hình Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise RAG Backend")

# Khởi tạo MCP Server
mcp = Server("enterprise-knowledge-base")
sse = SseServerTransport("/messages")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
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
    tools: Optional[List[Tool]] = None  # Support function calling

# --- HELPER FUNCTIONS ---
# (RAG logic đã chuyển sang MCP tools, không cần parse model suffixes nữa)

async def openai_stream_generator(chat_generator, model_name: str):
    """ Generator chuẩn SSE format cho LibreChat """
    chat_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())

    try:
        async for chunk in chat_generator:
            content = chunk.content
            if content:
                response_data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(response_data)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/v1/models")
async def list_models():
    """
    Trả về danh sách model để LibreChat nhận diện.
    RAG được xử lý qua MCP tools, không cần suffixes.
    """
    return {
        "object": "list",
        "data": [
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
            {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
        ]
    }

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    is_global: bool = Form(False)
):
    try:
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(temp_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        background_tasks.add_task(
            process_file, 
            file_path=file_path, 
            file_type=file.content_type or "text/plain",
            user_id=user_id, 
            is_global=is_global,
            original_filename=file.filename
        )
        return {"message": "Processing started", "file_id": unique_filename}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
async def list_files():
    """Endpoint để xem danh sách file đã upload"""
    try:
        files = get_all_files()
        return {"files": files, "count": len(files)}
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Built-in tools definition
BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_internal_documents",
            "description": "Search for information in the internal company knowledge base. Use this when asked about company documents, employees, policies, or any uploaded files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant information"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    Chat endpoint - proxy requests với function calling support.
    Gọi trực tiếp DeepSeek API để hỗ trợ tools đúng cách.
    """
    logger.info(f"Chat request: user={request.user}, model={request.model}, tools={len(request.tools) if request.tools else 0}")
    
    try:
        # Load provider config
        with open("providers.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        provider = config["providers"][0]  # DeepSeek
        api_key = os.getenv(provider["api_key_env"])
        base_url = provider["base_url"]
        
        logger.info(f"Using provider: {provider['name']}, base_url: {base_url}")
        
        # Tạo OpenAI client
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # Prepare messages
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Prepare request params
        params = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature or 0.7,
            "stream": request.stream
        }
        
        # Thêm tools - ưu tiên từ request, fallback sang built-in tools
        if request.tools:
            params["tools"] = [tool.dict() for tool in request.tools]
            logger.info(f"Using {len(request.tools)} tools from request")
        else:
            # Auto-inject built-in tools
            params["tools"] = BUILTIN_TOOLS
            logger.info(f"Auto-injected {len(BUILTIN_TOOLS)} built-in tools")
        
        # Call API (first call - may trigger tool calls)
        response = await client.chat.completions.create(**params)
        
        # Check if tool was called (need non-stream for tool handling)
        if not request.stream:
            # For non-streaming, handle tool execution
            pass  # TODO: implement later
        
        # Stream response
        async def stream_generator():
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'id': str(chunk.id), 'object': 'chat.completion.chunk', 'created': chunk.created, 'model': request.model, 'choices': [{'index': 0, 'delta': {'content': chunk.choices[0].delta.content}, 'finish_reason': None}]})}\n\n"
                elif chunk.choices[0].delta.tool_calls:
                    # Forward tool call chunk to LibreChat
                    tool_call = chunk.choices[0].delta.tool_calls[0]
                    yield f"data: {json.dumps({'id': str(chunk.id), 'object': 'chat.completion.chunk', 'created': chunk.created, 'model': request.model, 'choices': [{'index': 0, 'delta': {'tool_calls': [tool_call.dict()]}, 'finish_reason': None}]})}\n\n"
            
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"LLM Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# MCP SERVER - TOOL DEFINITIONS (Để LibreChat Agent sử dụng)
# ==============================================================================

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    tools = [
        Tool(
            name="search_internal_documents",
            description="Search for information in the internal company knowledge base. "
                        "Use this when asked about company documents, employees, policies, "
                        "or any uploaded files. Returns relevant excerpts from the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question to find relevant information"
                    }
                },
                "required": ["query"]
            }
        )
    ]
    logger.info(f"[MCP] Returning {len(tools)} tools: {[t.name for t in tools]}")
    return tools

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_internal_documents":
        query = arguments.get("query")
        logger.info(f"[MCP Tool Called] search_internal_documents: {query}")
        
        try:
            vector_store = get_vector_store()
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            docs = await retriever.ainvoke(query)
            
            if not docs:
                return [TextContent(
                    type="text", 
                    text="No relevant documents found in the knowledge base."
                )]
            
            # Format kết quả
            results = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get('source', 'Unknown')
                content = doc.page_content[:500]  # Giới hạn 500 ký tự
                results.append(f"[Document {i}: {source}]\n{content}\n")
            
            return [TextContent(
                type="text",
                text="\n".join(results)
            )]
            
        except Exception as e:
            logger.error(f"[MCP Tool Error] {e}")
            return [TextContent(
                type="text",
                text=f"Error searching knowledge base: {str(e)}"
            )]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

# ==============================================================================
# MCP SSE ENDPOINTS (Để LibreChat kết nối)
# ==============================================================================

@app.get("/sse")
async def handle_sse(request: Request):
    """SSE endpoint cho MCP protocol"""
    async with sse.connect_sse(
        request.scope, 
        request.receive, 
        request._send
    ) as streams:
        await mcp.run(
            streams[0], 
            streams[1], 
            mcp.create_initialization_options()
        )

@app.post("/messages")
async def handle_messages(request: Request):
    """Message endpoint cho MCP protocol"""
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )