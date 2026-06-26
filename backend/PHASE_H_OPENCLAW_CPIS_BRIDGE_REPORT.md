# PHASE H — OpenClaw → CPIS Bridge Report

> **Generated**: 2026-06-26
> **Run ID**: run_20260626_h03_bridge

---

## 1. Bridge Architecture

```
OpenClaw Collector Agent (cpis-info-collector)
  ↓ evidence_batch JSON (schema v1.0)
  ↓ CPIS_JSON_GATE validates route + envelope
POST /api/v1/openclaw/evidence
  ↓
OpenClawBridgeService.ingest_evidence()
  ↓ for each item:
  1. Create CollectionTask (status=COMPLETED)
  2. Create TaskEvent (stage=openclaw_ingest)
  3. Find or create Product (by unique_key)
  4. Create ProductVersion (with structured_data)
  5. Auto-approve if confidence >= 0.7
  ↓
Response: OpenClawEvidenceResponse { run_id, status, ingested, items, errors }
```

## 2. Files Created

| File | Purpose |
|------|---------|
| `backend/app/schemas/openclaw.py` | EvidenceBatch, EvidenceItem, request/response schemas |
| `backend/app/services/openclaw_bridge_service.py` | Bridge service — ingest logic |
| `backend/app/api/openclaw.py` | `POST /api/v1/openclaw/evidence` endpoint |
| `backend/tests/test_openclaw_bridge.py` | 4 tests (success, empty, invalid, partial) |

## 3. API Details

**Endpoint**: `POST /api/v1/openclaw/evidence`

**Request**: Evidence batch in `agent_handoff` envelope

**Response**:
```json
{
  "run_id": "string",
  "status": "success|partial|failed",
  "ingested": 1,
  "items": [
    {
      "item_id": "string",
      "task_id": "uuid",
      "status": "success|failed",
      "error": null
    }
  ],
  "errors": []
}
```

## 4. Test Results

| Test | Status |
|------|--------|
| Success: valid payload with 1 item | ✅ PASS |
| Empty items list | ✅ PASS |
| Invalid JSON returns 422 | ✅ PASS |
| Partial failure with bad item | ✅ PASS |

**Full test suite**: 248 passed (244 baseline + 4 bridge)

## 5. Real API Verification

| Test | Result |
|------|--------|
| POST with empty items | ✅ `ingested: 0, status: success` |
| POST with 1 item (TestProd) | ✅ `ingested: 1, status: success` |
| Product created in DB | ✅ `products total: 11, name: TestProd` |
| Dry-run with full schema | ✅ `ingested: 1, status: success` |

## 6. Security Boundary

| Constraint | Enforced |
|------------|----------|
| OpenClaw cannot write to CPIS DB directly | ✅ — via bridge API only |
| OpenClaw cannot write to Feishu | ✅ — no Feishu dependency in bridge |
| Bridge does not read Feishu env | ✅ — no Feishu imports |
| Bridge does not use Celery | ✅ — synchronous, no task queue |
| Bridge does not expose .env/secrets | ✅ — only accepts evidence JSON |
