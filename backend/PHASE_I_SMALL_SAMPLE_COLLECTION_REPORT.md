# PHASE I — 小样本采集报告

> **Generated**: 2026-06-26
> **Run ID**: run_20260626_phase_i

---

## 1. 采集 URL 列表

| # | 类型 | URL | 状态码 | 大小 |
|---|------|-----|--------|------|
| 1 | 官网首页 | https://www.apple.com/ | 200 | 249 KB |
| 2 | 产品详情页 | https://www.apple.com/airpods-pro/ | 200 | 520 KB |
| 3 | 文档/FAQ | https://developer.mozilla.org/en-US/docs/Web/HTML | 200 | 183 KB |

所有 URL 为公开可访问页面，无需登录、无付费墙、无反爬。

## 2. 采集链路

```
OpenClaw cpis-info-collector (simulated)
  ↓ evidence_batch JSON (schema v1.0)
  ↓ cpis-json-gate 验证通过
  ↓ POST /api/v1/openclaw/evidence
  ↓ BridgeService.ingest_evidence()
  ↓ CollectionTask (COMPLETED) + TaskEvent
  ↓ Product + ProductVersion (with structured_data)
  ↓ Review (approve / auto_approved)
  ↓ POST /api/v1/sync-records/sync-product/{id}
  ↓ Feishu Bitable → record created
  ↓ SyncRecord (status=success)
```

## 3. 禁止事项检查

| 禁止项 | 状态 |
|--------|------|
| 大规模采集 | ❌ 仅 3 URL |
| 定时采集 | ❌ 未启用 |
| 小红书/抖音/B站/知乎/微博/贴吧 | ❌ 未涉及 |
| 登录态页面 | ❌ 无 |
| 付费墙 | ❌ 无 |
| 绕过反爬 | ❌ 未尝试 |
| MediaCrawler/openserp/Comperator | ❌ 未使用 |
| Scrapling/crawl4ai 进入 pipeline | ❌ 仅评估未集成 |
| push / tag / merge | ❌ 未执行 |
| 提交 .env / 打印 secret | ❌ 未执行 |
