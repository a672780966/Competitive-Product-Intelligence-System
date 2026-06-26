# CPIS V1 — Quick Start Guide

Get CPIS V1 running on your local machine in under 5 minutes.

---

## Prerequisites

| Requirement   | Version | Notes                                         |
|---------------|---------|-----------------------------------------------|
| **Docker**    | 24+     | [Install Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | v2+ | Included with Docker Desktop; standalone install on Linux |
| **Git**       | 2.30+   | [Install Git](https://git-scm.com/downloads)   |
| **curl**      | any     | For verifying the health endpoint              |

Verify your setup:

```bash
docker --version
docker compose version
git --version
```

---

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd Competitive-Product-Intelligence-System
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit the `.env` file:

- **Required:** Set a strong password for the database:
  ```bash
  DB_PASSWORD=your-strong-password-here
  ```
- **Optional — AI features:** If you want real AI extraction (not stub), set:
  ```bash
  LLM_PROVIDER=openai
  LLM_API_KEY=sk-your-api-key-here
  LLM_MODEL=gpt-4o
  ```
- **Optional — Feishu integration:** Configure Feishu app credentials for syncing to Bitable.

> **Note:** The default `LLM_PROVIDER=stub` works out of the box without any API key — it returns mock data suitable for testing the UI and pipeline flow.

### 3. Start the system

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** — database
- **Redis 7** — cache and Celery broker
- **FastAPI backend** — API server (port 8000)
- **React frontend** — web UI (port 5173)
- **Celery worker** — async task processor

### 4. Verify the system is running

```bash
curl http://localhost:8000/health/live
```

Expected response:
```json
{"status":"ok"}
```

### 5. Check all services are up

```bash
docker compose ps
```

All services should show `Up` status.

### 6. Seed demo data (optional but recommended)

```bash
docker compose exec backend python scripts/seed_demo.py
```

This populates the database with sample competitive products, collection templates, and usage history for exploration.

### 7. Access the frontend

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Stopping the System

```bash
docker compose down
```

To also remove volumes (destroy all data):
```bash
docker compose down -v
```

---

## Troubleshooting

### "port is already allocated"
Stop the conflicting service on port 8000 or 5173, or change the port mapping in `docker-compose.yml`.

### Backend health check fails
Check the backend logs:
```bash
docker compose logs backend
```

### Database connection errors
Ensure the database has started fully (may take a few seconds):
```bash
docker compose logs postgres
docker compose restart backend
```

### "No such service" when running seed
Ensure all services are running:
```bash
docker compose up -d
```

### Cannot access frontend
Check if the frontend container is running:
```bash
docker compose ps frontend
docker compose logs frontend
```

### Celery tasks not executing
Verify the Celery worker is connected:
```bash
docker compose logs celery_worker
```

### Reset everything
```bash
docker compose down -v
docker compose up -d
# Re-run seed
docker compose exec backend python scripts/seed_demo.py
```
