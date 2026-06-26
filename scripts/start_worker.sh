#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Starting Celery Worker..."
docker compose -f docker-compose.demo.yml up -d celery-worker
echo "Worker started."
