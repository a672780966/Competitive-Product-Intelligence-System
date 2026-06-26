# CPIS Phase II — Small-Sample Collection Verification Plan
## Target Brand: 马登工装 / Maden

**Date:** 2026-06-26  
**Status:** Plan Document  
**Scope:** End-to-end pipeline verification using ≤3 safe public web pages  

---

## 1. Overview

This plan details the step-by-step verification of the **complete CPIS business pipeline** for brand "马登工装 / Maden", covering:

Source Discovery → Candidates → Select → Template → RunPlan → Collector → SourceSnapshot → ProductVersion → TaskEvent → Review → Feishu Sync → Usage

### Key Constraints
- No login-required pages (no weibo.com, zhihu.com, douyin.com, xiaohongshu.com, bilibili.com)
- No large-scale or scheduled collection
- Use CPIS built-in collector only (DirectHttpExecutor)
- ≤3 safe, public web pages
- No push/tag/merge/deploy

---

## 2. Prerequisites and Environment Checks

### 2.1 Verify System Components

| Component | Check Method | Expected |
|-----------|-------------|----------|
| Backend API | GET /api/v1/usage/summary | HTTP 200 with JSON |
| Celery Worker | celery status or docker ps | Worker alive |
| PostgreSQL | docker compose ps | Up |
| Redis | docker compose ps | Up |
| Frontend | localhost:5173 | HTML served |

### 2.2 Baseline State
- GET /api/v1/usage/summary — all-zero expected
- GET /api/v1/discovery/sessions — should be empty

---

## 3. Step-by-Step Execution

### Step 1 — Create Discovery Session

**API:** POST /api/v1/discovery/sessions

Request:
```json
{
  "query": "马登工装 Maden 工装外套 产品信息",
  "target_brand": "马登工装 / Maden",
  "topic": "apparel"
}
```

Expected: 201 Created, status "completed", candidate_count > 0

Internal: DiscoveryService creates session → MockSearchProvider returns 8 fixtures → MockModelProvider classifies → risk assessment → 8 SourceCandidate records persisted.

Note: MockSearchProvider returns Xiaomi 14 Ultra fixtures regardless of query. This is acceptable for pipeline verification — we test the system flow, not search accuracy.

---

### Step 2 — Select 3 Safe Candidates

API: GET /api/v1/discovery/sessions/{id}/candidates

Safe URLs from mock fixtures (low/medium risk, direct_http):
1. https://www.mi.com/xiaomi-14-ultra (OFFICIAL_HOMEPAGE, LOW)
2. https://www.mi.com/xiaomi-14-ultra/specs (PRODUCT_DETAIL, LOW)
3. https://www.ithome.com/review/xiaomi-14-ultra (REVIEW, MEDIUM)

Blocked/excluded: zhihu.com (BLOCKED), tieba.baidu.com (BLOCKED), xiaohongshu.com (BLOCKED)

Batch select: POST /api/v1/discovery/sessions/{id}/select with candidate_ids and selected: true

Verification: GET /api/v1/discovery/sessions/{id} — all selected candidates have selected: true

---

### Step 3 — Create Collection Template

API: POST /api/v1/discovery/sessions/{id}/create-template

Request:
```json
{
  "name": "马登工装 Phase II Verification",
  "description": "Small-sample collection verification for 马登工装 / Maden",
  "feishu_sync_enabled": false
}
```

Expected: 201 Created, template_id, candidate_count: 3

Verification: GET /api/v1/collection-templates/{id} — verify source_plan (3 sources), run_plan (3 URLs), status (active)

---

### Step 4 — Execute Template

API: POST /api/v1/collection-templates/{template_id}/run

Expected: 201 Created, tasks_created: 3

Internal pipeline:
1. TemplateService validates RunPlan
2. RunPlanExecutor resolves 3 URLs
3. TaskService.create_task() for each URL:
   - Creates CollectionTask (PENDING)
   - Runs URL validation (passes for public HTTPS)
   - Enqueues collect_url.delay(task_id, url) to Celery
4. Celery collect_url: fetches page → stores SourceSnapshot → chains to clean_content
5. Celery clean_content: cleans HTML → chains to extract_structured_data
6. Celery extract_structured_data: AI extraction → ProductVersioningService → Product + ProductVersion + ProductEvidence

Key risk: Tasks stall if Celery worker is not running.

---

### Step 5 — Verify Pipeline Results

#### 5.1 Task Status
API: GET /api/v1/collection-tasks/{task_id}
- status should be "completed"
- events show: creation → validation → enqueue → collection → cleaning → extraction
- snapshot has final_url, html_hash, cleaned_text

#### 5.2 Source Snapshot
API: GET /api/v1/collection-tasks/{task_id}/snapshots

