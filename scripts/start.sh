#!/usr/bin/env bash
# CPIS V1 — Quick start script
# Usage: bash scripts/start.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "========================================"
echo "  CPIS V1 — 竞品信息采集与分析系统"
echo "========================================"
echo ""

# 1. Check .env
if [ ! -f .env ]; then
  echo "[1/4] Creating .env from .env.example..."
  cp .env.example .env
  echo "  → .env created. Please edit it with your API keys before starting."
  echo "  → Required: LLM_API_KEY"
  echo "  → Optional: FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BITABLE_TOKEN"
  echo ""
else
  echo "[1/4] .env found."
fi

# 2. Build and start services
echo "[2/4] Building and starting services..."
docker compose up -d --build
echo ""

# 3. Run database migrations
echo "[3/4] Running database migrations..."
docker compose run --rm migrate
echo ""

# 4. Verify health
echo "[4/4] Verifying service health..."
sleep 3
if curl -sf http://localhost:8000/health/live > /dev/null 2>&1; then
  echo "  ✅ Backend API:    http://localhost:8000"
  echo "  ✅ API Docs:       http://localhost:8000/docs"
  echo "  ✅ Frontend:       http://localhost:3000"
else
  echo "  ⚠️  Backend still starting — check with: docker compose logs -f"
fi

echo ""
echo "Useful commands:"
echo "  docker compose logs -f     View logs"
echo "  docker compose ps          Service status"
echo "  docker compose down        Stop all services"
echo "  docker compose run --rm migrate   Run migrations"
echo "  docker compose exec backend alembic upgrade head   Manual migration"
echo "  docker compose exec worker celery -A app.tasks.worker inspect active"
echo ""
echo "Done!"
