#!/bin/bash
# Stop all services

cd "$(dirname "$0")/../.."
docker-compose -f infrastructure/docker/docker-compose.yml down
