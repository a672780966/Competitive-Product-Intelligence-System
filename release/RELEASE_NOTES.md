# CPIS V1 — Release Notes

**Version:** 1.0.0
**Date:** 2026-06-26

---

## Overview

CPIS V1 (Competitive Product Intelligence System V1) is an internal enterprise system designed to automatically collect publicly available competitive product information, process it through structured extraction (stub AI provider by default), store it in a database, synchronize with Feishu Bitable, and generate briefing reports. It replaces manual competitive intelligence workflows with a semi-automated, configurable pipeline.

---

## Features

### ✅ Real / Production-Ready

- **Direct HTTP Collection (Enhanced)** — Robust HTTP/HTML scraper with UA rotation pool (5 real browser UAs), gzip/brotli support, charset auto-detection, separated timeouts (connect/read/write/pool), and exponential-backoff retry with jitter. Covers 11 failure classifications via Failure Intelligence.
- **Sitemap & Robots.txt Discovery** — Automatic URL discovery via `sitemap.xml` and `robots.txt` with recursive index parsing and configurable `max_urls` limits.
- **Collector Runtime Framework** — Pluggable architecture with registry, selector, retry policy, and execution reports. Supports HTTP runtime natively; Playwright, Scrapling, Crawl4AI, RSS, PDF, API runtimes available as feature-flagged placeholders.
- **Collector Execution Reports** — Per-collector metrics (success/failure counts, duration, error messages) with full path coverage (blocked/started/failed/success/exception).
- **Feishu Bitable Sync** — Authenticated OAuth 2.0 integration with Feishu Bitable for team collaboration. ✅ Verified write capability.
- **DuckDuckGo Discovery Provider** — Search-based discovery provider for finding competitive product URLs. Code-ready but not independently verified in production.
- **Product Versioning & Diffing** — Tracks changes between successive product snapshots with AI-generated changelogs (requires LLM configuration).
- **Celery Task Scheduler** — Built-in Celery worker for asynchronous collection task execution.
- **Frontend Dashboard** — React 19 + TypeScript + Ant Design 5 frontend with product catalog, collection templates, usage metrics, and search history.
- **MCP (Model Context Protocol) Support** — AI-assisted discovery and template management via MCP tools.
- **Hermes Skills Integration** — Hermes Agent skills for automated workflows.
- **Docker Compose Deployment** — One-command infrastructure with PostgreSQL 16, Redis 7, FastAPI backend, and React frontend.
- **Release Documentation** — Comprehensive QUICK_START.md, DEPLOYMENT_GUIDE.md, DEMO_SCRIPT.md, CHANGELOG.md, LICENSE.md.

### ⚠️ Available with Configuration / Feature Flags

- **LLM AI Extraction** — Default **stub provider** (`LLM_PROVIDER=stub`) returns mock extractions without requiring an API key. Set `LLM_PROVIDER=openai` (or ollama/azure/vllm/localai) and configure `LLM_API_KEY` / `LLM_BASE_URL` for real AI extraction.
- **Playwright Collector** — Feature-flagged (`COLLECTOR_PLAYWRIGHT_ENABLED=false` by default). Requires Playwright system dependencies. Needed for JavaScript-rendered pages and anti-bot bypass.
- **Scrapling / Crawl4AI Collectors** — Feature-flagged experimental runtimes. Not enabled or tested for this release.
- **RSS / PDF / API Collectors** — Feature-flagged (`COLLECTOR_*_ENABLED=false` by default). Available for configuration.

### ❌ Not Supported (v1.0.0)

- **Scheduled Scraping** — Celery scheduler framework is present but recurring schedule-based collection is not wired into the default release workflow.
- **User Authentication / RBAC** — No authentication, authorization, or multi-tenant support. Intended for internal/trusted-network use.
- **SaaS / Cloud Hosting** — The system is designed for local or self-hosted Docker deployment only.
- **Social Media Collection** — Twitter, LinkedIn, and other social platforms are not supported as data sources.
- **Commercial License** — Distributed under the MIT License.

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
                    ┌───────┴──────────────────┐
                    │  Collectors              │
                    │  · HTTP/HTML     (✅)    │
                    │  · Playwright    (⚙️ FF) │
                    │  · Sitemap/Robots (✅)   │
                    │  · RSS           (⚙️ FF) │
                    │  · PDF           (⚙️ FF) │
                    │  · API           (⚙️ FF) │
                    └──────────────────────────┘
