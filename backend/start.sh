#!/bin/bash
# CPIS V1 — Backend startup script
# Runs DB migration, then starts uvicorn

echo "Running database migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
