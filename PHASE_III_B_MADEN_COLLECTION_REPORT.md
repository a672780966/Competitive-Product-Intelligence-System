# Phase III-B — 马登工装/Maden 采集执行报告

## 1. 采集流程

### 1.1 前置条件检查清单

| # | 检查项 | 验证命令 | 预期结果 |
|---|--------|---------|---------|
| 1 | PostgreSQL 运行中 | `docker ps \| grep postgres` 或 `pg_isready` | 服务运行 |
| 2 | Migration 已应用 | `cd backend && alembic current` | `005_add_exec_reports` |
| 3 | API 服务运行 | `curl -s http://localhost:8000/docs \| head -5` | 200 OK |
| 4 | Celery worker 运行 | `ps aux \| grep celery` | worker 进程存在 |
| 5 | Redis 运行 | `redis-cli ping` | PONG |
| 6 | DuckDuckGo 可达 | `curl -s https://html.duckduckgo.com/ \| head -3` | 返回 HTML |
| 7 | 今日拦截计数 | `curl -s http://localhost:8000/api/v1/blocked-sources/stats` | 数字 ≥ 0 |

### 1.2 修复 CollectorExecutionReport（步骤一）

执行 `PHASE_III_B_EXECUTION_REPORT_FIX.md` 中的修复步骤：
1. 确认 migration 已应用
2. 验证 `get_celery_session` 提交行为
3. 如有必要，补全 validation 失败路径的报告写入
4. 用 books.toscrape.com 验证修复

### 1.3 发现阶段（步骤二）

运行 `scripts/discover_maden_urls.py`：

```bash
cd /home/ctyun/Competitive-Product-Intelligence-System
mkdir -p scripts
# 将发现脚本保存到 scripts/discover_maden_urls.py
cd backend
python -c "
import asyncio
import sys
sys.path.insert(0, '.')
from scripts.discover_maden_urls import discover
asyncio.run(discover())
"
```

输出：`maden_discovery_results.json`

### 1.4 采集执行（步骤三）

#### 方案 A：有安全 URL（首选）

对于每个 risk_level="low" 的 URL，通过 API 创建采集任务：

```bash
# 批量创建采集任务
cat maden_discovery_results.json | python -c "
import json, sys, httpx, asyncio

data = json.load(sys.stdin)
safe_urls = [r for r in data['results'] if r['risk_level'] == 'low']

async def create_tasks():
    async with httpx.AsyncClient(base_url='http://localhost:8000', timeout=30) as c:
        tasks = []
        for r in safe_urls:
            resp = await c.post('/api/v1/collection-tasks', json={
                'source_url': r['url'],
                'category_hint': 'product',
                'language_hint': 'zh-CN',
                'priority': 1,
            })
            task = resp.json()
            tasks.append(task)
            print(f\"创建任务: {task['id']} <- {r['url']}\")
        print(f\"\\n共创建 {len(tasks)} 个采集任务\")
        return tasks

asyncio.run(create_tasks())
"
```

#### 方案 B：无安全 URL（回退）

如果所有 URL 均为 blocked，则输出 `PHASE_III_B_MADEN_COLLECTION_REPORT.md` 报告以下内容：

**结论：BLOCKED_NO_SAFE_MADEN_URL_FOUND**

详细说明：
- 搜索查询 4 组，共返回 N 个结果
- 其中 M 个来自被封禁源（小红书/抖音/B站/知乎/微博/贴吧）
- K 个来自淘宝/天猫（高风险，需登录）
- 其余为无关结果
- **无安全可采的公开 URL**

### 1.5 验证阶段（步骤四）

无论采集是否成功，都执行以下验证：

#### 验证 A：CollectorExecutionReport 写入验证

```python
"""验证每个任务的 execution report"""
import httpx, asyncio

async def verify_reports(task_ids):
    async with httpx.AsyncClient(base_url='http://localhost:8000', timeout=30) as c:
        for tid in task_ids:
            resp = await c.get(f'/api/v1/collection-tasks/{tid}/execution-reports')
            reports = resp.json()
            task_resp = await c.get(f'/api/v1/collection-tasks/{tid}')
            task = task_resp.json()
            print(f"任务 {tid[:8]}... 状态={task['status']} reports={len(reports)}")
            for r in reports:
                print(f"  report: runtime={r['collector_runtime']} status={r['status']} "
                      f"duration={r.get('duration_ms')}ms size={r.get('content_size')}B")
                if r.get('error_message'):
                    print(f"  error: {r['error_message']}")

task_ids = [...]  # 从创建结果中获取
asyncio.run(verify_reports(task_ids))
```

#### 验证 B：拦截统计验证

```bash
# 验证拦截器计数增加
curl -s http://localhost:8000/api/v1/blocked-sources/stats
```

#### 验证 C：Pipeline 完整性验证

```bash
# 对成功采集的任务验证 clean + extract
curl -s http://localhost:8000/api/v1/collection-tasks/{task_id} | \
  python -c "import json,sys; d=json.load(sys.stdin); print('stages:', [s['stage']+':'+s['status'] for s in d.get('pipeline_status',{}).get('stages',[])])"
```

## 2. 执行决策树

```
执行开始
  │
  ├─ Migration 已应用？
  │   ├─ No  → alembic upgrade head → 重试
  │   └─ Yes → 继续
  │
  ├─ DB 中已有 report 记录？
  │   ├─ Yes → CollectorExecutionReport ✅ 已修复
  │   └─ No  → 检查 get_celery_session 提交 → 修复
  │
  ├─ 搜索发现安全 URL？
  │   ├─ Yes → 创建采集任务 → 等待完成 → 验证报告
  │   └─ No  → 报告 BLOCKED_NO_SAFE_MADEN_URL_FOUND
  │
  └─ 生成全部 4 份输出文件
```

## 3. 预期结果记录模板

```json
{
  "phase": "III-B",
  "brand": "马登工装 / Maden",
  "execution_time": "2026-06-26T...",
  "report_fix_status": "success|partial|failed",
  "report_fix_details": "...",
  "discovery": {
    "queries": 4,
    "total_results": 0,
    "safe_results": 0,
    "blocked_results": 0,
    "high_risk_results": 0
  },
  "collection": {
    "tasks_created": 0,
    "tasks_completed": 0,
    "tasks_blocked": 0,
    "tasks_failed": 0
  },
  "overall_status": "BLOCKED_NO_SAFE_MADEN_URL_FOUND|COMPLETED_WITH_DATA",
  "blocked_source_count_today": 23
}
```
