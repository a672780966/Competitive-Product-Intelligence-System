#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Starting Frontend..."
docker compose -f docker-compose.demo.yml up -d frontend
echo "Frontend running at http://localhost:8080"
