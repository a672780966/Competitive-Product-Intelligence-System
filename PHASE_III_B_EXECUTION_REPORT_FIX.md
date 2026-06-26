# Phase III-B — CollectorExecutionReport 修复方案

## 1. 问题诊断

### 1.1 症状
执行 `GET /api/v1/collection-tasks/{task_id}/execution-reports` 返回空列表（DB 中 `collector_execution_reports` 表记录为 0）。

### 1.2 根因分析

经过逐层检查，**`tasks/collection.py` 中 `_do_collect()` 已经正确地创建了 `CollectorExecutionReport`**：
- 阻塞路径（line 130-143）：✅ 已写入
- 启动路径（line 150-157）：✅ 已写入
- 失败路径（line 169-180, 224-232）：✅ 已写入
- 成功路径（line 192-198）：✅ 已写入

上述所有路径均通过 `session.add(report)` + `await session.flush()` 持久化。

**真实原因排查清单：**

| # | 可能性 | 优先级 | 验证方法 |
|---|--------|--------|----------|
| 1 | **Migration 未运行** — `collector_execution_reports` 表不存在 | ⭐ 最高 | 连接 DB 检查表是否存在 |
| 2 | **Celery session 上下文未 commit** — `get_celery_session()` 的 `__aexit__` 未正确提交 | ⭐ 高 | 检查 `get_celery_session` 实现 |
| 3 | **Phase III 使用 mock 路径** — 未经过真实 `_do_collect` | 中 | 复查 Phase III 测试代码 |
| 4 | **risk_level 拦截在 validation 阶段** — 任务从未进入 `_do_collect` | 中 | 检查任务最终状态 |
| 5 | **Session 级异常回滚** — 写入后其他操作抛异常导致回滚 | 低 | 检查日志中的错误/回滚 |

### 1.3 最可能的根因组合

**假设 1（最可能）**：Migration `005_add_collector_execution_reports` 未对实际数据库执行。Phase V 通过 pytest 测试验证（测试使用内存 SQLite 或事务回滚），但生产/开发数据库未运行 `alembic upgrade head`。

**假设 2**：即使表存在，`get_celery_session` 上下文管理器若在 `_do_collect` return 后未 commit（因 Celery 任务在 async 上下文关闭前已完成），报告不会被持久化。

## 2. 修复步骤

### Step 1: 验证 Migration 状态

```bash
cd /home/ctyun/Competitive-Product-Intelligence-System/backend

# 检查当前 migration 版本
alembic current

# 如果有未应用的 migration，执行
alembic upgrade head

# 验证表存在
psql -U cpis -d cpis -c "\d collector_execution_reports"
```

如果无 PostgreSQL 运行环境，则启动 Docker Compose：

```bash
cd /home/ctyun/Competitive-Product-Intelligence-System
docker compose up -d db
sleep 5
cd backend && alembic upgrade head
```

### Step 2: 验证 `get_celery_session` 提交行为

检查 `app/core/database.py` 中的 `get_celery_session` 实现：

```python
# 预期行为：__aexit__ 中应自动 commit（成功时）或 rollback（异常时）
# 如果缺少自动 commit，需要补全
```

修复方案（如需要）：

```python
@contextlib.asynccontextmanager
async def get_celery_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # <-- 确保提交
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Step 3: 补全 `tasks/collection.py` 中的缺失路径

虽然 `_do_collect` 已覆盖所有路径，但以下两个路径**未创建报告**：

**路径 A：`collect_url` 顶层异常（Celery retry 耗尽后）**

如果 Celery 重试耗尽且 `_do_collect` 的 `raise` 未被捕获（line 237），报告已在 `_do_collect` 的 except 块中创建。✅ 已覆盖。

**路径 B：`_do_clean` 和 `_do_extract` 阶段**

这些阶段不涉及采集器执行，不需要 `CollectorExecutionReport`。✅ 设计正确。

**路径 C：直接通过 API 创建但 validation 失败的任务**

如果 `validate_url` 返回 `BLOCKED` 或 `FAILED`，任务不会进入 `_do_collect`。这种情况下没有 `CollectorExecutionReport` 是合理的——因为采集器从未执行。但为了审计完整性，**建议在 validation 失败时也创建一条报告**：

```python
# 在 task_service.py _run_validation 的 else 分支中（validation 失败时）
from app.models.collector_execution_report import CollectorExecutionReport

report = CollectorExecutionReport(
    task_id=task.id,
    url=task.source_url,
    collector_runtime="blocked",
    status="blocked",
    started_at=datetime.now(timezone.utc),
    finished_at=datetime.now(timezone.utc),
    duration_ms=0,
    content_size=0,
    retry_count=0,
    error_message=result.error_message or "URL validation failed",
)
self._db.add(report)
```

### Step 4: 验证修复

```python
# 创建测试任务 -> 确认 report 写入
POST /api/v1/collection-tasks
{"source_url": "https://books.toscrape.com", "category_hint": "books"}

# 查询 report
GET /api/v1/collection-tasks/{task_id}/execution-reports

# 预期：返回 1 条 report，status 为 "success" 或 "blocked" 或 "failed"
```

## 3. 自动验证脚本

创建验证脚本 `scripts/verify_execution_reports.py`：

```python
"""验证 CollectorExecutionReport 写入是否正常。"""
import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"

async def verify():
    # 1. 创建测试任务
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post("/api/v1/collection-tasks", json={
            "source_url": "https://books.toscrape.com",
            "category_hint": "books",
            "language_hint": "en",
        })
        if resp.status_code != 201:
            print(f"❌ 创建任务失败: {resp.status_code} {resp.text}")
            sys.exit(1)
        task = resp.json()
        task_id = task["id"]
        print(f"✅ 任务创建成功: {task_id}")

        # 2. 等待采集完成
        for i in range(30):
            resp = await client.get(f"/api/v1/collection-tasks/{task_id}")
            status = resp.json()["status"]
            if status in ("completed", "failed", "blocked"):
                print(f"✅ 任务完成: status={status}")
                break
            await asyncio.sleep(1)
        else:
            print("❌ 任务超时")
            sys.exit(1)

        # 3. 查询 execution report
        resp = await client.get(f"/api/v1/collection-tasks/{task_id}/execution-reports")
        reports = resp.json()
        if len(reports) > 0:
            report = reports[0]
            print(f"✅ ExecutionReport 写入成功:")
            print(f"   status={report['status']}")
            print(f"   collector_runtime={report['collector_runtime']}")
            print(f"   duration_ms={report.get('duration_ms')}")
            print(f"   content_size={report.get('content_size')}")
        else:
            print("❌ ExecutionReport 为空 — 修复未生效")
            sys.exit(1)

asyncio.run(verify())
```

## 4. 修复验收标准

| 检查项 | 预期结果 | 验证方式 |
|--------|---------|----------|
| `collector_execution_reports` 表存在 | 表存在并有正确的 schema | `\d collector_execution_reports` |
| 成功路径写入 report | status=success | 查 books.toscrape.com 任务 |
| 阻塞路径写入 report | status=blocked | 查被 blocked 的源 |
| 失败路径写入 report | status=failed | 查不可达 URL 的任务 |
| API 可查 | 返回完整 report 列表 | `GET /{task_id}/execution-reports` |
| Validation 失败也写入 | status=blocked | 创建明显无效 URL 的任务 |
