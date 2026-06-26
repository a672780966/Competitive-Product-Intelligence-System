# CPIS V1 — Deployment Guide

This guide covers production deployment considerations for CPIS V1.

---

## 1. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | `CPIS V1` | Application display name |
| `APP_VERSION` | No | `0.1.0` | Application version |
| `DEBUG` | No | `false` | Enable debug logging (`true`/`false`) |
| `ENVIRONMENT` | No | `production` | Runtime environment label |
| `SECRET_KEY` | **Yes** | — | Random string for session signing and encryption |
| `DATABASE_URL` | **Yes** | — | PostgreSQL DSN (asyncpg). See Database Setup below |
| `DB_PASSWORD` | **Yes** | — | PostgreSQL password used in DATABASE_URL |
| `REDIS_URL` | **Yes** | — | Redis connection string |
| `CELERY_BROKER_URL` | **Yes** | — | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | **Yes** | — | Redis URL for Celery result backend |
| `LLM_PROVIDER` | No | `stub` | AI provider: `openai`, `ollama`, `azure`, `vllm`, `localai`, or `stub` |
| `LLM_API_KEY` | Conditional | — | API key for the configured LLM provider |
| `LLM_MODEL` | Conditional | `gpt-4o` | Model name for the LLM provider |
| `LLM_BASE_URL` | No | — | Custom base URL for OpenAI-compatible API |
| `FEISHU_APP_ID` | Conditional | — | Feishu app ID for Bitable sync |
| `FEISHU_APP_SECRET` | Conditional | — | Feishu app secret for Bitable sync |
| `FEISHU_BITABLE_TOKEN` | Conditional | — | Feishu Bitable token for data sync |
| `COLLECTION_TIMEOUT_SECONDS` | No | `60` | Max seconds per collection request |
| `COLLECTION_MAX_RETRIES` | No | `3` | Max retry attempts per collection |
| `COLLECTOR_PLAYWRIGHT_ENABLED` | No | `false` | Enable Playwright collector runtime |
| `COLLECTOR_SCRAPLING_ENABLED` | No | `false` | Enable Scrapling collector runtime |
| `COLLECTOR_CRAWL4AI_ENABLED` | No | `false` | Enable Crawl4AI collector runtime |
| `COLLECTOR_RSS_ENABLED` | No | `false` | Enable RSS collector runtime |
| `COLLECTOR_PDF_ENABLED` | No | `false` | Enable PDF collector runtime |
| `COLLECTOR_API_ENABLED` | No | `false` | Enable API collector runtime |

---

## 2. Production Checklist

### Database Setup

- Use **managed PostgreSQL** (e.g., AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL) or a dedicated PostgreSQL 16 instance.
- Set strong `DB_PASSWORD` (generate via `openssl rand -base64 32`).
- Ensure the database user has limited privileges (no `SUPERUSER`).
- Enable **SSL/TLS** for database connections:
  ```
  DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/cpis?ssl=require
  ```
- Configure **automated backups** (see §6 below).
- Set `max_connections` appropriately for your instance size (start with 100).

### Redis Setup

- Use **managed Redis** (e.g., AWS ElastiCache, Redis Cloud, Azure Cache for Redis) or a dedicated Redis 7 instance.
- Set a strong **Redis password** using `REQUIREPASS`.
- Enable **TLS** for Redis connections where available.
- Use separate Redis DB numbers or separate instances for:
  - `db 0` — application cache (REDIS_URL)
  - `db 1` — Celery broker (CELERY_BROKER_URL)
  - `db 2` — Celery result backend (CELERY_RESULT_BACKEND)

### Celery Worker Configuration

- **Concurrency:** Start with `--concurrency=4` and adjust based on workload:
  ```yaml
  # docker-compose override example
  celery_worker:
    command: celery -A app.tasks worker --loglevel=info --concurrency=4
  ```
- **Task result TTL:** Configure `result_expires` to avoid filling Redis:
  ```python
  app.conf.result_expires = 3600  # 1 hour
  ```
- **Rate limiting:** Apply per-task rate limits for heavy collection operations.
- **Monitoring:** Use Flower or Celery events for worker monitoring (see §8).

