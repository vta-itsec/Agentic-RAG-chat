#!/bin/bash
# Start all services with proper env file

cd "$(dirname "$0")/../.."
docker-compose -f infrastructure/docker/docker-compose.yml --env-file .env up -d