#### 5.3 Products
API: GET /api/v1/products
- At least 1 product with unique_key, brand, name, review_status

API: GET /api/v1/products/{id}
- Check versions array

#### 5.4 Product Versions
API: GET /api/v1/products/{id}/versions

#### 5.5 Task Events
API: GET /api/v1/collection-tasks/{task_id}/events
- Chronological log with stage, status, message, duration_ms

---

### Step 6 — Human Review

API: GET /api/v1/reviews — list products needing review
API: POST /api/v1/reviews/{version_id}/approve — approve with comments
API: POST /api/v1/reviews/{version_id}/reject — reject with comments

Expected: decision "approved" or "rejected", product review_status updated

---

### Step 7 — Feishu Sync (if enabled)

Precondition: Feishu credentials in .env (FEISHU_APP_ID, etc.), AUTO_SYNC_FEISHU=false

API: POST /api/v1/sync-records/sync-product/{product_id}
API: POST /api/v1/sync-records/sync-all
API: GET /api/v1/sync-records

Each sync record: product_id, sync_status, feishu_record_id, synced_at, error_message

---

### Step 8 — Usage Summary

API: GET /api/v1/usage/summary
API: GET /api/v1/usage/daily

Post-pipeline expected: total_task_count >= 3, total_days >= 1

---

### Step 9 — Evidence Bundle

17 evidence items to collect:
1. Baseline usage (before)
2. Discovery session created
3. Candidates listed
4. Candidates selected
5. Template created
6. Template verified
7. Template executed
8. Task details (x3)
9. Task events (x3)
10. Source snapshots (x3)
11. Products listed
12. Product detail
13. Product versions
14. Reviews listed
15. Review approve/reject
16. Feishu sync records
17. Final usage (after)

---

## 4. Failure Scenarios

### A: Celery Worker Not Running
Symptom: Tasks stuck in PENDING
Recovery: cd backend && celery -A app.tasks.worker worker --loglevel=info

### B: URL Validation Blocks
Symptom: Task status = blocked
Check: URL must be public HTTPS
Recovery: Choose alternative URL

### C: Feishu Sync Fails
Symptom: sync_status = failed
Acceptable — error path is validated

### D: Low Extraction Confidence
Symptom: review_status = needs_review
Proceed with manual review (Step 6)

---

## 5. Success Criteria

- [ ] Step 1: Session completed, candidate_count > 0
- [ ] Step 2: 2-3 candidates selected, LOW/MEDIUM risk, direct_http
- [ ] Step 3: Template with 3 sources in source_plan
- [ ] Step 4: 3 tasks created
- [ ] Step 5: Each task completes with Snapshot, Events, ProductVersion
- [ ] Step 5b: At least one product created
- [ ] Step 6 (opt): Review lifecycle works
- [ ] Step 7 (opt): Feishu sync record created
- [ ] Step 8: Usage reflects pipeline activity

---

## Appendix A — Key API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/v1/discovery/sessions | Create session |
| GET | /api/v1/discovery/sessions/{id}/candidates | List candidates |
| PATCH | /api/v1/discovery/candidates/{id} | Select/deselect |
| POST | /api/v1/discovery/sessions/{id}/select | Batch select |
| POST | /api/v1/discovery/sessions/{id}/create-template | Create template |
| GET | /api/v1/collection-templates | List templates |
| GET | /api/v1/collection-templates/{id} | Get template |
| POST | /api/v1/collection-templates/{id}/run | Run template |
| GET | /api/v1/collection-tasks/{id} | Task detail |
| GET | /api/v1/collection-tasks/{id}/events | Task events |
| GET | /api/v1/collection-tasks/{id}/snapshots | Source snapshot |
| GET | /api/v1/products | List products |
| GET | /api/v1/products/{id} | Product detail |
| GET | /api/v1/products/{id}/versions | Product versions |
| GET | /api/v1/reviews | List reviews |
| POST | /api/v1/reviews/{id}/approve | Approve review |
| POST | /api/v1/reviews/{id}/reject | Reject review |
| POST | /api/v1/sync-records/sync-product/{id} | Sync to Feishu |
| GET | /api/v1/sync-records | List sync records |
| GET | /api/v1/usage/summary | Usage summary |
| GET | /api/v1/usage/daily | Daily usage |

## Appendix B — Architectural Notes

1. Mock providers return Xiaomi 14 Ultra fixtures regardless of query. Acceptable for system flow testing.
2. Celery dependency: collection pipeline requires running worker.
3. Feishu credentials in .env; manual sync needed (AUTO_SYNC_FEISHU=false).
4. URL validation blocks localhost/private IPs; public HTTPS passes.
5. Non-product pages may yield low-confidence extractions (NEEDS_REVIEW). Normal behavior.
