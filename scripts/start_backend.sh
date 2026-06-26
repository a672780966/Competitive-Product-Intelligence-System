#!/usr/bin/env bash
set -euo pipefail
# Start CPIS backend services (PostgreSQL + Redis + Backend API)
cd "$(dirname "$0")/.."
echo "Starting PostgreSQL and Redis..."
docker compose -f docker-compose.demo.yml up -d postgres redis
echo "Waiting for PostgreSQL to be healthy..."
until docker compose -f docker-compose.demo.yml exec -T postgres pg_isready -U cpis 2>/dev/null; do sleep 2; done
echo "Starting Backend API..."
docker compose -f docker-compose.demo.yml up -d backend
echo "Backend API running at http://localhost:8000"
