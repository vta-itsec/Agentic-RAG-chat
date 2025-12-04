# 🔄 Migration Guide - Old → New Structure

## Overview

This guide helps you migrate from the legacy monolithic structure to the new microservices-based SaaS architecture.

## What Changed?

### Old Structure
```
my_enterprise_chat/
├── backend/          # Monolithic FastAPI app
├── mcp_servers/      # MCP tools
├── docker-compose.yml
└── data/
```

### New Structure
```
my_enterprise_chat/
├── apps/             # Applications
│   └── api/          # Refactored FastAPI
├── services/         # Microservices
│   ├── rag-engine/
│   ├── llm-gateway/
│   └── mcp-server/
├── packages/         # Shared code
├── infrastructure/   # Deployment configs
│   └── docker/
├── scripts/          # Utilities
└── docs/             # Documentation
```

## Migration Steps

### Option 1: Automatic Migration (Recommended)

```bash
# Run migration script
chmod +x scripts/migrate.sh
./scripts/migrate.sh
```

This script will:
1. Stop old containers
2. Backup data & configs
3. Setup new structure
4. Build & start new services

### Option 2: Manual Migration

#### Step 1: Backup Everything

```bash
# Create backup directory
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup data
cp -r data/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"
cp providers.yaml "$BACKUP_DIR/"
cp librechat.yaml "$BACKUP_DIR/"
```

#### Step 2: Stop Old Services

```bash
docker-compose down
```

#### Step 3: Update Configuration

The new API expects environment variables. Update your `.env`:

```env
# Old
OPENROUTER_API_KEY=xxx
DEEPSEEK_API_KEY=xxx

# New (same, but structured)
DEEPSEEK_API_KEY=xxx

# New additions
ENVIRONMENT=production
DEBUG=false
JWT_SECRET=your-secret-key-here
JWT_REFRESH_SECRET=your-refresh-secret-here
```

#### Step 4: Update Docker Compose

```bash
# Rename old compose file
mv docker-compose.yml docker-compose.old.yml

# Symlink new compose file
ln -s infrastructure/docker/docker-compose.yml docker-compose.yml
```

#### Step 5: Update librechat.yaml

The new structure uses the new API endpoint:

```yaml
# Old
endpoints:
  custom:
    - name: "Enterprise RAG"
      baseURL: "http://rag_api:8000/v1"

# New
endpoints:
  custom:
    - name: "Enterprise RAG"
      baseURL: "http://api:8000/api/v1"  # Changed!
```

#### Step 6: Build & Start

```bash
# Build new containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

## Verification

### 1. Check Services

```bash
# All services should be running
docker-compose ps

# Expected output:
# enterprise-api    running    0.0.0.0:8000->8000/tcp
# librechat         running    0.0.0.0:3080->3080/tcp
# mongodb           running    0.0.0.0:27017->27017/tcp
# qdrant            running    0.0.0.0:6333->6333/tcp
# ollama            running    0.0.0.0:11434->11434/tcp
```

### 2. Test API

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"2.0.0","environment":"production"}

# List models
curl http://localhost:8000/api/v1/models

# Expected: {"object":"list","data":[...]}
```

### 3. Test Chat

```bash
# Test chat completion
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### 4. Access UI

Open browser: http://localhost:3080

## Data Migration

Your existing data in `data/` directory is **automatically preserved**. No manual migration needed for:

- ✅ MongoDB data (`data/mongo/`)
- ✅ Qdrant vectors (`data/qdrant/`)
- ✅ Ollama models (`data/ollama/`)
- ✅ LibreChat uploads (`data/librechat/`)

## Rollback (If Needed)

If something goes wrong, you can rollback:

```bash
# Stop new services
docker-compose down

# Restore old docker-compose
mv docker-compose.old.yml docker-compose.yml

# Start old services
docker-compose up -d
```

## Breaking Changes

### API Endpoints

| Old Endpoint | New Endpoint | Notes |
|--------------|--------------|-------|
| `/v1/chat/completions` | `/api/v1/chat/completions` | Added `/api` prefix |
| `/v1/models` | `/api/v1/models` | Added `/api` prefix |
| `/upload` | `/api/v1/documents/upload` | Restructured |
| `/files` | `/api/v1/documents` | Renamed |

### Environment Variables

No breaking changes - all old variables still work. New optional variables:

- `ENVIRONMENT` (default: "development")
- `DEBUG` (default: true)
- `POSTGRES_URL` (optional, for future use)
- `REDIS_URL` (optional, for caching)
- `SENTRY_DSN` (optional, for monitoring)

## Code Migration

### Backend Code Location

Old location:
```
backend/app/main.py
backend/app/llm_factory.py
backend/app/rag.py
```

New location:
```
apps/api/src/main.py
apps/api/src/services/llm_service.py
apps/api/src/services/rag_service.py
```

### Import Changes

Old:
```python
from app.llm_factory import get_llm_client
from app.rag import get_vector_store
```

New:
```python
from src.services.llm_service import LLMService
from src.services.rag_service import RAGService
```

## FAQ

**Q: Will my chat history be preserved?**  
A: Yes! All MongoDB data is preserved in `data/mongo/`.

**Q: Do I need to re-upload documents?**  
A: No! Qdrant vectors are preserved in `data/qdrant/`.

**Q: Can I run both old and new side-by-side?**  
A: Not recommended. They use the same ports. Use different ports if needed.

**Q: How do I update the API code?**  
A: Edit files in `apps/api/src/`. Hot reload is enabled in development.

**Q: Where are logs stored?**  
A: View with `docker-compose logs -f api` or `docker-compose logs -f librechat`

## Troubleshooting

### Issue: API won't start

**Solution**:
```bash
# Check logs
docker-compose logs api

# Common causes:
# 1. Missing .env variables
# 2. Port 8000 already in use
# 3. Build cache issues → docker-compose build --no-cache
```

### Issue: "Import could not be resolved"

**Solution**:
```bash
# Rebuild container
docker-compose build api

# Or install locally for IDE
cd apps/api
pip install -r requirements.txt
```

### Issue: LibreChat can't connect to API

**Solution**:
```bash
# Check librechat.yaml baseURL
# Should be: http://api:8000/api/v1

# Restart LibreChat
docker-compose restart librechat
```

## Next Steps

After successful migration:

1. 📖 Read [Architecture Documentation](./architecture.md)
2. 🧪 Run tests: `docker-compose run --rm api pytest`
3. 📊 Setup monitoring (optional)
4. 🚀 Deploy to production (see deployment guide)

## Support

- GitHub Issues: https://github.com/vta-itsec/Agentic-RAG-chat/issues
- Docs: https://github.com/vta-itsec/Agentic-RAG-chat/tree/main/docs
