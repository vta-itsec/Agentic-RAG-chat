# MCP Server - Enterprise RAG

Model Context Protocol server for querying internal knowledge base.

## Features

- **search_documents**: Search knowledge base with semantic similarity
- **get_document**: Retrieve full document content by ID
- **list_collections**: List all available document collections

## Architecture

```
LibreChat → MCP Server → API Backend → Qdrant Vector DB
```

## Usage with LibreChat

1. Start all services:
```bash
./infrastructure/docker/start.sh
```

2. In LibreChat UI:
   - Select "Enterprise RAG" endpoint
   - The MCP tools will be available automatically
   - Ask questions like: "Search for our security policy"

## Available Tools

### search_documents
Search internal knowledge base for relevant documents.

**Parameters:**
- `query` (required): Search query
- `top_k` (optional): Number of results (default: 5, max: 20)
- `collection` (optional): Specific collection to search

**Example:**
```
"Search for employee onboarding procedures"
```

### get_document
Retrieve full content of a specific document.

**Parameters:**
- `document_id` (required): Document unique identifier

**Example:**
```
"Get document with ID: doc_12345"
```

### list_collections
List all available document collections.

**Example:**
```
"Show me all available document collections"
```

## Development

### Local Testing

```bash
# Build image
docker build -t mcp-rag-server services/mcp-server/

# Run standalone
docker run -it --rm \
  -e API_BASE_URL=http://host.docker.internal:8000/api/v1 \
  mcp-rag-server
```

### Adding New Tools

1. Add tool definition in `handle_list_tools()`
2. Implement handler function
3. Add to `handle_call_tool()` dispatcher
4. Update requirements.txt if needed
5. Rebuild container

## Environment Variables

- `API_BASE_URL`: Backend API endpoint (default: http://api:8000/api/v1)
- `API_TIMEOUT`: HTTP request timeout in seconds (default: 30.0)

## Troubleshooting

### MCP server not connecting

```bash
# Check logs
docker logs mcp-rag-server

# Verify API is reachable
docker exec mcp-rag-server curl http://api:8000/api/v1/health
```

### No search results

- Ensure documents are uploaded to Qdrant
- Check API logs for errors
- Verify collection names match

## API Integration

The MCP server communicates with these API endpoints:

- `POST /api/v1/documents/search` - Search documents
- `GET /api/v1/documents/{id}` - Get document by ID
- `GET /api/v1/documents/collections` - List collections
