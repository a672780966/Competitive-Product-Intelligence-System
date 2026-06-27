#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Auto-create .env from .env.example if missing
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[INFO] Created .env from .env.example — edit DB_PASSWORD if needed."
    else
        echo "ERROR: Neither .env nor .env.example found."
        exit 1
    fi
fi

# Check if Docker images exist; build if missing
BACKEND_IMAGE_EXISTS=false
FRONTEND_IMAGE_EXISTS=false
if command -v sg &>/dev/null; then
    sg docker -c "docker image inspect cpis-backend:latest >/dev/null 2>&1" && BACKEND_IMAGE_EXISTS=true || true
    sg docker -c "docker image inspect cpis-frontend:latest >/dev/null 2>&1" && FRONTEND_IMAGE_EXISTS=true || true
else
    docker image inspect cpis-backend:latest >/dev/null 2>&1 && BACKEND_IMAGE_EXISTS=true || true
    docker image inspect cpis-frontend:latest >/dev/null 2>&1 && FRONTEND_IMAGE_EXISTS=true || true
fi

if [ "$BACKEND_IMAGE_EXISTS" = false ] || [ "$FRONTEND_IMAGE_EXISTS" = false ]; then
    echo "[BUILD] Docker images not found — building with buildx..."
    echo "  (This uses buildx --output type=docker to bypass containerd native snapshotter bug)"
    bash scripts/build-images.sh
fi

echo "=== CPIS V1 Demo ==="
echo "Starting all services..."
if command -v sg &>/dev/null; then
    sg docker -c "docker compose -f docker-compose.demo.yml up -d"
else
    docker compose -f docker-compose.demo.yml up -d
fi
echo "Waiting for backend (up to 60s)..."
for i in $(seq 1 30); do
    if command -v sg &>/dev/null; then
        HEALTH_OK=$(sg docker -c "curl -sf http://localhost:8000/health/live > /dev/null 2>&1" && echo "ok" || echo "fail")
    else
        HEALTH_OK=$(curl -sf http://localhost:8000/health/live > /dev/null 2>&1 && echo "ok" || echo "fail")
    fi
    if [ "$HEALTH_OK" = "ok" ]; then
        echo "Backend ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Backend failed to start within 60s. Check:"
        echo "  docker compose -f docker-compose.demo.yml logs backend"
        exit 1
    fi
    sleep 2
done
echo "Seeding demo data..."
if command -v sg &>/dev/null; then
    sg docker -c "docker compose -f docker-compose.demo.yml exec -T backend python /app/scripts/seed_demo.py"
else
    docker compose -f docker-compose.demo.yml exec -T backend python /app/scripts/seed_demo.py
fi
echo ""
echo "=== Demo Ready ==="
echo "  Frontend: http://localhost:8080"
echo "  API:      http://localhost:8000"
echo "  Docs:     http://localhost:8000/docs"