### Feishu Integration Configuration

1. Create a Feishu app at [Feishu Developer Console](https://open.feishu.cn/app).
2. Enable permissions: `bitable:app`, `drive:drive`, `contact:user.employee_id`.
3. Set `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, and `FEISHU_BITABLE_TOKEN`.
4. Grant admin access to the target bitable.
5. Test synchronization with a single record before enabling bulk sync.

---

## 3. Docker Compose for Production

Create a `docker-compose.prod.yml` override:

```yaml
version: "3.8"
services:
  backend:
    environment:
      - DEBUG=false
      - ENVIRONMENT=production
    env_file:
      - .env
    restart: always
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: "4G"

  celery_worker:
    environment:
      - DEBUG=false
    env_file:
      - .env
    restart: always
    deploy:
      replicas: 2   # scale workers
      resources:
        limits:
          cpus: "2"
          memory: "4G"

  postgres:
    restart: always
    volumes:
      - pgdata:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: "4G"

  redis:
    restart: always
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: "2G"
```

Run with:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 4. HTTPS / SSL

### Option A: Reverse Proxy (Recommended)

Use **Nginx** or **Caddy** as a reverse proxy in front of the backend:

```nginx
# nginx.conf example
server {
    listen 443 ssl;
    server_name cpis.yourcompany.com;

    ssl_certificate /etc/ssl/certs/cpis.crt;
    ssl_certificate_key /etc/ssl/private/cpis.key;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option B: Caddy (Auto HTTPS)

```caddyfile
cpis.yourcompany.com {
    reverse_proxy backend:8000
}
```

---

## 5. Security Considerations

- **Never commit `.env`** to version control (the `.gitignore` already excludes it).
- **Rotate secrets** (`SECRET_KEY`, `DB_PASSWORD`, `LLM_API_KEY`) regularly.
- **Network isolation:** Run backend, Celery, and database on an internal Docker network; only expose the reverse proxy.
- **File upload limits:** Configure in the reverse proxy if collection artifacts are uploaded.
- **Logging:** Ensure sensitive data (API keys, passwords) is redacted from logs.

---

## 6. Backup and Restore

### Database Backup

```bash
# Manual backup
docker compose exec -T postgres pg_dump -U cpis cpis > backup_$(date +%Y%m%d).sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U cpis -d cpis
```

### Automated Backup (cron)

```bash
# Add to crontab (daily at 2 AM)
0 2 * * * cd /path/to/cpis && docker compose exec -T postgres pg_dump -U cpis cpis | gzip > /backups/cpis_$(date +\%Y\%m\%d).sql.gz
```

### Redis Backup

- Configure Redis **RDB snapshots** or **AOF persistence** in production.
- RDB default: `save 900 1 save 300 10 save 60 10000`
- Back up the `dump.rdb` file with your regular file backup.

### Full System Backup

```bash
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Database
docker compose exec -T postgres pg_dump -U cpis cpis > "$BACKUP_DIR/db.sql"

# Environment (redact secrets)
cp .env "$BACKUP_DIR/.env.backup"

# Compress
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
```

---

## 7. Monitoring

### Health Endpoint

```
GET /health/live    → {"status":"ok"}              (basic liveness)
GET /health/ready   → {"status":"ok","db":"ok",...} (readiness with dependency checks)
```

### Docker Health Checks

Docker Compose already includes health check definitions for all services. View status:

```bash
docker compose ps
```

### Prometheus + Grafana (Optional)

Expose Celery metrics via `flower`:

```bash
docker compose exec celery_worker celery -A app.tasks flower --port=5555
```

Add the Celery exporter to your Prometheus scrape config.

### Logging

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f celery_worker
```

Configure log rotation in Docker Compose:

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 8. Health Checks

The system exposes two health check endpoints:

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health/live` | Kubernetes/Docker liveness probe | `{"status":"ok"}` |
| `GET /health/ready` | Readiness probe (checks DB) | `{"status":"ok","db":"ok"}` |

Configure Docker health checks in `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
  interval: 30s
  timeout: 10s
  retries: 3
```
