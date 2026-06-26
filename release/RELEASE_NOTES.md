# CPIS V1 — Release Notes

**Version:** 0.1.0  
**Date:** 2026-06-26

---

## Overview

CPIS V1 (Competitive Product Intelligence System V1) is an internal enterprise system designed to automatically collect publicly available competitive product information, process it through structured extraction (stub AI provider by default), store it in a database, synchronize with Feishu Bitable, and generate briefing reports. It replaces manual competitive intelligence workflows with a semi-automated, configurable pipeline.

---

## Features

- **Configurable Collection Pipeline** — Define templates to collect data from competition web pages via HTTP/HTML scraping.
- **Structured Extraction Framework** — Extractor pipeline with stub AI provider. Real LLM integration pending.
- **Product Versioning & Diffing** — Tracks changes between successive product snapshots with stub changelogs currently.
- **Feishu Integration** — Syncs collected product data to Feishu Bitable for team collaboration.
- **Task Scheduler** — Built-in Celery task scheduler for recurring collection jobs.
- **Dashboard & Usage Tracking** — Frontend dashboard with usage metrics and search history.
- **Collector Runtime Framework** — Pluggable collector architecture with support for multiple runtime types (HTTP, Playwright, RSS, PDF, API).
- **MCP Support** — Model Context Protocol support for AI-assisted discovery and template management.
- **Docker Compose Deployment** — One-command infrastructure setup with PostgreSQL, Redis, Celery workers, and FastAPI backend.

---

## Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Frontend    │────▶│  FastAPI     │────▶│  PostgreSQL  │
│  (React 19)  │     │  Backend     │     │  (Database)  │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                    ┌───────┴────────┐
                    │  Celery Workers │
                    │  (Async Tasks)  │
                    └───────┬────────┘
                            │
                    ┌───────┴────────┐
                    │  Collectors    │
                    │  · HTTP/HTML   │
                    │  · Playwright  │
                    │  · RSS         │
                    │  · PDF         │
                    │  · API         │
                    └────────────────┘
```

**Key modules:** `collectors/` (data fetching), `cleaners/` (noise removal), `extractors/` (AI extraction), `analyzers/` (diff/changelog), `integrations/` (Feishu sync), `tasks/` (Celery workers), `prompts/` (versioned LLM prompts), `repositories/` (data access), `services/` (business logic orchestration).

---

## Quick Start Reference

```bash
# Prerequisites: Docker, Docker Compose, Git

# 1. Clone & setup
git clone <repo-url>
cd Competitive-Product-Intelligence-System
cp .env.example .env
# Edit .env: set DB_PASSWORD, optionally configure LLM_API_KEY

# 2. Start the system
docker compose up -d

# 3. Verify health
curl http://localhost:8000/health/live

# 4. Seed demo data
docker compose exec backend python scripts/seed_demo.py

# 5. Visit http://localhost:5173 for the frontend

# 6. Stop
docker compose down
```

See [QUICK_START.md](./QUICK_START.md) for detailed instructions and [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for production setup.

---

## Known Limitations

- **Stub AI provider by default** — The default `LLM_PROVIDER=stub` returns mock extractions without requiring an API key, suitable for UI demos and pipeline testing but not production use.
- **Single-threaded collection** — Without a Celery worker pool sufficiently sized, collection throughput may be limited.
- **No authentication/authorization** — The v0.1.0 release does not include user authentication or RBAC; it is intended for internal/trusted-network use.
- **Limited error recovery** — Automatic retry is implemented (3 retries with exponential backoff), but manual intervention may be required for persistent failures.
- **Frontend is demo-ready, not feature-complete** — The React frontend covers core workflows; advanced filtering, pagination improvements, and admin panels are planned for future releases.

---

## Non-Goals (v0.1.0)

The following items are explicitly out of scope for this release and will not be included:

- **No social media collection** — Social media platforms (Twitter, LinkedIn, etc.) are not supported as data sources.
- **No Scrapling/Crawl4AI in v1** — The Scrapling and Crawl4AI collector runtimes exist as feature-flagged placeholders but are not enabled or tested for this release.
- **No scheduled scraping** — While the Celery scheduler infrastructure is present, recurring schedule-based collection is not wired into the default release workflow.
- **No SaaS frontend** — The system is designed for local or self-hosted deployment; no cloud/SaaS offering is provided.
- **No commercial license** — The project is distributed under the MIT License; no commercial licensing option is available.
