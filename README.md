# Enterprise RAG Chat System

Enterprise-grade chat system with RAG (Retrieval Augmented Generation) capabilities, powered by LibreChat, Ollama, and Qdrant.

## Architecture

- **LibreChat**: Web UI for chat interface
- **FastAPI Backend**: REST API with RAG endpoints
- **MCP Server**: Model Context Protocol server for LibreChat integration
- **Qdrant**: Vector database for document storage
- **Ollama**: Local embeddings with nomic-embed-text
- **MongoDB**: Data persistence for chat history
- **DeepSeek**: LLM provider for chat completions

## Features

- 📄 **Document Upload**: Support PDF, DOCX, TXT, MD files
- 🔍 **Semantic Search**: Vector similarity search with Qdrant
- 💬 **Chat Interface**: LibreChat UI with streaming responses
- 🔧 **MCP Tools**: Search documents, get documents, list collections
- 🐳 **Docker Compose**: Complete containerized stack
- 🔄 **Hot Reload**: Development mode with auto-restart

## Prerequisites

- Docker and Docker Compose
- DeepSeek API key (get from https://platform.deepseek.com/)

## Quick Start

### 1. Setup Environment

```bash
# Copy and configure environment variables
cp .env.example .env

# Edit .env and add your DeepSeek API key
DEEPSEEK_API_KEY=sk-your-api-key-here
```

### 2. Start Services

```bash
# Make scripts executable
chmod +x infrastructure/docker/start.sh
chmod +x infrastructure/docker/stop.sh

# Start all services
./infrastructure/docker/start.sh

# Or use docker-compose directly
docker-compose -f infrastructure/docker/docker-compose.yml --env-file .env up -d
```

### 3. Access Services

- **LibreChat UI**: http://localhost:3080
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## API Usage

### Upload Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@document.pdf" \
  -F "title=My Document" \
  -F "source=Upload" \
  -F "user_id=user123"
```

### Search Documents

```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "security policy",
    "top_k": 5,
    "score_threshold": 0.5
  }'
```

### Get Document

```bash
curl http://localhost:8000/api/v1/documents/{doc_id}
```

### Delete Document

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/{doc_id}
```

### List Collections

```bash
curl http://localhost:8000/api/v1/documents/collections/list
```

## MCP Server Integration

The MCP (Model Context Protocol) server provides tools for LibreChat:

1. **search_documents**: Search internal knowledge base
   - Input: query, top_k, score_threshold
   - Returns: List of relevant documents

2. **get_document**: Get specific document by ID
   - Input: document_id
   - Returns: Document content and metadata

3. **list_collections**: List all document collections
   - Returns: Collection names and statistics

LibreChat automatically invokes these tools when needed during conversations.

## Configuration

### LibreChat

Edit `infrastructure/docker/librechat.yaml`:

```yaml
mcpServers:
  enterprise-rag:
    command: docker
    args: [exec, -i, mcp-rag-server, python, -m, src.server]
    env:
      API_BASE_URL: "http://api:8000/api/v1"

endpoints:
  custom:
    - name: "Enterprise RAG"
      baseURL: "http://api:8000/api/v1"
      models: ["deepseek-chat", "deepseek-reasoner"]
```

### Vector Search

Adjust search threshold in `apps/api/src/services/rag_service.py`:

```python
async def search(
    self,
    query: str,
    limit: int = 5,
    score_threshold: float = 0.5,  # Default: 0.5 (range: 0.0 - 1.0)
    ...
)
```

Lower threshold = more results (less strict)
Higher threshold = fewer results (more strict)

### Embeddings Model

Ollama uses `nomic-embed-text` by default. To change:

```bash
# Pull different model
docker exec -it ollama ollama pull mxbai-embed-large

# Update RAG_SERVICE_OLLAMA_MODEL in .env
RAG_SERVICE_OLLAMA_MODEL=mxbai-embed-large
```

## Development

### Project Structure

```
my_enterprise_chat/
├── apps/
│   └── api/
│       └── src/
│           ├── api/v1/endpoints/  # API endpoints
│           ├── services/          # Business logic
│           └── main.py            # FastAPI app
├── services/
│   └── mcp-server/
│       └── src/
│           └── server.py          # MCP protocol server
├── infrastructure/
│   └── docker/
│       ├── docker-compose.yml     # Service orchestration
│       └── librechat.yaml         # LibreChat config
└── data/                          # Persistent data
    ├── mongo/                     # MongoDB data
    ├── qdrant/                    # Vector database
    └── ollama/                    # Model storage
```

### Hot Reload

API supports hot reload in development:

```yaml
volumes:
  - ../../apps/api:/app  # Mount source code
command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Logs

```bash
# All services
docker-compose -f infrastructure/docker/docker-compose.yml logs -f

# Specific service
docker logs -f enterprise-chat-api
docker logs -f librechat
docker logs -f qdrant
```

## Troubleshooting

### LibreChat "Missing API Key" Error

```bash
# Verify environment variable is loaded
docker exec librechat env | grep DEEPSEEK

# Restart services with --env-file
./infrastructure/docker/stop.sh
./infrastructure/docker/start.sh
```

### Search Returns Empty Results

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify collection exists
curl http://localhost:6333/collections

# Lower score threshold
curl -X POST http://localhost:8000/api/v1/documents/search \
  -d '{"query": "test", "score_threshold": 0.1}'
```

### MCP Server Issues

```bash
# MCP server should NOT auto-start
# It's invoked by LibreChat via docker exec

# Check logs in LibreChat
docker logs librechat | grep mcp

# Test MCP server manually
docker run -i --rm \
  --network docker_enterprise_network \
  -e API_BASE_URL=http://api:8000/api/v1 \
  docker-mcp-rag \
  python -m src.server
```

### MongoDB Compatibility

```bash
# If MongoDB fails to start with existing v5 data:
# - Version is pinned to mongo:5
# - Data persists in data/mongo/

# Clean start (deletes data):
docker-compose down -v
rm -rf data/mongo/*
docker-compose up -d
```

## Production Considerations

1. **Security**:
   - Use secrets management (not .env files)
   - Enable authentication on Qdrant
   - Add API authentication/authorization
   - Use HTTPS with reverse proxy

2. **Performance**:
   - Increase Ollama memory limit
   - Scale API with multiple replicas
   - Add Redis for caching
   - Use GPU for embeddings

3. **Monitoring**:
   - Add Prometheus metrics
   - Setup health checks
   - Log aggregation (ELK/Loki)
   - Error tracking (Sentry)

4. **Backup**:
   - Regular MongoDB backups
   - Qdrant snapshots
   - Document versioning

## License

MIT License

## Support

For issues, questions, or contributions, please open an issue on GitHub.