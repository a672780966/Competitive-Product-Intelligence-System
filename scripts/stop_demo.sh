#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Stopping demo..."
docker compose -f docker-compose.demo.yml down
echo "Demo stopped. Volumes preserved — run start_demo.sh to resume."
