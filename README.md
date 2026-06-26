# CPIS V1 — Competitive Product Intelligence System

**竞品公开信息自动采集与分析系统**

CPIS V1 is an internal enterprise system that automatically collects publicly available competitive product information, processes it through AI-powered structured extraction, stores it in a database, synchronizes with Feishu Bitable, and generates briefing reports. It replaces manual competitive intelligence workflows with a semi-automated, configurable pipeline.

**Served teams:** Product Management, Sales, Marketing, R&D, Management

---

## Architecture

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

**Data flow:** URL Input → Compliance Validation → Web Collection → Content Cleaning → AI Structured Extraction → Product Storage & Versioning → Human Review → Feishu Bitable Sync → Briefing Report Generation

See [docs/](./docs/) for detailed architecture documents and phase evidence.

---

## Features

- **Configurable Collection Pipeline** — Define templates to collect data from competitive web pages via pluggable collector runtimes (HTTP/HTML, Playwright, RSS, PDF, API).
- **AI-Powered Structured Extraction** — Leverages OpenAI-compatible LLMs (or stub mode for demos) to extract structured product data from raw HTML/text with confidence scoring.
- **Product Versioning & Diffing** — Tracks changes between successive product snapshots with AI-generated changelogs and diff analysis.
- **Feishu Bitable Integration** — Automatic synchronization of collected product data to Feishu Bitable for team-wide collaboration.
- **Task Scheduler & Async Workers** — Celery-based async task processing for collection jobs with retry policy, execution reports, and monitoring.
- **Dashboard & Usage Tracking** — Frontend dashboard with collection metrics, task execution reports, search history, and collector runtime distribution.
- **One-Command Docker Deployment** — Single `docker compose up -d` to start PostgreSQL, Redis, FastAPI backend, Celery workers, and React frontend.
- **MCP Support** — Model Context Protocol support for AI-assisted discovery and template management.

---

## Quick Start

Get CPIS V1 running locally in under 5 minutes. See the full [Quick Start Guide](release/QUICK_START.md) for detailed instructions.

```bash
# Prerequisites: Docker, Docker Compose, Git

# 1. Clone & configure
git clone <repository-url>
cd Competitive-Product-Intelligence-System
cp .env.example .env
# Edit .env as needed (DB_PASSWORD, LLM_API_KEY, etc.)

# 2. Start all services
docker compose up -d

# 3. Verify health
curl http://localhost:8000/health/live

# 4. Seed demo data (optional, recommended)
docker compose exec backend python scripts/seed_demo.py

# 5. Open the frontend
# → http://localhost:5173 (dev mode)
# → http://localhost:8080  (demo mode via docker-compose.demo.yml)

# 6. Stop
docker compose down
```

The default `LLM_PROVIDER=stub` works out of the box without any API key — ideal for UI demos and pipeline testing.

---

## Demo

A complete walkthrough script for presenters is available at [release/DEMO_SCRIPT.md](release/DEMO_SCRIPT.md). The demo covers:

- **Step 1:** Start the system via Docker Compose
- **Step 2:** Seed demo data (sample products, templates, usage history)
- **Step 3:** Browse products, version history, and AI-generated changelogs
- **Step 4:** Run a collection template and monitor task execution
- **Step 5:** Check the usage dashboard with metrics and search history
- **Optional:** Feishu sync and MCP tool integration

**One-command demo start:**

```bash
./scripts/start_demo.sh
```

This starts all services using `docker-compose.demo.yml`, waits for the backend to be healthy, seeds demo data, and opens the frontend at [http://localhost:8080](http://localhost:8080).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI (Python 3.12) |
| **ORM & Migrations** | SQLAlchemy 2 + Alembic |
| **Database** | PostgreSQL 16 |
| **Cache & Message Broker** | Redis 7 + Celery 5 |
| **Data Collection** | httpx, BeautifulSoup4, lxml, trafilatura, Playwright |
| **Frontend Framework** | React 19 + TypeScript + Vite |
| **UI Component Library** | Ant Design 5 |
| **State Management** | TanStack Query |
| **Form Validation** | React Hook Form + Zod |
| **Logging** | structlog |
| **Quality** | pytest, Ruff, mypy |
| **Infrastructure** | Docker Compose |

---

## Project Structure

```
cpis-v1/
├── backend/
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Configuration, logging, database
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── repositories/   # Data access layer
│   │   ├── services/       # Business logic orchestration
│   │   ├── collectors/     # Web collection runtimes (HTTP, Playwright, RSS, PDF, API)
│   │   ├── cleaners/       # HTML→text, noise removal
│   │   ├── extractors/     # AI-based structured extraction
│   │   ├── analyzers/      # Diff/changelog analysis
│   │   ├── integrations/   # Feishu Bitable sync
│   │   ├── tasks/          # Celery async task definitions
│   │   └── prompts/        # Versioned LLM system prompts
│   ├── alembic/            # Database migrations
│   ├── scripts/            # Utility scripts (seed_demo.py, etc.)
│   └── tests/              # Backend test suite
├── frontend/
│   └── src/
│       ├── api/            # API client calls
│       ├── components/     # Shared UI components
│       ├── features/       # Business feature modules
│       ├── layouts/        # Page layouts
│       ├── routes/         # Route definitions
│       ├── stores/         # State management
│       └── types/          # TypeScript type definitions
├── scripts/                # Start/stop scripts for demo, backend, frontend, worker
├── release/                # Release documentation (QUICK_START.md, DEMO_SCRIPT.md, DEPLOYMENT_GUIDE.md, CHANGELOG.md, LICENSE.md, RELEASE_NOTES.md)
├── docs/                   # Phase execution plans and audit reports
├── docker-compose.yml      # Full system composition
├── docker-compose.demo.yml # Demo-optimized composition
└── .env.example            # Environment variable template
```

---

## Development

- **Backend:** `cd backend && poetry install && uvicorn app.main:app --reload`
- **Frontend:** `cd frontend && npm install && npm run dev`
- **Tests:** `cd backend && pytest`
- **Lint:** `cd backend && ruff check . && mypy .`
- **Migrations:** `cd backend && alembic upgrade head`

See [docs/](./docs/) for detailed development node execution plans and phase evidence.

---

## License

This project is licensed under the MIT License. See [release/LICENSE.md](release/LICENSE.md) for details.
