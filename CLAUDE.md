# CPIS V1 — CLAUDE.md

## Project Overview

CPIS V1 = Competitive Product Intelligence System V1（竞品公开信息自动采集与分析系统）。
企业内部系统，采集公开竞品页面 → AI 结构化 → 入库 → 飞书同步 → 简报生成。

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Redis 7, Celery 5
- **Data Collection:** httpx, BeautifulSoup4, lxml, trafilatura, Playwright
- **Frontend:** React 19, TypeScript, Vite, Ant Design 5, TanStack Query, React Hook Form + Zod
- **Infrastructure:** Docker Compose
- **Quality:** pytest, Ruff, mypy

## Commands

### Backend
- Install: `cd backend && poetry install`
- Dev server: `cd backend && uvicorn app.main:app --reload`
- Test: `cd backend && pytest`
- Lint: `cd backend && ruff check . && mypy .`
- Migrate: `cd backend && alembic upgrade head`

### Frontend
- Install: `cd frontend && npm install`
- Dev: `cd frontend && npm run dev`
- Build: `cd frontend && npm run build`

### Docker
- Start all: `docker compose up -d`
- Logs: `docker compose logs -f`

## Architecture

### Module Responsibilities
- **collectors/** — HTTP fetch + Playwright render
- **cleaners/** — HTML→text, noise removal
- **extractors/** — AI-based structured extraction
- **analyzers/** — Diff/changelog between product versions
- **integrations/** — Feishu Bitable sync
- **tasks/** — Celery async workers
- **prompts/** — LLM system prompts (versioned)
- **repositories/** — Data access layer (SQLAlchemy)
- **services/** — Business logic orchestration

### Data Flow
URL Input → URLValidation → Collection → Cleaning → AIExtraction → ProductVersioning → HumanReview → FeishuSync → ReportGeneration

### Key Conventions
- All DB models use `created_at` / `updated_at` timestamps (TimestampMixin)
- Pydantic schemas for all API input/output (no raw dicts)
- Repository pattern for DB access (services don't touch SQLAlchemy directly)
- Celery tasks for all async/background work
- LLM prompts versioned in prompts/ directory
- Confidence threshold for auto-pass vs human review: 0.7

## Branching (when needed)
- `main` — stable, production
- `feat/<node-number>-<short-name>` — feature branches

## Reference
- Development nodes: `../cpis_v1_development_nodes/`
- Spec doc: `../竞品公开信息自动采集与分析系统-V1-开发规格说明.md`
