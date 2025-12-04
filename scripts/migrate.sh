#!/bin/bash

# Migration Script: Old structure → New structure
# This script helps migrate from the old structure to the new SaaS architecture

set -e

echo "🚀 Enterprise RAG Chat - Migration Script"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Stopping old containers...${NC}"
docker-compose down

echo -e "${GREEN}✓ Old containers stopped${NC}"
echo ""

echo -e "${YELLOW}Step 2: Backing up data...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup important files
cp -r data/ "$BACKUP_DIR/" 2>/dev/null || echo "No data directory found"
cp .env "$BACKUP_DIR/.env" 2>/dev/null || echo "No .env file found"
cp providers.yaml "$BACKUP_DIR/providers.yaml" 2>/dev/null || echo "No providers.yaml found"
cp librechat.yaml "$BACKUP_DIR/librechat.yaml" 2>/dev/null || echo "No librechat.yaml found"

echo -e "${GREEN}✓ Backup created in $BACKUP_DIR/${NC}"
echo ""

echo -e "${YELLOW}Step 3: Setting up new structure...${NC}"

# Copy old docker-compose.yml to legacy/
mkdir -p legacy
mv docker-compose.yml legacy/docker-compose.old.yml 2>/dev/null || true

# Symlink new docker-compose.yml
ln -sf infrastructure/docker/docker-compose.yml docker-compose.yml

echo -e "${GREEN}✓ New structure configured${NC}"
echo ""

echo -e "${YELLOW}Step 4: Building new containers...${NC}"
docker-compose build

echo -e "${GREEN}✓ Containers built${NC}"
echo ""

echo -e "${YELLOW}Step 5: Starting services...${NC}"
docker-compose up -d

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Check services: docker-compose ps"
echo "2. View logs: docker-compose logs -f api"
echo "3. Access UI: http://localhost:3080"
echo "4. API Docs: http://localhost:8000/docs"
echo ""
echo "Old structure backed up in: $BACKUP_DIR/"
echo ""
