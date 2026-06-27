#!/usr/bin/env bash
# Build CPIS demo images using buildx --output type=docker
# This bypasses the containerd-native snapshotter bug in Docker 29.x
# where COPY --from=builder with large directories causes
# "wrong diff id calculated on extraction" error.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Building backend image ==="
docker buildx build --output type=docker --no-cache \
  -f backend/Dockerfile \
  -t cpis-backend \
  backend/

echo "=== Building frontend image ==="
docker buildx build --output type=docker --no-cache \
  -f frontend/Dockerfile \
  -t cpis-frontend \
  frontend/

echo "=== Images built ==="
sg docker -c 'docker images cpis-backend cpis-frontend 2>&1' || docker images cpis-backend cpis-frontend
