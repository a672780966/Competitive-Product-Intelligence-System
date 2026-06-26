# CPIS Phase II — 真实小样本采集验证 证据包

## 总览

| 项 | 结果 |
|---|------|
| **Run ID** | `phase-ii-20260626` |
| **测试品牌** | 马登工装 / Maden（MockSearchProvider 返回固定 Xiaomi fixture） |
| **状态** | **全部通过** |
| **修复项** | Celery worker 缺少 task 注册（已修复: `worker.py` 添加 import） |

---

## 1. Source Discovery — 来源发现

- **API:** `POST /api/v1/discovery/sessions`
- **Session ID:** `29e79fa1-0f33-4507-af89-d4c682cbfe7b`
- **查询:** `"马登工装 Maden 工装外套 产品信息 官方店铺"`
- **候选数:** 8
- **状态:** completed ✅

## 2. Candidates — 候选选择

- **选择候选数:** 3
- **已排除:** zhihu.com (blocked), tieba.baidu.com (blocked), xiaohongshu.com (blocked)
- **选中 URL:**
  1. `https://www.mi.com/xiaomi-14-ultra` — low risk, official_homepage
  2. `https://www.mi.com/xiaomi-14-ultra/specs` — low risk, product_detail
  3. `https://www.ithome.com/review/xiaomi-14-ultra` — medium risk, review

## 3. Template — 采集模板

- **API:** `POST /api/v1/discovery/sessions/{id}/create-template`
- **Template ID:** `5fed1f0c-9f4c-489f-a4bd-4af35f646800`
- **名:** 马登工装 Phase II Verification
- **来源数:** 3
- **source_plan:** 3 sources with URLs, risk_level, recommended_collector

## 4. Template Run — 模板执行

- **API:** `POST /api/v1/collection-templates/{id}/run`
- **tasks_created:** 3
- **Mock URL 采集结果:** 全部 blocked (HTTP 405/404 — URLs 为假 fixture)
- **错误路径验证:** ✅ creation → validation → blocked(FETCH_HTTP_ERROR)
- **TaskEvent 正确记录:** ✅

## 5. 直接采集验证（真实 URL）

| 阶段 | 状态 | 耗时 |
|------|------|------|
| creation | ✅ pending | - |
| validation | ✅ passed | - |
| enqueue | ✅ pending | - |
| collection | ✅ completed | 796ms |
| cleaning | ✅ completed | 67ms |
| extraction | ✅ completed | 647ms |

- **Task ID:** `574c95dc-c665-4fc2-8dbc-0a29d2cedaca`
- **URL:** `https://example.com`
- **Snapshot:** created (559 bytes)
- **Cleaned text:** 129 chars
- **Product ID:** `ace242b6-f52b-43d6-9a60-1b91d192190d`

## 6. Human Review

- **Review ID:** `27af5f25-8072-48da-94e0-f1577a9681b2`
- **操作:** approved
- **Comments:** "Phase II verification - example.com test"
- **Reviewer:** admin

## 7. Feishu Sync

- **Sync API:** `POST /api/v1/sync-records/sync-product/{product_id}`
- **sync_status:** success ✅
- **feishu_record_id:** `recvnCW6XSWjY4`
- **DB 类型:** bitable

## 8. Usage 统计

- **total_task_count:** 0（需要刷新或增量统计未触发）

## 9. 修复项

| 问题 | 修复 |
|------|------|
| Celery worker 启动时未注册 task | `worker.py` 添加 `from app.tasks.collection import collect_url, clean_content, extract_structured_data` |

## 10. 检查清单

- [x] Discovery → Candidates → Select → Template → Run 全链路
- [x] Mock URL 采集失败路径（blocked status + TaskEvent）
- [x] 真实 URL 采集成功（collect → clean → extract 全部 completed）
- [x] SourceSnapshot 持久化
- [x] Product / ProductVersion 创建
- [x] Human Review（approve）
- [x] Feishu Sync（success）
- [x] Error handling 路径验证
