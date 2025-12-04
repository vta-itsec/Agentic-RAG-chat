import uvicorn
import logging
import httpx
import readabilipy.simple_json
import markdownify
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent

# Cấu hình Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-fetch")

# --- QUAN TRỌNG: HEADER GIẢ DANH ĐỂ KHÔNG BỊ CHẶN ---
FAKE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/"
}

# KHỞI TẠO SERVER
mcp = Server("internet-fetcher")
sse = SseServerTransport("/messages")

async def fetch_and_clean(url: str) -> str:
    # verify=False để tránh lỗi SSL, follow_redirects=True để tự chuyển hướng
    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=FAKE_HEADERS)
            resp.raise_for_status()
            
            # Dùng readabilipy để lọc nội dung chính (cần Nodejs trong Dockerfile)
            try:
                article = readabilipy.simple_json.simple_json_from_html_string(
                    resp.text, use_readability=True
                )
                html_content = article.get("content") or resp.text
                title = article.get("title", "No Title")
            except Exception:
                html_content = resp.text
                title = "Raw Content"

            # Chuyển sang Markdown
            markdown = markdownify.markdownify(html_content, heading_style="ATX")
            return f"# {title}\n\n{markdown[:15000]}" # Cắt 15k ký tự
            
        except httpx.HTTPStatusError as e:
            return f"Error {e.response.status_code}: Website blocked access or page not found."
        except Exception as e:
            return f"Fetch Error: {str(e)}"

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="fetch_website_content",
            description="Use this tool to read content from an external URL (Internet). "
                        "Useful for summarizing news, articles, or reading documentation links provided by the user. "
                        "DO NOT use this for internal company files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"}
                },
                "required": ["url"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "fetch_website_content":
        url = arguments.get("url")
        content = await fetch_and_clean(url)
        return [TextContent(type="text", text=content)]
    return [TextContent(type="text", text=f"Tool {name} not found")]

# --- WEB SERVER (SSE) ---
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

app = Starlette(debug=True, routes=[
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)