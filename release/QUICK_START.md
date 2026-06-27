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

## Quick Start (Recommended)

### 1. Clone and enter the repository

```bash
git clone <repository-url>
cd Competitive-Product-Intelligence-System
```

### 2. Start everything with one command

```bash
bash scripts/start_demo.sh
```

This single command:
- Creates `.env` from `.env.example` (if missing)
- Starts all services (PostgreSQL, Redis, Backend, Celery Worker, Frontend)
- Runs database migrations automatically
- Seeds demo data (products, discovery sessions, collection templates)
- Waits for the backend to be ready (up to 60 seconds)

### 3. Access the frontend

Open [http://localhost:8080](http://localhost:8080) in your browser.

### 4. Verify everything is running

```bash
curl http://localhost:8000/health/live
# Expected: {"status":"ok"}
```

### 5. API Endpoints

| Endpoint | Description |
|----------|-------------|
| `http://localhost:8000/` | API root |
| `http://localhost:8000/docs` | API documentation (Swagger UI) |
| `http://localhost:8000/api/v1/system/provider-status` | Provider configuration status |

---

## Stopping the System

```bash
bash scripts/stop_demo.sh
```

To also remove all data (reset):

```bash
docker compose -f docker-compose.demo.yml down -v
```

---

## Manual Step-by-Step (Alternative)

If you prefer manual control:

### 1. Configure environment variables

```bash
cp .env.example .env
```

### 2. Start all services

```bash
docker compose -f docker-compose.demo.yml up -d
```

### 3. Seed demo data

```bash
docker compose -f docker-compose.demo.yml exec backend python /app/scripts/seed_demo.py
```

---

## Troubleshooting

### "port is already allocated"
Stop the conflicting service, or change port mappings in `docker-compose.demo.yml`.

### Backend fails to start
Check logs:
```bash
docker compose -f docker-compose.demo.yml logs backend
```

### Frontend shows blank page
Ensure the backend is running and the API is accessible:
```bash
curl http://localhost:8000/health/live
```

### Celery tasks not executing
Check worker logs:
```bash
docker compose -f docker-compose.demo.yml logs celery-worker
```

### Reset everything
```bash
docker compose -f docker-compose.demo.yml down -v
bash scripts/start_demo.sh
```
