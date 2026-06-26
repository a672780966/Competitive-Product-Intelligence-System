# Phase VI — Demo Verification Report

## Demo Complete Flow

The CPIS V1 demo covers the following pipeline:

```
Discovery → Candidate → Template → RunPlan → Collector → Review → Feishu → Usage
```

### Step 1: Start System
```bash
cp .env.example .env
./scripts/start_demo.sh
```
→ All 5 services start (postgres, redis, backend, celery-worker, frontend)
→ Backend health check passes at http://localhost:8000/health/live
→ Frontend available at http://localhost:8080

### Step 2: Seed Demo Data
```bash
docker compose -f docker-compose.demo.yml exec -T backend python /app/scripts/seed_demo.py
```
→ Seeds 3 products (TechPro X100, NovaBook Pro 14, SoundWave Buds Pro)
→ Seeds 1 discovery session
→ Seeds 1 collection template
→ Idempotent — safe to run multiple times

### Step 3: Navigate
- **Products page**: http://localhost:8080/products — 3 demo products visible
- **Tasks page**: http://localhost:8080/tasks — collection tasks listed
- **Usage page**: http://localhost:8080/usage — daily stats chart
- **Templates page**: http://localhost:8080/collection-templates — demo template visible

### Step 4: Run Collection
1. Navigate to Templates → select demo template
2. Click "Run" → creates collection tasks
3. Celery worker processes tasks → SourceSnapshot created
4. Products/versions updated
5. Review page shows results

### Step 5: Verify Completion
- Task status shows "completed"
- Usage stats updated with collected_page_count
- Products have versions with extraction data

## API Verification

| Endpoint | Method | Expected |
|----------|--------|----------|
| `/health/live` | GET | 200 OK |
| `/api/v1/products` | GET | Product list |
| `/api/v1/collection-templates` | GET | Template list |
| `/api/v1/usage/summary` | GET | Usage stats |
| `/docs` | GET | Swagger UI |

## Demo Script
Full walkthrough available at `release/DEMO_SCRIPT.md`
