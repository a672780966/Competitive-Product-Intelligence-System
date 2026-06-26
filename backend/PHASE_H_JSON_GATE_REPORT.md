# PHASE H — cpis-json-gate Validation Report

> **Generated**: 2026-06-26
> **Run ID**: run_20260626_h01_json_gate

---

## 1. Plugin Installation

| Step | Status | Detail |
|------|--------|--------|
| Unit tests (27) | ✅ All pass | `validatePublishResult` (25 subtests) + `validateSessionsSend` (2) |
| Install via `openclaw plugins install` | ✅ | Path: `~/.openclaw/extensions/cpis-json-gate/` |
| Enable plugin | ✅ | `openclaw plugins enable cpis-json-gate` |
| Gateway restart | ✅ | New PID: 1061722 → 1064240 |
| Plugin load status | ✅ **loaded** | Confirmed via `openclaw plugins list` |
| Version | v1.2.0 | Adapted for gateway v2026.3.8 |

## 2. Schema Validation Rules (cpis-json-gate v1.2.0)

### `before_tool_call` — sessions_send validation

| Rule | Tested |
|------|--------|
| Non-applicable agents pass through | ✅ |
| Markdown fences in message are blocked | ✅ |
| Envelope must have correct from_agent/to_agent | ✅ |
| payload_type must match route | ✅ |
| evidence_batch schema_version must be 1.0 | ✅ |
| Items must have unique item_id, ASIN, product_url | ✅ |
| image_url must be http/https or null | ✅ |
| prices, ratings, ranking fields validated | ✅ |

### `before_agent_finalize` — publish_result validation

| Rule | Tested |
|------|--------|
| Accepts valid publish_result JSON | ✅ |
| Rejects empty / Markdown fences | ✅ |
| Rejects invalid JSON / non-objects | ✅ |
| Rejects unknown fields | ✅ |
| Rejects wrong schema_version / object_type | ✅ |
| published must be boolean | ✅ |
| feishu_url required when published=true | ✅ |
| images_expected / images_uploaded constraints | ✅ |
| image_failures must have item_id, image_url, reason | ✅ |

## 3. Evidence JSON Schema (v1.0)

The bridge accepts the `evidence_batch` envelope as defined by collector-rules.md:

```
agent_handoff {
  schema_version: "1.0"
  object_type: "agent_handoff"
  from_agent: "cpis-info-collector"
  to_agent: "cpis-product-analyst"
  payload_type: "evidence_batch"
  payload: EvidenceBatch {
    schema_version: "1.0"
    object_type: "evidence_batch"
    run_id, status, collection_scope
    sources: [{ source_id, source_url/url, source_type }]
    items: [{ item_id, product_name, asin, product_url, ... }]
    collection_summary
  }
}
```

## 4. Verdict

- **Schema**: ⚠️ Bridge accepts schema v1.0 but uses a simplified subset (fewer required fields than cpis-json-gate validator). The bridge intentionally accepts partial data since CPIS doesn't require Amazon BSR fields.
- **Gate**: ✅ Functional — will block malformed OpenClaw agent output.
- **Recommendation**: When OpenClaw fully integrates, cpis-json-gate will enforce Amazon-specific rules (ranking source types, ASIN format, max_items_per_ranking). For now, bridge is lenient.
