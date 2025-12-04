import os
import logging
import uvicorn
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from sse_starlette.sse import EventSourceResponse

# Thư viện MCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent

# Import logic RAG cũ (đảm bảo file rag.py nằm cùng thư mục)
from app.rag import get_vector_store, process_file, get_all_files

# Cấu hình Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- KHỞI TẠO APP & MCP ---
app = FastAPI(title="Enterprise Knowledge Service")
mcp = Server("enterprise-knowledge-base")
sse = SseServerTransport("/messages")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# PHẦN 1: REST API (CHO VIỆC QUẢN TRỊ/UPLOAD)
# ==============================================================================

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
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
        
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
        return {"message": "File processing started", "filename": file.filename}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"error": str(e)}

@app.get("/files")
async def list_files():
    files = get_all_files()
    return {"files": files, "count": len(files)}

# ==============================================================================
# PHẦN 2: MCP TOOL DEFINITION (ĐỂ LLM GỌI)
# ==============================================================================

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_internal_documents",
            # MÔ TẢ NÀY RẤT QUAN TRỌNG ĐỂ LLM BIẾT KHI NÀO DÙNG
            description="Use this tool to search for INTERNAL company information. "
                        "Useful for questions about employees (e.g., Thao Dang, Tuan Anh), "
                        "projects, policies, or uploaded files. "
                        "Do not use this for general internet queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The specific keyword or question to search in the database"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_internal_documents":
        query = arguments.get("query")
        logger.info(f"MCP RAG Called with query: {query}")
        try:
            vector_store = get_vector_store()
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            docs = await retriever.ainvoke(query)
            
            if not docs:
                return [TextContent(type="text", text="No matching documents found.")]
                
            content = "\n\n".join([f"[Source: {d.metadata.get('source', 'Unknown')}]\n{d.page_content}" for d in docs])
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [TextContent(type="text", text=f"Database Error: {str(e)}")]

    return [TextContent(type="text", text=f"Tool {name} not found")]

# ==============================================================================
# PHẦN 3: SSE TRANSPORT (CẦU NỐI VỚI LIBRECHAT)
# ==============================================================================

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)