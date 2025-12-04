# API Service

FastAPI-based REST API for Enterprise RAG Chat.

## Features

- **Multi-tenant architecture**: Isolated data per organization
- **Authentication & Authorization**: JWT-based auth with RBAC
- **Rate limiting**: Per-user and per-organization limits
- **LLM Gateway**: Route requests to multiple LLM providers
- **RAG Integration**: Vector search with Qdrant
- **Tool Execution**: MCP protocol support
- **File Upload**: Multi-format document processing

## Architecture

```
apps/api/
├── src/
│   ├── api/                  # API routes
│   │   ├── v1/
│   │   │   ├── auth.py      # Authentication endpoints
│   │   │   ├── chat.py      # Chat endpoints
│   │   │   ├── documents.py # Document management
│   │   │   └── users.py     # User management
│   ├── core/                 # Core functionality
│   │   ├── config.py        # Configuration
│   │   ├── security.py      # Auth & security
│   │   └── dependencies.py  # DI containers
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   │   ├── llm_service.py  # LLM routing
│   │   ├── rag_service.py  # RAG processing
│   │   └── tool_service.py # Tool execution
│   └── main.py             # FastAPI app
├── tests/
├── Dockerfile
└── requirements.txt
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### Chat
- `POST /api/v1/chat/completions` - Stream chat completions
- `GET /api/v1/chat/history` - Get chat history
- `DELETE /api/v1/chat/{chat_id}` - Delete conversation

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `DELETE /api/v1/documents/{doc_id}` - Delete document

### Models
- `GET /api/v1/models` - List available models

## Development

```bash
cd apps/api

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --port 8000

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## Environment Variables

See `.env.example` for required environment variables.
