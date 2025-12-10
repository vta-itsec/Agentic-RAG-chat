"""
MCP Server with FastMCP
Provides SSE endpoint for LibreChat to connect
"""
import os
import sys

import httpx
from fastmcp import FastMCP, Context


# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000/api/v1")
API_TIMEOUT = 30.0

# Initialize FastMCP server
mcp = FastMCP(
    "Enterprise RAG",
    dependencies=["httpx"]
)


@mcp.tool()
async def search_documents(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
    ctx: Context = None
) -> str:
    """
    Search internal knowledge base for relevant documents.
    
    Use this when users ask about company policies, procedures,
    technical documentation, or any domain-specific information.
    
    Args:
        query: The search query to find relevant documents
        top_k: Number of results to return (default: 5, max: 20)
        score_threshold: Minimum similarity score (0.0-1.0, default: 0.5)
        ctx: FastMCP context for logging (optional)
    
    Returns:
        Formatted string with search results
    """
    if not query:
        return "Error: Query parameter is required"
    
    # Log to client if context available
    if ctx:
        await ctx.info(f"Searching documents for: '{query}'")
    
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/documents/search",
                json={
                    "query": query,
                    "top_k": min(top_k, 20),
                    "score_threshold": score_threshold
                }
            )
            response.raise_for_status()
            results = response.json()
            
            if not results:
                return f"No documents found matching query: '{query}'"
            
            # Format results
            formatted_results = []
            for i, doc in enumerate(results, 1):
                result_text = (
                    f"**Document {i}** (Score: {doc['score']:.3f})\n"
                    f"**Title:** {doc.get('title', 'Untitled')}\n"
                    f"**Source:** {doc.get('source', 'Unknown')}\n"
                    f"**Content:**\n{doc['content']}\n"
                    f"**ID:** {doc['id']}\n"
                    f"---"
                )
                formatted_results.append(result_text)
            
            return f"Found {len(results)} relevant documents:\n\n" + "\n\n".join(formatted_results)
            
    except httpx.HTTPError as e:
        return f"Error searching documents: {str(e)}"


@mcp.tool()
async def get_document(document_id: str, ctx: Context = None) -> str:
    """
    Retrieve a specific document by its ID.
    
    Use when you have a document ID from search results and need the full content.
    
    Args:
        document_id: The unique ID of the document to retrieve
        ctx: FastMCP context for logging (optional)
    
    Returns:
        Document content and metadata
    """
    if ctx:
        await ctx.info(f"Fetching document: {document_id}")
    if not document_id:
        return "Error: document_id parameter is required"
    
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(f"{API_BASE_URL}/documents/{document_id}")
            response.raise_for_status()
            doc = response.json()
            
            result_text = (
                f"**Title:** {doc.get('title', 'Untitled')}\n"
                f"**Source:** {doc.get('source', 'Unknown')}\n"
                f"**Created:** {doc.get('created_at', 'N/A')}\n\n"
                f"**Content:**\n{doc['content']}"
            )
            
            return result_text
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Document not found: {document_id}"
        return f"Error retrieving document: {str(e)}"


@mcp.tool()
async def list_collections(ctx: Context = None) -> str:
    """
    List all available document collections and their statistics.
    
    Use to understand what knowledge bases are available.
    
    Args:
        ctx: FastMCP context for logging (optional)
    
    Returns:
        List of collections with document counts
    """
    if ctx:
        await ctx.info("Listing all document collections")
    
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(f"{API_BASE_URL}/documents/collections/list")
            response.raise_for_status()
            collections = response.json()
            
            if not collections:
                return "No collections found. Upload documents to create collections."
            
            result_lines = ["**Available Collections:**\n"]
            for coll in collections:
                result_lines.append(
                    f"- **{coll.get('name', 'Unknown')}**: "
                    f"{coll.get('vectors_count', 0)} documents"
                )
            
            return "\n".join(result_lines)
            
    except httpx.HTTPError as e:
        return f"Error listing collections: {str(e)}"


# Run server
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5173"))
    
    # Run with mcp.run() which handles SSE setup automatically
    mcp.run(transport="sse", port=port, host="0.0.0.0")
