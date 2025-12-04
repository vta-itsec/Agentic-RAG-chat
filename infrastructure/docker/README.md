# Enterprise Chat - Docker Deployment

## Cấu trúc mới (SaaS Architecture)

```
infrastructure/docker/
├── docker-compose.yml    # Service orchestration
├── librechat.yaml        # LibreChat configuration
└── README.md            # This file
```

## Services

### Frontend
- **LibreChat** (port 3080) - UI
  - Kết nối MongoDB để lưu conversations
  - Giao tiếp với API qua internal network

### Backend
- **API** (port 8000) - Main API service
  - FastAPI với clean architecture
  - LLM proxy (DeepSeek, OpenRouter, etc.)
  - RAG service với Qdrant
  - Function calling support
  - Health checks: `/api/v1/health`

### Infrastructure
- **MongoDB** (port 27017) - User data & conversations
- **Qdrant** (port 6333, 6334) - Vector database
- **Ollama** (port 11434) - Local embeddings

## Yêu cầu

1. **File .env** ở root project:
```bash
# API Keys
DEEPSEEK_API_KEY=sk-xxx
OPENROUTER_API_KEY=sk-or-xxx (optional)

# JWT Secret (generate với: openssl rand -hex 32)
JWT_SECRET=your-secret-here

# Optional
POSTGRES_PASSWORD=secure-password
```

2. **Ollama models** (pull trước khi chạy):
```bash
ollama pull nomic-embed-text
```

## Chạy hệ thống

### 1. Từ thư mục infrastructure/docker:

```bash
cd infrastructure/docker

# Build và start tất cả services
docker-compose up -d

# Xem logs
docker-compose logs -f api
docker-compose logs -f librechat

# Stop tất cả
docker-compose down

# Stop và xóa volumes (reset database)
docker-compose down -v
```

### 2. Từ root project (khuyến nghị):

```bash
# Chạy từ root để đảm bảo context đúng
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Logs
docker-compose -f infrastructure/docker/docker-compose.yml logs -f

# Stop
docker-compose -f infrastructure/docker/docker-compose.yml down
```

## Kiểm tra services

### 1. Health checks:

```bash
# API health
curl http://localhost:8000/api/v1/health

# API docs
open http://localhost:8000/docs

# Qdrant
curl http://localhost:6333/healthz

# Ollama
curl http://localhost:11434/api/tags
```

### 2. Test API trực tiếp:

```bash
# List models
curl http://localhost:8000/api/v1/models

# Chat completion (streaming)
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

### 3. LibreChat UI:

```bash
# Mở trình duyệt
open http://localhost:3080

# Register user mới hoặc login
# Chọn endpoint: "Enterprise RAG"
# Model: deepseek-chat hoặc deepseek-reasoner
```

## Upload documents (RAG)

```bash
# Upload file để indexing
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@document.pdf" \
  -F "metadata={\"source\":\"manual\",\"category\":\"policy\"}"

# List documents
curl http://localhost:8000/api/v1/documents

# Delete document
curl -X DELETE http://localhost:8000/api/v1/documents/{doc_id}
```

## Hot reload trong development

Code changes tự động reload nhờ volume mounts:
- `apps/api/src` → `/app/src` (API code)
- `apps/api/providers.yaml` → `/app/providers.yaml` (LLM configs)

## Troubleshooting

### Container không start:

```bash
# Xem logs chi tiết
docker-compose logs api
docker-compose logs librechat

# Kiểm tra container status
docker ps -a

# Restart specific service
docker-compose restart api
```

### API không kết nối được:

1. Kiểm tra .env file có DEEPSEEK_API_KEY
2. Kiểm tra network: `docker network ls`
3. Test từ host: `curl http://localhost:8000/api/v1/health`
4. Test từ container:
```bash
docker exec -it librechat curl http://api:8000/api/v1/health
```

### LibreChat không thấy models:

1. Kiểm tra librechat.yaml mount đúng:
```bash
docker exec librechat cat /app/librechat.yaml
```

2. Kiểm tra API endpoint trong config:
- baseURL phải là `http://api:8000/api/v1`
- Không dùng localhost vì containers dùng internal network

3. Restart LibreChat:
```bash
docker-compose restart librechat
```

### Database connection issues:

```bash
# MongoDB
docker exec -it mongodb mongosh
> show dbs
> use enterprise_chat
> show collections

# Qdrant
curl http://localhost:6333/collections
```

### Ollama models không load:

```bash
# Exec vào container
docker exec -it ollama bash

# Pull model
ollama pull nomic-embed-text

# List models
ollama list
```

## Production deployment

Để deploy production, sửa docker-compose.yml:

1. Tắt hot reload (remove volume mounts for src/)
2. Đổi ENVIRONMENT=production
3. Set DEBUG=false
4. Configure proper secrets management
5. Add reverse proxy (nginx)
6. Enable SSL/TLS
7. Setup monitoring (Prometheus + Grafana)

## Architecture diagram

```
┌─────────────┐
│  Browser    │
│  :3080      │
└──────┬──────┘
       │
┌──────▼──────────┐
│   LibreChat     │
│   (Frontend)    │
└──────┬──────────┘
       │
┌──────▼──────────┐
│      API        │◄──────┐
│   (FastAPI)     │       │
└──┬───┬───┬──────┘       │
   │   │   │              │
   │   │   └──────────────┤
   │   │                  │
┌──▼───▼────┐    ┌────────▼─────┐
│  Qdrant   │    │   MongoDB    │
│ (Vectors) │    │  (App Data)  │
└───────────┘    └──────────────┘
       │
┌──────▼──────┐
│   Ollama    │
│ (Embeddings)│
└─────────────┘
```

## Next steps

- [ ] Implement RAG service (services/rag-engine/)
- [ ] Add MCP server (services/mcp-server/)
- [ ] Setup Redis for caching
- [ ] Add monitoring with Prometheus
- [ ] Create Kubernetes manifests
- [ ] Setup CI/CD pipeline
