# 🏗️ Architecture Overview

## System Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  Web Browser     │         │  Mobile App      │              │
│  │  (LibreChat UI)  │         │  (Future)        │              │
│  └────────┬─────────┘         └────────┬─────────┘              │
└───────────┼──────────────────────────────┼────────────────────────┘
            │                              │
            └──────────────┬───────────────┘
                           │ HTTPS
┌─────────────────────────▼────────────────────────────────────────┐
│                    API Gateway Layer                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │           FastAPI Application (Port 8000)                   │  │
│  │  • Authentication & Authorization (JWT)                     │  │
│  │  • Rate Limiting & Throttling                               │  │
│  │  • Request Validation                                       │  │
│  │  • Response Caching                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────┬──────────────┬──────────────┬────────────────────────┘
            │              │              │
      ┌─────▼─────┐  ┌────▼─────┐  ┌────▼──────┐
      │  LLM      │  │   RAG    │  │   MCP     │
      │ Gateway   │  │  Engine  │  │  Tools    │
      └─────┬─────┘  └────┬─────┘  └────┬──────┘
            │              │              │
┌───────────▼──────────────▼──────────────▼────────────────────────┐
│                     Service Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   DeepSeek   │  │    Qdrant    │  │   MongoDB    │           │
│  │     API      │  │  Vector DB   │  │  Document DB │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Gateway (`apps/api`)

**Purpose**: Centralized entry point for all client requests

**Responsibilities**:
- Request routing & load balancing
- Authentication & authorization
- Rate limiting per user/org
- Request/response transformation
- Error handling & logging

**Tech Stack**:
- FastAPI (async Python web framework)
- JWT for authentication
- Redis for rate limiting & caching

### 2. LLM Gateway Service (`services/llm-gateway`)

**Purpose**: Intelligent routing to multiple LLM providers

**Features**:
- Multi-provider support (DeepSeek, OpenAI, Anthropic)
- Automatic fallback on provider failures
- Response caching for identical queries
- Cost optimization routing
- Token usage tracking

**Provider Priority**:
1. DeepSeek (primary - cost-effective)
2. OpenAI (fallback - high reliability)
3. Anthropic (fallback - advanced reasoning)

### 3. RAG Engine (`services/rag-engine`)

**Purpose**: Semantic search over user documents

**Pipeline**:
```
Document Upload
    ↓
Text Extraction (PDF/DOCX/TXT)
    ↓
Chunking (512 tokens with overlap)
    ↓
Embedding Generation (Ollama - nomic-embed-text)
    ↓
Vector Storage (Qdrant with metadata)
    ↓
Query Time: Vector Search → Context Injection → LLM
```

**Features**:
- Multi-tenant data isolation
- Hybrid search (semantic + keyword)
- Metadata filtering
- Reranking for relevance

### 4. MCP Tool Server (`services/mcp-server`)

**Purpose**: Function calling tools for LLM agents

**Available Tools**:
- `search_internal_documents`: Search vector database
- `fetch_website_content`: Fetch & parse web pages
- (Future): `execute_code`, `query_database`, etc.

### 5. Document Processor (`services/document-processor`)

**Purpose**: Async document processing pipeline

**Features**:
- Parallel processing with Celery
- Support for 50+ file formats
- OCR for scanned PDFs
- Table extraction
- Image analysis

## Data Flow

### Chat Request Flow

```
1. User sends message via LibreChat
    ↓
2. API Gateway validates JWT & rate limits
    ↓
3. LLM Gateway determines if RAG needed
    ↓
4. RAG Engine retrieves relevant documents (if needed)
    ↓
5. Context + Query sent to LLM provider
    ↓
6. LLM may call tools via MCP
    ↓
7. Tools execute & return results
    ↓
8. LLM generates final response
    ↓
9. Response streamed back to client
```

### Document Upload Flow

```
1. User uploads file via UI
    ↓
2. API Gateway saves to temp storage
    ↓
3. Document Processor extracts text
    ↓
4. Text split into chunks
    ↓
5. Embeddings generated via Ollama
    ↓
6. Vectors stored in Qdrant with metadata
    ↓
7. User notified of completion
```

## Scalability Considerations

### Horizontal Scaling

- **API Gateway**: Stateless, scale with load balancer
- **LLM Gateway**: Cache results in Redis, scale independently
- **RAG Engine**: Qdrant supports clustering
- **Document Processor**: Celery workers scale horizontally

### Vertical Scaling

- **Qdrant**: Increase memory for larger vector collections
- **MongoDB**: Shard for multi-tenancy at scale
- **Ollama**: GPU acceleration for embeddings

## Security

### Authentication Flow

```
1. User logs in → API issues JWT access + refresh tokens
2. Client stores tokens (httpOnly cookies)
3. Each request includes Authorization: Bearer <token>
4. API validates token signature & expiry
5. Token includes: user_id, org_id, roles
```

### Data Isolation

- **Multi-tenancy**: Qdrant collections partitioned by org_id
- **Row-level security**: MongoDB queries filtered by org_id
- **API-level**: All queries include org context

## Monitoring & Observability

### Metrics (Future)

- Request latency (p50, p95, p99)
- LLM token usage per user/org
- Vector search performance
- Error rates by endpoint

### Logging

- Structured JSON logs via structlog
- Correlation IDs for request tracing
- Sensitive data masking

### Health Checks

- `/health`: Basic liveness
- `/health/ready`: Dependency checks (DB, Qdrant, Redis)

## Deployment

### Docker Compose (Development)

```bash
docker-compose up -d
```

### Kubernetes (Production - Future)

- API Gateway: 3 replicas + HPA
- LLM Gateway: 2 replicas
- RAG Engine: 2 replicas
- Qdrant: StatefulSet with persistent volumes
- MongoDB: ReplicaSet (3 nodes)
