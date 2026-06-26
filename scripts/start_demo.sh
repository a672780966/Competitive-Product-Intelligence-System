#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== CPIS V1 Demo ==="
echo "Starting all services..."
docker compose -f docker-compose.demo.yml up -d
echo "Waiting for backend..."
until curl -sf http://localhost:8000/health/live > /dev/null 2>&1; do sleep 2; done
echo "Seeding demo data..."
docker compose -f docker-compose.demo.yml exec -T backend python /app/scripts/seed_demo.py 2>/dev/null || true
echo ""
echo "=== Demo Ready ==="
echo "  Frontend: http://localhost:8080"
echo "  API:      http://localhost:8000"
echo "  Docs:     http://localhost:8000/docs"
