# CPIS Phase VI — Product Readiness Execution Plan

**Date:** 2026-06-26
**Status:** Plan Document
**Scope:** Release structure, Docker readiness, one-click startup, demo dataset, documentation, packaging, verification.

## Steps

### 1. Create release/ directory structure
Create: `release/RELEASE_NOTES.md`, `release/CHANGELOG.md`, `release/QUICK_START.md`, `release/DEPLOYMENT_GUIDE.md`, `release/DEMO_SCRIPT.md`, `release/LICENSE.md`

### 2. Enhance .env.example
Add Phase V feature flags: `COLLECTOR_PLAYWRIGHT_ENABLED=false`, etc. Add comments.

### 3. Create docker-compose.demo.yml
Simplified demo compose with all-in-one config, demo-optimized settings, no external deps.

### 4. Create startup scripts
- `scripts/start_backend.sh` — start PostgreSQL + Redis + backend
- `scripts/start_frontend.sh` — start frontend dev server
- `scripts/start_worker.sh` — start Celery worker
- `scripts/start_demo.sh` — docker compose up demo
- `scripts/stop_demo.sh` — docker compose down demo

### 5. Create demo seed script
`backend/scripts/seed_demo.py` — creates demo products, versions, reviews, usage, templates.

### 6. Update README.md
Consolidate architecture, deployment instructions, API docs reference.

### 7. Create packaging script
`scripts/package-release.sh` — tar.gz with proper exclusions.

### 8. Release verification
Run pytest, frontend build, alembic current, docker compose config, secret scan, git status.

### 9. Demo verification
Start demo, seed data, verify pipeline.

### 10. Finalize release notes
Record verification results.