```

**Legend:** ✅ = Real & enabled | ⚙️ FF = Feature-flagged, disabled by default

**Key modules:** `collectors/` (data fetching), `cleaners/` (noise removal), `extractors/` (AI extraction, stub by default), `analyzers/` (diff/changelog), `integrations/` (Feishu sync), `tasks/` (Celery workers), `prompts/` (versioned LLM prompts), `repositories/` (data access), `services/` (business logic orchestration).

---

## Quick Start Reference

```bash
# Prerequisites: Docker, Docker Compose, Git

# 1. Clone & setup
git clone <repo-url>
cd Competitive-Product-Intelligence-System
cp .env.example .env
# Edit .env: set DB_PASSWORD, optionally configure LLM_API_KEY

# 2. Start (Demo Mode)
bash scripts/start_demo.sh

# 3. Verify health
curl http://localhost:8000/health/live

# 4. Access
#   Frontend: http://localhost:8080
#   API:      http://localhost:8000
#   Docs:     http://localhost:8000/docs

# 5. Stop
bash scripts/stop_demo.sh
```

See [QUICK_START.md](./QUICK_START.md) for detailed instructions and [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for production setup.

---

## Milestones (Completed)

| Phase | Description | Status |
|-------|-------------|--------|
| Phase I-Reset | Discovery, Templates, Scheduler, Usage, MCP | ✅ Complete |
| Phase II | Maden Verification with real URLs | ✅ Complete |
| Phase III | Small Sample + 马登工装真实采集 (Madenwear.com) | ✅ Complete |
| Phase IV | AI Discovery Provider Layer (DuckDuckGo) | ✅ Complete |
| Phase V | Collector Runtime Enhancement (Registry, Retry, Reports) | ✅ Complete |
| Phase VI | Product Readiness (Release Docs, Feature Flags) | ✅ Complete |
| Phase VII | Crawler Capability Upgrade (DirectHTTP 8 enhancements, Failure Intelligence, Sitemap Discovery) | ✅ Complete |
| Product Usability Hardening | Seed API 405/500 fix, demo compose reliability, Docker build recovery, error message audit, auto-migration, real URL E2E, artifact completeness | ✅ Complete |

### Upcoming

| Phase | Description | Status |
|-------|-------------|--------|
| Phase VIII | Real LLM Provider Integration | 📋 Planned |
| Phase IX | Enterprise Features (RBAC, Multi-tenant) | 📋 Planned |

---

## Known Limitations

| Limitation | Detail | Workaround |
|------------|--------|------------|
| **Stub AI provider by default** | `LLM_PROVIDER=stub` returns mock extractions | Set `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` for real AI |
| **Playwright not enabled by default** | JS-rendered pages and some anti-bot sites may fail | Set `COLLECTOR_PLAYWRIGHT_ENABLED=true` + install Playwright deps |
| **Some sites block HTTP scraping** | baike.baidu.com (403 WAF), smzdm.com (JS challenge) | Requires Playwright or alternative data source |
| **No authentication** | System is open on trusted networks | Deploy behind reverse proxy with auth |
| **No scheduled scraping** | Manual trigger required per collection | Use Celery beat configuration in custom deployment |
| **Single-threaded collection** | Without sufficient Celery workers, throughput is limited | Scale `deploy.replicas` for celery-worker service |
| **Limited error recovery** | Automatic retry implemented (3 retries, exponential backoff) | Manual intervention may be needed for persistent failures |
| **Frontend is demo-ready** | Core workflows covered; advanced filtering/admin panels pending | Future releases will address |

---

## Non-Goals (v1.0.0)

The following items are explicitly out of scope for this release:

- **Social media collection** — Twitter, LinkedIn, etc. are not supported as data sources.
- **Scrapling/Crawl4AI in v1** — Feature-flagged placeholders, not enabled or tested.
- **Scheduled scraping** — Celery scheduler infrastructure present but not wired into default workflow.
- **SaaS frontend** — Local or self-hosted deployment only; no cloud/SaaS offering.
- **Commercial license** — MIT License; no commercial licensing option available.
- **User authentication** — No RBAC, multi-tenant, or auth layer.
- **Real LLM provider** — Requires separate configuration and API key.

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for full version history.
