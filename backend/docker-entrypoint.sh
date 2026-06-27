#!/usr/bin/env bash
set -euo pipefail

# Run migrations if RUN_MIGRATIONS env is set to true
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
  echo "Migrations complete."
fi

exec "$@"
