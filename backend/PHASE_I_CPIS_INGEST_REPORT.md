# PHASE I — CPIS Ingest 报告

> **Generated**: 2026-06-26
> **Run ID**: run_20260626_phase_i_ingest

---

## 1. 入库链路

```
evidence_json
  → bridge service
  → CollectionTask (COMPLETED, priority=50, created_by=openclaw-bridge)
  → TaskEvent (stage=openclaw_ingest, status=COMPLETED)
  → Product (brand, name, unique_key, review_status)
  → ProductVersion (structured_data, overall_confidence)
  → Review (approve / auto_approved)
  → Feishu Sync (POST /api/v1/sync-records/sync-product/{id})
```

## 2. CollectionTask 详情

| URL | Task ID | Status | Events |
|-----|---------|--------|--------|
| apple.com | ca98390c | completed | 1 |
| airpods-pro/ | 7d1be381 | completed | 1 |
| MDN HTML | 97b7cfba | completed | 1 |

## 3. Product 详情

| 产品名 | Product ID | Brand | Review Status | Versions |
|--------|-----------|-------|---------------|----------|
| Apple iPhone 16 Pro | 4458a98e | Apple | approved | 1 |
| AirPods Pro 2nd Gen | 04e2e266 | Apple | auto_approved | 1 |
| MDN Web Docs HTML | 8dda8d05 | Mozilla | approved | 1 |

## 4. ProductVersion 详情

| 产品 | Version ID | Confidence | Structured Data |
|------|-----------|------------|-----------------|
| iPhone 16 Pro | 2d118618 | 0.4 | pricing={$999}, ratings={4.8/5000} |
| AirPods Pro 2nd Gen | e20464ad | 0.7 | pricing={$249}, ratings={4.7/85000}, distribution |
| MDN HTML | 85752e76 | 0.4 | pricing={$0}, ratings={4.9/15000} |

## 5. Review 详情

| 产品 | Review 方式 | Reviewer | Result |
|------|------------|----------|--------|
| iPhone 16 Pro | 手动批准 | phase-i-test | approved |
| AirPods Pro 2nd Gen | 自动 (conf≥0.7) | system | auto_approved |
| MDN HTML | 手动批准 | phase-i-test | approved |

## 6. TaskEvent 详情

| Task ID | Stage | Status | Message |
|---------|-------|--------|---------|
| ca98390c | openclaw_ingest | completed | Ingested from OpenClaw evidence batch phase-i-url-001 |
| 7d1be381 | openclaw_ingest | completed | Ingested from OpenClaw evidence batch phase-i-url-002 |
| 97b7cfba | openclaw_ingest | completed | Ingested from OpenClaw evidence batch phase-i-url-003 |
