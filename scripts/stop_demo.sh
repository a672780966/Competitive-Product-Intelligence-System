#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Stopping demo..."
docker compose -f docker-compose.demo.yml down --remove-orphans
echo "Demo stopped. Volumes preserved — run start_demo.sh to resume."
echo "To also reset data, add the -v flag: docker compose -f docker-compose.demo.yml down -v"
