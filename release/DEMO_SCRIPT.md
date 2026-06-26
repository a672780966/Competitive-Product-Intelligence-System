# CPIS V1 — Demo Script

A walkthrough for presenters to demonstrate CPIS V1's key features.

**Estimated time:** 5–10 minutes  
**Prerequisites:** System running, demo data seeded (see [QUICK_START.md](./QUICK_START.md))

---

## Step 1: Start the System

```bash
docker compose up -d
```

**Verify:**
- `docker compose ps` — all services show "Up" status.
- `curl http://localhost:8000/health/live` — returns `{"status":"ok"}`.

**What to say:**
> "CPIS V1 runs on Docker Compose with four main services: PostgreSQL for data storage, Redis for caching and task queues, a FastAPI backend that powers the API, and a React frontend for the user interface. Celery workers handle async collection tasks in the background."

**Expected screen:** Terminal showing healthy services.

---

## Step 2: Seed Demo Data

```bash
docker compose exec backend python scripts/seed_demo.py
```

**Verify:**
- Script completes without errors.
- Output shows sample products, templates, and usage records created.

**What to say:**
> "The seed script populates the database with sample competitive products, collection templates, and some usage history so we can explore the system immediately. In a real deployment, this data would come from your configured collection workflows."

**Expected screen:** Terminal showing seed execution log with created records.

---

## Step 3: Browse Products

Open [http://localhost:5173](http://localhost:5173) in a browser.

**Navigate to:** The Products page (typically the main dashboard view).

**What to show:**
- List of competitive products with names, descriptions, and status badges.
- Product version history showing extracted data snapshots.
- AI-generated changelogs between versions.

**What to say:**
> "The product catalog shows all competitive products being tracked. Each product has a timeline of collected versions — the system automatically fetches product pages, extracts structured data using AI, and tracks changes over time. You can see the AI-generated changelog showing what changed between versions."

**Expected screen:** The products page showing demo products with version history.

---

## Step 4: Run a Collection Template

Navigate to **Templates** (or **Collections**) section.

**What to show:**
1. Click on an existing collection template (e.g., "Demo Product Page").
2. Select **Run Now** or **Execute**.
3. Monitor the collection task status.

**While running, say:**
> "Collection templates define what to collect, from where, and how to process it. When we run a template, the backend dispatches a Celery task that fetches the page, cleans the HTML, runs AI extraction, and stores the result as a new product version. Let's watch the task complete..."

**After completion:**
4. Navigate back to the Products page.
5. Show the new version appeared in the product timeline.
6. Click to view the extracted data.

**What to say:**
> "The new version is now available with AI-extracted structured data. The system compares it with previous versions to highlight what's new, changed, or removed."

**Expected screen:** Collection task shows "completed" status; new version visible in product timeline with extracted data.

---

## Step 5: Check the Usage Dashboard

Navigate to **Usage** or **Dashboard** section.

**What to show:**
- Collection counts (total collections, success rate).
- Task execution metrics (average duration, retry counts).
- Search history showing recent discovery queries.
- Collector runtime distribution (which collectors were used most).

**What to say:**
> "The usage dashboard gives operators visibility into how the system is performing — how many collections have been run, success rates, average task durations, and which collector runtimes are being used. This helps identify bottlenecks and optimize collection configurations. The search history shows past discovery queries, making it easy to revisit previous research."

**Expected screen:** Dashboard with metrics charts and search history table.

---

## Optional: Show Feishu Sync

If Feishu credentials are configured:

1. Navigate to **Settings** or **Integrations**.
2. Show the sync status.
3. Open the Feishu Bitable to display synced records.

**What to say:**
> "When Feishu integration is configured, collected product data is automatically synced to a Feishu Bitable, making it accessible to the broader team without needing to log into the CPIS system."

---

## Optional: Show MCP (Model Context Protocol)

If MCP tools are available:

1. Trigger an AI-assisted discovery or template creation via the MCP interface.
2. Show how natural language commands can manage the system.

---

## Recovery: What If Something Fails

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Frontend blank/not loading | Frontend container not ready | `docker compose logs frontend` |
| API returns 500 | Database not migrated | `docker compose exec backend alembic upgrade head` |
| "Connection refused" | Service not fully started | Wait 10s, retry. Check `docker compose ps` |
| Collection task stuck | Celery worker not running | `docker compose up -d celery_worker` |
| Seed script fails | DB not ready | Ensure postgres is healthy: `docker compose ps postgres` |

---

## Demo Checklist

- [ ] Docker running (Step 1)
- [ ] All containers healthy (Step 1)
- [ ] Demo data seeded (Step 2)
- [ ] Frontend accessible at localhost:5173 (Step 3)
- [ ] At least one collection template visible (Step 4)
- [ ] Usage dashboard shows data (Step 5)
- [ ] (Optional) Feishu sync configured
- [ ] (Optional) MCP tools available
