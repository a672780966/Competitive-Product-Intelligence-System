# Phase III-B（马登工装补测）+ P0 Reality Alignment — 完整实施计划

**生成日期:** 2026-06-26  
**目标:** 完成真实品牌采集补测 + 修复所有 overclaim，对齐项目真实状态  
**审计人:** Hermes Agent (Codex 计划)

---

## 目录

- [任务 A: Phase III-B — 马登工装真实品牌采集补测](#任务-a-phase-iii-b--马登工装真实品牌采集补测)
  - [A1: CollectorExecutionReport 写入修复](#a1-collectorexecutionreport-写入修复)
  - [A2: DuckDuckGo 真实搜索发现](#a2-duckduckgo-真实搜索发现)
  - [A3: 候选 URL 风险评估](#a3-候选-url-风险评估)
  - [A4: 完整 CPIS Pipeline 采集执行](#a4-完整-cpis-pipeline-采集执行)
  - [A5: 验证与证据输出](#a5-验证与证据输出)
- [任务 B: P0 Reality Alignment — 真实能力对齐修复](#任务-b-p0-reality-alignment--真实能力对齐修复)
  - [B1: README.md 首屏文案修正](#b1-readmemd-首屏文案修正)
  - [B2: 核心功能模块 overclaim 修正](#b2-核心功能模块-overclaim-修正)
  - [B3: 系统架构图 overclaim 修正](#b3-系统架构图-overclaim-修正)
  - [B4: 技术栈标签修正](#b4-技术栈标签修正)
  - [B5: 路线图文案修正](#b5-路线图文案修正)
  - [B6: RELEASE_NOTES.md overclaim 修正](#b6-release_notesmd-overclaim-修正)
  - [B7: CHANGELOG.md overclaim 修正](#b7-changelogmd-overclaim-修正)
  - [B8: 英文/日文/韩文 README 同步修正](#b8-英文日文韩文-readme-同步修正)
  - [B9: Discovery 页面文案修正](#b9-discovery-页面文案修正)
  - [B10: Provider 配置页/状态接口新增](#b10-provider-配置页状态接口新增)
  - [B11: Overclaim 保护测试](#b11-overclaim-保护测试)
  - [B12: REAL_PROVIDER_INTEGRATION_PLAN.md 生成](#b12-real_provider_integration_planmd-生成)
- [执行顺序](#执行顺序)
- [文件变更清单汇总](#文件变更清单汇总)

---

## 任务 A: Phase III-B — 马登工装真实品牌采集补测

### A1: CollectorExecutionReport 写入修复

#### 当前状态

- **代码层面**: `backend/app/tasks/collection.py` 中 `_do_collect()` 已在所有路径（成功/失败/阻塞/启动）正确创建 `CollectorExecutionReport` 并调用 `session.add(report)` + `session.flush()`
- **DB 层面**: `collector_execution_reports` 表记录为 0 条
- **根因**: 最可能是 migration `005_add_collector_execution_reports` 未对实际数据库应用（现有测试使用内存 SQLite，未触及真实 PostgreSQL）

#### 修复步骤

| # | 操作 | 命令/代码 | 验证 |
|---|------|----------|------|
| 1 | 确认 PostgreSQL 运行 | `docker ps | grep postgres` 或 `pg_isready` | 服务运行 |
| 2 | 检查 migration 当前版本 | `cd /home/ctyun/Competitive-Product-Intelligence-System/backend && alembic current` | 应 >= `005_add_exec_reports` |
| 3 | 应用未运行的 migration | `alembic upgrade head` | 成功 |
| 4 | 验证表存在 | `psql -U cpis -d cpis -c "\d collector_execution_reports"` | 表存在，schema 正确 |
| 5 | 创建测试任务 | `POST /api/v1/collection-tasks {"source_url": "https://books.toscrape.com", "category_hint": "books"}` | 返回 201 |
| 6 | 等待完成并查 report | `GET /api/v1/collection-tasks/{task_id}/execution-reports` | 返回 ≥1 条 report |

#### 额外修复（如需要）

如果 migration 已应用但 report 仍为空，检查 `get_celery_session` 提交行为：

```python
# backend/app/core/database.py — 确保上下文管理器自动 commit
@contextlib.asynccontextmanager
async def get_celery_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # 确保提交
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

#### 需修改的文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `backend/app/services/task_service.py` | `_run_validation` 的验证失败路径中追加 `CollectorExecutionReport` 写入（当前 validation 失败的任务不会进入 `_do_collect`，无 report） | 中 |
| `backend/app/core/database.py` | 如 `get_celery_session` 缺少自动 commit，补全 | 仅当需要 |

---

### A2: DuckDuckGo 真实搜索发现

#### 搜索查询方案

使用 `DuckDuckGoSearchProvider`（`language="zh-CN"`, `max_results=10`），执行 4 组独立查询：

| # | 查询词 | 预期目标 | 优先级 | 说明 |
|---|--------|---------|--------|------|
| 1 | `"马登工装" 品牌 官网` | 官方主页/品牌介绍页 | ⭐⭐⭐ | 最可能找到百度百科或品牌集合页 |
| 2 | `"马登工装" Maden 男装` | 非电商平台品牌文章 | ⭐⭐⭐ | 寻找第三方评测或导购 |
| 3 | `"马登" 工装 淘宝 品牌 评价` | 第三方推荐文章 | ⭐⭐ | 电商平台外内容 |
| 4 | `Maden 工装 复古 男装 品牌介绍` | 新闻/媒体提及 | ⭐⭐ | 英文品牌名搜索 |

#### 搜索实现脚本

```python
# scripts/discover_maden_urls.py
"""使用 DuckDuckGo 发现马登工装公开 URL"""
import asyncio, json, sys
from urllib.parse import urlparse
sys.path.insert(0, "/home/ctyun/Competitive-Product-Intelligence-System/backend")
from app.providers.duckduckgo_provider import DuckDuckGoSearchProvider

BANNED_DOMAINS = {
    "xiaohongshu.com", "xhscdn.com", "douyin.com", "iesdouyin.com",
    "bilibili.com", "b23.tv", "zhihu.com", "weibo.com", "weibo.cn",
    "tieba.baidu.com",
}
HIGH_RISK_DOMAINS = {
    "taobao.com", "tmall.com", "detail.tmall.com", "item.taobao.com",
    "1688.com", "alibaba.com",
}

async def discover():
    provider = DuckDuckGoSearchProvider()
    queries = [
        '"马登工装" 品牌 官网',
        '"马登工装" Maden 男装',
        '"马登" 工装 淘宝 品牌 评价',
        'Maden 工装 复古 男装 品牌介绍',
    ]
    all_results, seen_urls = [], set()
    for i, query in enumerate(queries, 1):
        print(f"\n查询 {i}/4: {query}")
        results = await provider.search(query, max_results=10, language="zh-CN")
        for r in results:
            domain = (urlparse(r.url).hostname or "").lower()
            url_key = r.url.rstrip("/").lower()
            if url_key in seen_urls: continue
            seen_urls.add(url_key)
            banned = any(b in domain for b in BANNED_DOMAINS)
            high_risk = any(h in domain for h in HIGH_RISK_DOMAINS)
            risk = "blocked" if banned else ("high" if high_risk else "low")
            entry = {
                "query": query, "title": r.title, "url": r.url,
                "domain": domain, "snippet": (r.snippet or "")[:200],
                "risk_level": risk,
            }
            all_results.append(entry)
            print(f"  [{'🔴' if risk=='blocked' else '🟡' if risk=='high' else '🟢'}] {r.title}")
            print(f"  URL: {r.url}")
    output = {
        "brand": "马登工装 / Maden",
        "total_queries": len(queries),
        "total_results": len(all_results),
        "results": all_results,
        "summary": {
            "safe_count": sum(1 for r in all_results if r["risk_level"] == "low"),
            "high_risk_count": sum(1 for r in all_results if r["risk_level"] == "high"),
            "blocked_count": sum(1 for r in all_results if r["risk_level"] == "blocked"),
        }
    }
    with open("maden_discovery_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n总结果: {len(all_results)}, 安全: {output['summary']['safe_count']}, 拦截: {output['summary']['blocked_count']}")

if __name__ == "__main__":
    asyncio.run(discover())
```

#### 预期结果

马登工装（Maden）是淘宝/天猫强依赖品牌，预期发现结果：

| 结果类型 | 预期数量 | 来源 |
|---------|---------|------|
| 淘宝/天猫商品页 → **BLOCKED** | 较多 | `*.taobao.com`, `*.tmall.com` |
| 社交平台 → **BLOCKED** | 可能有 | 小红书/知乎等 |
| 百度百科/品牌介绍 → **LOW** | 0-1 | `baike.baidu.com` |
| 第三方评测 → **LOW** | 0-2 | 什么值得买/IT之家等 |
| **总计安全可采** | **0-3** | |

---

### A3: 候选 URL 风险评估

#### 风险评估逻辑

```python
from urllib.parse import urlparse

BLOCKED_PATTERNS = ["xiaohongshu", "douyin", "bilibili", "zhihu", "weibo", "tieba.baidu.com"]
HIGH_RISK_PATTERNS = ["taobao.com", "tmall.com", "1688.com", "alibaba.com"]

def assess_url_risk(url: str) -> str:
    domain = urlparse(url).hostname or ""
    for p in BLOCKED_PATTERNS:
        if p in domain.lower(): return "blocked"
    for p in HIGH_RISK_PATTERNS:
        if p in domain.lower(): return "blocked"  # 直接拦截
    return "low"
```

#### 候选 URL 白名单过滤

仅选择 `risk_level="low"` 的 URL 进入采集阶段。最多选 3 个。

#### 需创建的文件

| 文件 | 内容 |
|------|------|
| `scripts/discover_maden_urls.py` | 搜索发现脚本 |
| `maden_discovery_results.json` | 搜索结果 JSON（自动生成） |
| `PHASE_III_B_MADEN_DISCOVERY_REPORT.md` | 发现报告（已存在模板，需填充真实结果） |

---

### A4: 完整 CPIS Pipeline 采集执行

#### Pipeline 流程

```
Discovery → Candidates → RunPlan → CollectorSelector → CollectorRuntime → SourceSnapshot → Cleaner → Extractor → ProductVersion
```

#### 执行步骤

| 步骤 | 说明 | 实现方式 |
|------|------|---------|
| 1. 创建发现会话 | 使用 `POST /api/v1/discovery/sessions` | API 调用 |
| 2. 搜索与分类 | DuckDuckGo 搜索 + StubLLMProvider 分类 | DiscoveryService |
| 3. 候选来源筛选 | 选最多 3 个 safe URL | 手动选择 |
| 4. 创建 RunPlan/模板 | 使用 `POST /api/v1/discovery/sessions/{id}/create-template` | API 调用 |
| 5. 创建采集任务 | 对每个 safe URL 调用 `POST /api/v1/collection-tasks` | API 调用 |
| 6. URL 验证 | `validate_url` → 风险评估 | TaskService |
| 7. 采集执行 | CollectorSelector → DirectHttpCollector | Celery task `collect_url` |
| 8. HTML 清洗 | `HtmlCleaner` → trafilatura + bs4 | Celery task `clean_content` |
| 9. AI 提取 | `ProductExtractor` + `StubLLMProvider` | Celery task `extract_structured_data` |
| 10. 产品版本 | `ProductVersioningService.process_extraction` | 自动执行 |

#### 候选 URL 采集的预期结果

| URL | 预期状态 | 说明 |
|-----|---------|------|
| 百度百科 baike.baidu.com | `completed` | 公开可访问 |
| 第三方评测站 | `completed` 或 `failed` | 取决于站点反爬强度 |
| if no safe URLs | `BLOCKED_NO_SAFE_MADEN_URL_FOUND` | 所有结果均被拦截 |

#### 禁止行为

- ❌ 不使用 `books.toscrape.com` 替代
- ❌ 不使用 `example.com` 替代
- ❌ 不采集小红书/抖音/B站/知乎/微博/贴吧
- ❌ 不使用 `MockSearchProvider`（必须用 `DuckDuckGoSearchProvider`）

#### 需修改的文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| 无（全通过 API + 脚本执行） | | |

---

### A5: 验证与证据输出

#### 验证检查点

| # | 检查项 | 验证方式 | 通过条件 |
|---|--------|---------|---------|
| 1 | Migration 已应用 | `alembic current` | `005_add_exec_reports` |
| 2 | `collector_execution_reports` 表存在 | `\d collector_execution_reports` | 表存在 |
| 3 | 成功路径写入 report | 查 books.toscrape.com 任务 report | `status=success` |
| 4 | 阻塞路径写入 report | 查 blocked URL 任务 report | `status=blocked` |
| 5 | API 可查 report | `GET /{task_id}/execution-reports` | 返回数组 |
| 6 | DuckDuckGo 搜索正常 | 4 queries 均返回结果 | 无异常 |
| 7 | 马登 URL 风险评估正确 | 检查结果 | 所有 taobao/tmall → blocked |
| 8 | Pipeline stages 完整 | 查任务详情 | creation→validation→collection→(cleaning→extraction) |

#### 输出文件

| 文件 | 状态 | 内容 |
|------|------|------|
| `PHASE_III_B_EXECUTION_REPORT_FIX.md` | ✅ 已有模板 | 修复 CollectorExecutionReport 的完整方案 |
| `PHASE_III_B_MADEN_DISCOVERY_REPORT.md` | ✅ 已有模板 | 搜索发现策略与结果 |
| `PHASE_III_B_MADEN_COLLECTION_REPORT.md` | ✅ 已有模板 | 采集执行流程与报告 |
| `PHASE_III_B_FINAL_EVIDENCE.md` | ✅ 已有模板 | 最终证据汇总 |
| `scripts/discover_maden_urls.py` | ⚠️ 需创建 | 搜索发现脚本 |
| `maden_discovery_results.json` | ⚠️ 需生成 | 搜索发现结果 |
| `scripts/verify_execution_reports.py` | ⚠️ 需创建 | 报告修复验证脚本 |

---

## 任务 B: P0 Reality Alignment — 真实能力对齐修复

### B1: README.md 首屏文案修正

#### 当前 overclaim

**文件**: `README.md`  
**行 14**: `AI 驱动的竞品信息自动采集、结构化提取与分析系统。`  
**行 15**: `将散落在互联网上的公开竞品信息，转化为结构化的产品数据库和可追溯的商业情报。`

#### 修正方案

将 `AI 驱动` 替换为 `半自动化`，体现当前真实状态：

```markdown
<p align="center">
  V1 Core Pipeline + Provider-Ready Architecture。<br>
  将散落在互联网上的公开竞品信息，通过可配置的采集管道，转化为结构化的产品数据库。
</p>
```

#### 精确修改

```diff
-  AI 驱动的竞品信息自动采集、结构化提取与分析系统。<br>
-  将散落在互联网上的公开竞品信息，转化为结构化的产品数据库和可追溯的商业情报。
+  V1 Core Pipeline + Provider-Ready Architecture。<br>
+  将散落在互联网上的公开竞品信息，通过可配置的采集管道，转化为结构化的产品数据库。<br>
+  ⚠️ 当前基于 Stub/Mock Provider，真实 LLM/Search 集成待后续阶段接入。
```

#### 需修改的文件

| 文件 | 当前文本 | 替换文本 |
|------|---------|---------|
| `README.md` L14-16 | `AI 驱动的...可追溯的商业情报` | `V1 Core Pipeline + Provider-Ready...` |

---

### B2: 核心功能模块 overclaim 修正

#### 修正列表

| 文件 | 行 | 当前文本 (overclaim) | 修正文本 |
|------|---|---------------------|---------|
| `README.md` | 48 | `🧠 自然语言请求 → 🔍 AI 来源发现` | `🧠 自然语言请求 → 🔍 来源发现 (Mock Mode)` |
| `README.md` | 67 | `**AI 来源发现** — SearchProvider + LLMProvider 架构，从自然语言描述自动发现相关竞品信息来源。默认 DuckDuckGo，预留 OpenAI/Gemini/Claude/SerpAPI 接口。` | `**Discovery Provider Ready / Mock Mode** — SearchProvider + LLMProvider 接口已定义。默认 MockSearchProvider + StubLLMProvider（返回固定数据，无网络调用）。DuckDuckGoSearchProvider 代码已实现，但未经真实验证。预留 OpenAI/Gemini/Claude/SerpAPI 接口（均尚待实现）。` |
| `README.md` | 71 | `**AI 结构化提取** — ProductExtractor + ModelProvider 管道，将清洗后的 HTML 转换为结构化的 Product、ProductVersion、ProductEvidence 记录。置信度阈值 0.7 自动通过。` | `**AI 提取框架 (Stub Mode)** — ProductExtractor + StubLLMProvider 管道。当前提取返回模拟数据（stub 模式），置信度阈值 0.7 自动通过。真实 LLM 提取待后续阶段实现。` |
| `README.md` | 72 | `**产品版本管理** — 版本间差异对比、Changelog 生成、基于证据的提取（带来源归因）。` | `**产品版本管理** — 版本间差异对比、Changelog 生成（基于 stub 数据）。` |
| `README.md` | 213 | `**AI 层** — OpenAI 兼容 LLM API, DuckDuckGo Search` | `**AI 层 (Stub/Mock)** — OpenAICompatibleProvider 已实现，但默认使用 StubLLMProvider（无真实 LLM 调用）。DuckDuckGoSearchProvider 代码已实现。` |

### B3: 系统架构图 overclaim 修正

#### 架构图中的 providers 标签修正

**文件**: `README.md` L97-98

当前:
```
Search["SearchProvider<br/>DuckDuckGo / Stub<br/>OpenAI·Gemini·Claude·SerpAPI"]
LLM["LLMProvider<br/>Stub<br/>OpenAI·Gemini·Claude·DeepSeek·Qwen"]
```
修正为:
```
Search["SearchProvider<br/>DuckDuckGo (代码已就绪) / Mock (默认)<br/>OpenAI·Gemini·Claude·SerpAPI (预留)"]
LLM["LLMProvider<br/>Stub (默认, 无真实调用)<br/>OpenAI·Gemini·Claude·DeepSeek·Qwen (预留)"]
```

#### 需修改的文件

| 文件 | 修改内容 |
|------|---------|
| `README.md` L96-99 | Provider 子图标签修正 |

### B4: 技术栈标签修正

#### 当前 overclaim

README.md L213:
```
**AI 层** — OpenAI 兼容 LLM API, DuckDuckGo Search
```

#### 修正方案

```diff
- **AI 层** — OpenAI 兼容 LLM API, DuckDuckGo Search
+ **AI 层 (Mock/Stub)** — OpenAICompatibleProvider 已实现但默认使用 Stub；DuckDuckGoSearchProvider 代码就绪但未经真实验证
```

### B5: 路线图文案修正

#### 当前文本

README.md L220-224:
```
- **发现 Provider** — OpenAI Search / Gemini Search / Claude Search / SerpAPI
- **LLM Provider** — OpenAI / Gemini / Claude / DeepSeek / Qwen 提取与分类
- **采集运行时扩展** — RSS 订阅 / PDF 文档 / REST API / Scrapling / Crawl4AI
```

#### 修正方案

无需大幅修改，但可增加状态前缀以体现当前状态。建议改为：

```
- [🔲 REAL] **发现 Provider** — OpenAI Search / Gemini Search / Claude Search / SerpAPI（全部待实现）
- [🔲 REAL] **LLM Provider** — OpenAI / Gemini / Claude / DeepSeek / Qwen 提取与分类（全部待实现）
- [⚙️ CODE] **采集运行时扩展** — RSS 订阅 / PDF 文档 / REST API / Scrapling / Crawl4AI（代码就绪，功能开关关闭，需要真实验证）
```

### B6: RELEASE_NOTES.md overclaim 修正

#### 修正列表

| 行 | 当前文本 | 修正文本 |
|---|---------|---------|
| 10 | `process it through AI-powered structured extraction` | `process it through structured extraction (stub AI provider by default)` |
| 17 | `AI-Powered Structured Extraction — Leverages OpenAI-compatible LLMs to extract structured product data from raw HTML/text.` | `Structured Extraction Framework — Extractor pipeline with stub AI provider. OpenAI-compatible LLM provider code is ready but not wired as default. Real LLM integration pending.` |
| 18 | `Product Versioning & Diffing — Tracks changes between successive product snapshots with AI-generated changelogs.` | `Product Versioning & Diffing — Tracks changes between successive product snapshots (stub changelogs currently).` |

### B7: CHANGELOG.md overclaim 修正

#### 修正列表

| 行 | 当前文本 | 修正文本 |
|---|---------|---------|
| L21 | `Default stub AI provider` — ✅ 此处已正确说明 | 无需修改 |
| L43 | `AI discovery provider layer` — 描述为 `AI-powered discovery`，实际是接口层 | 将 `AI-powered discovery` 改为 `discovery provider interface layer` |
| L68 | `Verification suite for the "Maden" (麻登) competitive intelligence use case.` — 注意品牌名应为 `马登` 非 `麻登` | `马登` |
| L122 | `AI extractor framework with prompt versioning` — 此处应为 `Stub AI extractor framework` | 可保留 `AI extractor framework` 但上下文 context 应说明为 stub |

### B8: 英文/日文/韩文 README 同步修正

#### 需同步修正的 overclaim

所有 `README.en.md`, `README.ja.md`, `README.ko.md` 都需要同步修改相同的 overclaim。

#### 英文版关键位置

| 行 | 当前文本 | 修正文本 |
|---|---------|---------|
| L14 | `Automatically collect, extract, and analyze competitive product information from public web sources — transforming raw data into structured, actionable insights.` | `Collect, extract, and analyze competitive product information from public web sources. V1 Core Pipeline + Provider-Ready architecture; real LLM and search integrations pending.` |

### B9: Discovery 页面文案修正

#### 文件

`frontend/src/features/discovery/DiscoveryPage.tsx`

#### 当前 overclaim

L219: `正在搜索并分析来源...` → 实际是 MockSearchProvider 返回固定数据

#### 修正方案

```diff
- <Paragraph style={{ marginTop: 16, color: "#999" }}>正在搜索并分析来源...</Paragraph>
+ <Paragraph style={{ marginTop: 16, color: "#999" }}>
+   正在搜索并分析来源...
+   <br />
+   <Text type="warning" style={{ fontSize: 12 }}>
+     ⚡ Discovery Provider Ready / Mock Mode — 当前使用模拟数据，未调用真实搜索引擎
+   </Text>
+ </Paragraph>
```

#### 同时增加 Provider 指示器

在会话信息卡（L228-241）增加：

```tsx
// 添加 provider 模式标签
{currentSession.search_provider && (
  <Tag color={currentSession.search_provider === "mock" ? "orange" : "blue"}>
    搜索: {currentSession.search_provider === "mock" ? "Mock" : currentSession.search_provider}
  </Tag>
)}
{currentSession.model_provider && (
  <Tag color={currentSession.model_provider === "llm" ? "orange" : "blue"}>
    LLM: {currentSession.model_provider === "llm" ? "Stub" : currentSession.model_provider}
  </Tag>
)}
```

### B10: Provider 配置页/状态接口新增

#### 新增 API 端点

**文件**: `backend/app/api/discovery.py` 或新建 `backend/app/api/provider_status.py`

**路由**: `GET /api/v1/system/provider-status`

**返回格式**:

```json
{
  "current_search_provider": "mock",
  "current_llm_provider": "stub",
  "is_real_provider_enabled": false,
  "is_mock_mode": true,
  "search_provider_details": {
    "configured": "mock",
    "real_available": ["duckduckgo"],
    "description": "DuckDuckGoSearchProvider code is ready; MockSearchProvider is active (no network calls)"
  },
  "llm_provider_details": {
    "configured": "stub",
    "real_available": ["openai_compatible"],
    "has_api_key": true,
    "has_base_url": true,
    "has_model": true,
    "description": "OpenAICompatibleProvider code is ready; StubLLMProvider is active (no real LLM calls)"
  },
  "missing_env_keys": [],
  "collector_runtimes": {
    "direct_http": {"enabled": true, "verified": true},
    "playwright": {"enabled": false, "verified": false},
    "scrapling": {"enabled": false, "verified": false},
    "crawl4ai": {"enabled": false, "verified": false},
    "rss": {"enabled": false, "verified": false},
    "pdf": {"enabled": false, "verified": false},
    "api": {"enabled": false, "verified": false}
  }
}
```

#### 实现细节

```python
# backend/app/api/provider_status.py
from fastapi import APIRouter
from app.core import get_settings
from app.providers.config import get_search_provider_config, get_llm_provider_config

router = APIRouter(prefix="/api/v1/system", tags=["system"])

@router.get("/provider-status")
async def get_provider_status():
    settings = get_settings()
    search_config = get_search_provider_config()
    llm_config = get_llm_provider_config()
    
    search_provider = search_config.get("provider", "mock")
    llm_provider = llm_config.get("provider", "stub")
    
    missing_keys = []
    if llm_provider not in ("stub", "mock"):
        if not settings.LLM_API_KEY: missing_keys.append("LLM_API_KEY")
        if not settings.LLM_BASE_URL: missing_keys.append("LLM_BASE_URL")
        if not settings.LLM_MODEL: missing_keys.append("LLM_MODEL")
    
    return {
        "current_search_provider": search_provider,
        "current_llm_provider": llm_provider,
        "is_real_provider_enabled": search_provider not in ("mock", "stub") or llm_provider not in ("stub", "mock"),
        "is_mock_mode": search_provider in ("mock", "stub") and llm_provider in ("stub", "mock"),
        "search_provider_details": {
            "configured": search_provider,
            "real_available": ["duckduckgo"],
            "duckduckgo_verified": False,
        },
        "llm_provider_details": {
            "configured": llm_provider,
            "real_available": ["openai_compatible"],
            "has_api_key": bool(settings.LLM_API_KEY),
            "has_base_url": bool(settings.LLM_BASE_URL),
            "has_model": bool(settings.LLM_MODEL),
        },
        "missing_env_keys": missing_keys,
        "collector_runtimes": {
            "direct_http": {"enabled": True, "verified": True},
            "playwright": {"enabled": bool(getattr(settings, 'COLLECTOR_PLAYWRIGHT_ENABLED', False)), "verified": False},
            "scrapling": {"enabled": False, "verified": False},
            "crawl4ai": {"enabled": False, "verified": False},
            "rss": {"enabled": False, "verified": False},
            "pdf": {"enabled": False, "verified": False},
            "api": {"enabled": False, "verified": False},
        },
    }
```

#### 前端 Provider Status 页面组件

**新建文件**: `frontend/src/features/system/ProviderStatusPage.tsx`

显示表格：
| 项目 | 值 | 状态 |
|------|----|------|
| 当前搜索 Provider | mock | ⚪ Mock |
| 当前 LLM Provider | stub | ⚪ Stub |
| LLM_API_KEY 配置 | ✓/✗ | |
| LLM_BASE_URL 配置 | ✓/✗ | |
| LLM_MODEL 配置 | ✓/✗ | |
| 真实 LLM 集成 | — | 🔴 待实现 |
| 真实搜索集成 | — | 🔴 待实现 |

### B11: Overclaim 保护测试

#### 新建测试文件

**文件**: `backend/tests/test_overclaim_protection.py`

```python
"""P0 Reality Alignment — Tests that protect against overclaim.

These tests verify that any claim of "AI-powered" or "real provider"
is backed by actual configuration, and that mock/stub mode is
properly reflected in the system status.
"""

import pytest
from app.core import get_settings
from app.providers.config import get_search_provider_config, get_llm_provider_config
from app.providers.real_providers import create_real_search_provider, create_real_llm_provider
from app.providers.mock_providers import MockSearchProvider, StubLLMProvider

class TestNoOverclaim:
    """Tests that prevent claiming real AI capabilities when in stub mode."""

    def test_default_search_provider_is_mock(self):
        """Default SEARCH_PROVIDER should be 'mock', not a real provider."""
        config = get_search_provider_config()
        assert config.get("provider") in ("mock", "stub"), \
            f"Default search provider should be mock/stub, got '{config.get('provider')}'"

    def test_default_llm_provider_is_stub(self):
        """Default LLM_PROVIDER should be 'stub', not a real provider."""
        config = get_llm_provider_config()
        assert config.get("provider") in ("mock", "stub"), \
            f"Default LLM provider should be mock/stub, got '{config.get('provider')}'"

    def test_create_search_provider_returns_mock_by_default(self):
        """create_real_search_provider() should return MockSearchProvider by default."""
        provider = create_real_search_provider()
        assert isinstance(provider, MockSearchProvider), \
            f"Expected MockSearchProvider, got {type(provider).__name__}"

    def test_create_llm_provider_returns_stub_by_default(self):
        """create_real_llm_provider() should return StubLLMProvider by default."""
        provider = create_real_llm_provider()
        assert isinstance(provider, StubLLMProvider), \
            f"Expected StubLLMProvider, got {type(provider).__name__}"

    def test_readme_does_not_claim_ai_powered_without_real_llm(self):
        """README.md should not claim 'AI-powered' if LLM provider is stub."""
        config = get_llm_provider_config()
        llm_provider = config.get("provider", "stub")
        # Read README.md and check first paragraph
        import os
        readme_path = os.path.join(os.path.dirname(__file__), "../../README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            first_para = f.read()[:500]
        if llm_provider in ("stub", "mock"):
            # If we're in stub mode, README should not claim AI-powered as active
            assert "AI 驱动" not in first_para or "⚠️" in first_para, \
                "README claims AI-powered but LLM provider is stub"

    def test_provider_status_api_returns_mock_mode(self):
        """The provider status endpoint should accurately reflect mock mode."""
        # This test calls the actual API
        ...
```

### B12: REAL_PROVIDER_INTEGRATION_PLAN.md 生成

#### 新建文件

**文件**: `REAL_PROVIDER_INTEGRATION_PLAN.md`

#### 内容模板

```markdown
# Real Provider Integration Plan

## 当前状态

| Provider | 代码就绪 | 默认启用 | 真实验证 | 备注 |
|----------|---------|---------|---------|------|
| MockSearchProvider | ✅ | ✅ (默认) | ✅ | 返回固定 Xiaomi fixture 数据 |
| DuckDuckGoSearchProvider | ✅ | ❌ | ❌ | 代码已实现，未做真实调用验证 |
| StubLLMProvider | ✅ | ✅ (默认) | ✅ | 返回模拟分类/提取结果 |
| OpenAICompatibleProvider | ✅ | ❌ | ❌ | 代码已实现，需 API key |
| Reserved Providers | ✅ | ❌ | ❌ | 全部抛出 NotImplementedError |

## 集成优先级

### P1: DuckDuckGoSearchProvider 真实验证
- [ ] 设置 `SEARCH_PROVIDER=duckduckgo`
- [ ] 执行真实搜索查询（测试中文/英文）
- [ ] 验证搜索结果解析正确
- [ ] 写集成测试

### P2: OpenAICompatibleProvider 真实验证
- [ ] 配置 `LLM_PROVIDER=openai`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
- [ ] 执行真实 LLM 调用（简单 classify + extract）
- [ ] 验证返回格式正确
- [ ] 写集成测试

### P3: 认证检查与降级策略
- [ ] 缺少 API key 时自动降级到 stub
- [ ] 真实调用失败时自动回退
- [ ] 用户可见的错误提示

### P4: 预留 Provider 实现
- [ ] OpenAI/Gemini/Claude/SerpAPI SearchProvider
- [ ] OpenAI/Gemini/Claude/DeepSeek/Qwen LLMProvider

## 实现指南

### 如何启用真实 Provider
1. 修改 `.env`: `SEARCH_PROVIDER=duckduckgo` 或 `LLM_PROVIDER=openai`
2. 配置对应 API key 和 endpoint
3. 重启后端服务
4. 访问 `GET /api/v1/system/provider-status` 确认

### 如何添加新的 Provider
1. 在 `app/providers/` 下创建实现文件
2. 实现 `SearchProvider` 或 `LLMProvider` 接口
3. 在 `app/providers/real_providers.py` 的工厂函数中注册
4. 添加对应测试
```

---

## 执行顺序

### Phase 1: CollectorExecutionReport 修复 + 验证（任务 A 前置）

```
Step 1: 检查 migration 状态 → 应用 migration → 验证表存在
Step 2: 创建测试任务（books.toscrape.com）→ 验证 report 写入
Step 3: 如失败 → 检查 get_celery_session → 修复提交行为
```

### Phase 2: 马登工装采集（任务 A 主体）

```
Step 4: 创建 scripts/discover_maden_urls.py
Step 5: 执行 4 组 DuckDuckGo 搜索
Step 6: 输出 maden_discovery_results.json
Step 7: 风险评估 → 选择最多 3 个 safe URL
Step 8: 创建采集任务（通过 API）
Step 9: 监控任务状态 → 验证全 pipeline
Step 10: 输出 PHASE_III_B_FINAL_EVIDENCE.md
```

### Phase 3: Overclaim 修复（任务 B）

```
Step 11: 修正 README.md（首屏 + 功能模块 + 架构图 + 技术栈 + 路线图）
Step 12: 修正 RELEASE_NOTES.md
Step 13: 修正 CHANGELOG.md（品牌名修正）
Step 14: 修正 docs/README.en.md / README.ja.md / README.ko.md
Step 15: 修正 DiscoveryPage.tsx 文案
Step 16: 新增 GET /api/v1/system/provider-status 端点
Step 17: 新建 tests/test_overclaim_protection.py
Step 18: 新建 REAL_PROVIDER_INTEGRATION_PLAN.md
```

---

## 文件变更清单汇总

### 需修改的文件

| 文件 | 任务 | 修改内容 | 风险 |
|------|------|---------|------|
| `README.md` | B1-B5 | 首屏文案、功能模块、架构图、技术栈、路线图 overclaim 修正 | 低 — 纯文案修改 |
| `release/RELEASE_NOTES.md` | B6 | AI-powered → Structured Extraction Framework | 低 — 纯文案修改 |
| `release/CHANGELOG.md` | B7 | "麻登" → "马登", AI-powered → interface layer | 低 |
| `docs/README.en.md` | B8 | 同步修正 overclaim | 低 |
| `docs/README.ja.md` | B8 | 同步修正 overclaim | 低 |
| `docs/README.ko.md` | B8 | 同步修正 overclaim | 低 |
| `frontend/src/features/discovery/DiscoveryPage.tsx` | B9 | Mock Mode 指示器 + 文案 | 中 — React 组件 |
| `backend/app/core/database.py` | A1 | 如需要，修复 get_celery_session 自动 commit | 高 — 核心数据库 |
| `backend/app/services/task_service.py` | A1 | validation 失败路径追加 CollectorExecutionReport | 中 |
| `backend/app/api/discovery.py` 或新建 `backend/app/api/provider_status.py` | B10 | 新增 provider-status 端点 | 低 |

### 需新增的文件

| 文件 | 任务 | 内容 | 风险 |
|------|------|------|------|
| `scripts/discover_maden_urls.py` | A2 | DuckDuckGo 搜索发现脚本 | 低 |
| `scripts/verify_execution_reports.py` | A5 | CollectorExecutionReport 自动验证 | 低 |
| `maden_discovery_results.json` | A2 | 搜索发现结果（自动生成） | 低 |
| `backend/tests/test_overclaim_protection.py` | B11 | Overclaim 保护测试 | 低 |
| `REAL_PROVIDER_INTERGRATION_PLAN.md` | B12 | 真实 Provider 集成计划 | 低 |
| `frontend/src/features/system/ProviderStatusPage.tsx` | B10 | Provider 状态页面（可选） | 中 |

### 无需修改的已验证文件

| 文件 | 原因 |
|------|------|
| `backend/app/tasks/collection.py` | `_do_collect()` 已正确创建 CollectorExecutionReport |
| `backend/app/models/collector_execution_report.py` | Model 定义正确 |
| `backend/app/providers/duckduckgo_provider.py` | 代码就绪，无需修改 |
| `backend/app/providers/mock_providers.py` | Mock 实现正确 |
| `backend/app/providers/interfaces.py` | 接口定义正确 |
| `backend/app/providers/reserved_providers.py` | 预留实现正确（均抛出 NotImplementedError） |
| `backend/app/providers/real_providers.py` | 工厂函数路由正确 |
| `backend/app/extractors/ai_provider.py` | OpenAICompatibleProvider 代码就绪 |
| `backend/app/services/discovery_service.py` | Discovery 编排正确，默认使用 Mock |
| `backend/app/collectors/selector.py` | 风险评估和选择器正确 |

---

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| DuckDuckGo 搜索被限制/返回空 | 无法发现任何马登 URL | 中 | 使用多个查询词，接受 `BLOCKED_NO_SAFE_MADEN_URL_FOUND` |
| PostgreSQL 未运行 | Migration 无法应用 | 低 | 使用 Docker Compose 启动 |
| Celery worker 未运行 | 采集任务不会执行 | 中 | 启动 Celery: `celery -A app.tasks worker --loglevel=info` |
| Redis 未运行 | Celery broker 不可用 | 低 | 使用 Docker Compose 启动 |
| 淘宝/天猫反爬升级 | 即使 low-risk URL 也可能被反爬拦截 | 高 | DirectHttpCollector 已有错误处理逻辑 |
| 前端构建失败 | Provider Status 页面可能无法编译 | 低 | 纯后端 API 端点无此风险 |

---

## 验收标准

### 任务 A 验收

- [ ] `collector_execution_reports` 表存在且有记录
- [ ] DuckDuckGo 搜索返回真实结果（非空）
- [ ] 马登工装 URL 风险评估正确（taobao/tmall → blocked）
- [ ] 如存在 safe URL，成功走完完整的 CPIS Pipeline
- [ ] 如无 safe URL，如实报告 `BLOCKED_NO_SAFE_MADEN_URL_FOUND`
- [ ] 所有 4 份 III-B 证据报告已填写真实数据

### 任务 B 验收

- [ ] README.md 首屏不再 claim "AI 驱动"
- [ ] README.md 功能模块 table 明确标注 Mock/Stub 模式
- [ ] RELEASE_NOTES.md 修正 AI-powered 表述
- [ ] CHANGELOG.md 品牌名修正
- [ ] Discovery 页面显示 Mock Mode 指示器
- [ ] `GET /api/v1/system/provider-status` 返回正确状态
- [ ] `test_overclaim_protection.py` 测试通过
- [ ] `REAL_PROVIDER_INTEGRATION_PLAN.md` 已生成
