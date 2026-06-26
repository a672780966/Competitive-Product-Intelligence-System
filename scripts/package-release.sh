#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUTPUT="release/cpis-v1-local-demo.tar.gz"
echo "Creating release package: $OUTPUT"
tar czf "$OUTPUT" \
    --exclude=".env" \
    --exclude=".env.*" \
    --exclude="backend/.venv" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="node_modules" \
    --exclude="frontend/node_modules" \
    --exclude="backend/alembic/versions/__pycache__" \
    --exclude=".git" \
    --exclude=".gitignore" \
    --exclude="release/cpis-v1-local-demo.tar.gz" \
    --exclude="*.tar.gz" \
    backend/ frontend/ docker-compose.yml docker-compose.demo.yml \
    scripts/ release/ README.md .env.example CLAUDE.md
echo "Package created: $(ls -lh $OUTPUT | awk '{print $5}')"
