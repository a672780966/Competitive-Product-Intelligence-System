# CHANGELOG

All notable changes to CPIS V1 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-06-26 — Phase VI: Product Readiness

### Added
- **Release documentation** — RELEASE_NOTES.md, CHANGELOG.md, QUICK_START.md, DEPLOYMENT_GUIDE.md, DEMO_SCRIPT.md, LICENSE.md.
- **Feature flags** — Collector runtime feature flags added to `.env.example` for Playwright, Scrapling, Crawl4AI, RSS, PDF, and API runtimes (`COLLECTOR_*_ENABLED=false`).
- **Default stub AI provider** — `LLM_PROVIDER=stub` set as default so the system runs without an API key for demos.

### Changed
- `.env.example` updated with Phase V collector runtime feature toggles and LLM_PROVIDER default.

---

## [0.1.0-rc.5] — 2026-06-25 — Phase V: Collector Runtime Enhancement

### Added
- **Collector execution reports** — New `collector_execution_report` model to track per-collector execution metrics (success/failure counts, duration, error messages).
- **Collector runtime registry** — `collectors/registry.py` for registering and looking up collector implementations by source type.
- **Collector runtime implementations:**
  - `api_runtime.py` — REST API collector for JSON/XML endpoints.
  - `pdf_runtime.py` — PDF document collector with text extraction.
  - `rss_runtime.py` — RSS/Atom feed collector.
  - `scrapling_runtime.py` — Scrapling-based dynamic page collector (feature-flagged, not enabled by default).
  - `crawl4ai_runtime.py` — Crawl4AI-based collector (feature-flagged, not enabled by default).
- **Collector retry policy** — `collectors/retry_policy.py` with configurable retry logic and exponential backoff.
- **Selector-based routing** — `collectors/selector.py` for automatic runtime selection based on URL/content type.
- **Task service enhancements** — `services/task_service.py` with improved collection task orchestration.
- **Alembic migrations** — `005_add_collector_execution_reports.py` and `006_add_collection_task_source_type.py` for new schemas.
- **API endpoints** — Task management endpoints (`/api/tasks/`) for creating and monitoring collection tasks.
- **Comprehensive test suite** — `test_collectors.py`, `test_phase_v.py`, and pipeline tests covering collector integration, retries, idempotency, and failure scenarios.

---

## [0.1.0-rc.4] — 2026-06-24 — Phase IV: AI Discovery Provider Layer

### Added
- **Discovery provider interface** — `providers/interfaces.py` defining the abstract base for AI-powered discovery providers.
- **Search history tracking** — `models/search_history.py`, `repositories/search_history_repository.py`, and corresponding tests.
- **Discovery provider tests** — `test_discovery_providers.py`, `test_providers_phase4.py` for provider integration verification.
- **Phase 4 test suite** — Validates AI discovery provider layer functionality, including search history recording and provider abstraction.

---

## [0.1.0-rc.3] — 2026-06-23 — Phase III: Small Sample

### Added
- Small-sample data validation and pipeline integration testing.
- Refined collection pipeline for end-to-end sample runs.
- Bug fixes and edge case handling from Phase II verification findings.

### Fixed
- Pipeline failure modes addressed (see `test_pipeline_failures.py`).
- Idempotency improvements in collection task processing.

---

## [0.1.0-rc.2] — 2026-06-22 — Phase II: Maden Verification

### Added
- Verification suite for the "Maden" (麻登) competitive intelligence use case.
- End-to-end pipeline verification with real-world sample URLs.
- Collection → Cleaning → AI Extraction → Product Versioning data flow validation.

---

## [0.1.0-rc.1] — 2026-06-21 — Phase I-Reset: Discovery, Templates, Scheduler, Usage, MCP

### Added
- **Discovery module** — Initial discovery framework for finding new competitive product URLs.
- **Collection templates** — Template-based collection configuration allowing reusable collection workflows.
- **Task scheduler integration** — Celery-based scheduling infrastructure wired into the application.
- **Usage tracking** — Dashboard usage metrics and logging infrastructure.
- **MCP (Model Context Protocol) support** — AI-assisted capabilities for discovery and template management.
- **Search history** — Initial search history recording for discovery queries.

---

## [0.0.9] — 2026-06-20 — Phase I: Feishu, Small Sample

### Added
- **Feishu integration** — Application integration with Feishu Bitable for synchronizing collected product data.
  - Feishu API client with OAuth 2.0 authentication.
  - Bitable record creation and update operations.
- **Small sample collection** — Initial small-scale collection pipeline for testing end-to-end flow.
- Frontend improvements for feishu sync status display.

---

## [0.0.8] — 2026-06-19 — Phase H: OpenClaw Integration

### Added
- **OpenClaw integration** — Integration with the OpenClaw data collection framework.
- Enhanced collector orchestration leveraging OpenClaw capabilities.
- Test suite updates for OpenClaw integration paths.

---

## [0.0.7] — 2026-06-18 — Phases A-G: Infrastructure, OpenClaw, Docker

### Added
- **Phase A — Project scaffolding**
  - FastAPI backend skeleton with modular application structure.
  - Poetry dependency management.
  - SQLAlchemy 2.0 ORM setup with async support.
  - Alembic migration framework initialized.
- **Phase B — Database models**
  - Core data models: products, collections, product versions.
  - Repository pattern for data access layer.
  - Timestamp mixin for all models.
- **Phase C — Collection pipeline**
  - HTTP/HTML collector using httpx + BeautifulSoup4.
  - HTML cleaner for noise removal.
  - AI extractor framework with prompt versioning.
- **Phase D — AI extraction**
  - OpenAI-compatible LLM integration.
  - Structured extraction with Pydantic schemas.
  - Confidence threshold scoring (0.7 threshold).
- **Phase E — Frontend foundation**
  - React 19 + TypeScript + Vite project setup.
  - Ant Design 5 component library integration.
  - TanStack Query for API data fetching.
  - React Hook Form + Zod for form validation.
- **Phase F — Docker Compose orchestration**
  - Multi-service Docker Compose configuration.
  - PostgreSQL 16, Redis 7 services.
  - Celery worker configuration.
  - Volume mounts for persistent data.
- **Phase G — API layer & integrations**
  - RESTful API endpoints for CRUD operations.
  - Feishu integration preparation.
  - Celery task worker integration.

---

## [0.0.1] — 2026-06-01 — Project Initialization

### Added
- Initial repository structure.
- Project README and CLAUDE.md documentation.
- Basic Python and Node.js environment configuration.
