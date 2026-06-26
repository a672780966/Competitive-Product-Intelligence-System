# PHASE H — Scrapling / crawl4ai 采集增强评估报告

> **Generated**: 2026-06-26
> **Run ID**: run_20260626_h05_evaluation

---

## 1. 当前 CPIS 采集栈

| 组件 | 版本 | 用途 |
|------|------|------|
| **httpx** | 0.28.1 | HTTP 请求（HttpxCollector） |
| **beautifulsoup4** | 4.15.0 | HTML 解析 |
| **lxml** | 5.4.0 | XML/HTML 解析引擎 |
| **trafilatura** | 1.12.2 | 正文提取（cleaner） |
| **playwright** | 1.60.0 | JS 渲染（PlaywrightCollector） |

## 2. Scrapling 评估

| 维度 | 评估 |
|------|------|
| **用途** | 智能 HTML 解析库，CSS/XPath 选择器增强 |
| **与现有栈对比** | 功能重叠 beautifulsoup4 + lxml |
| **增量价值** | 自适应 CSS 选择器、自动检测网页变化、anti-bot 检测 |
| **安装** | ❌ 未安装，需额外依赖 |
| **许可证** | MIT |
| **合适方式** | 可作为 `CollectorSelector` 的 feature flag 可选项 |
| **建议** | 🟢 **低优先级 feature flag** — 当现有栈遇到反爬/动态选择器问题时启用 |

## 3. crawl4ai 评估

| 维度 | 评估 |
|------|------|
| **用途** | AI 驱动的网页爬取，自动提取结构化数据 |
| **与现有栈对比** | 功能覆盖 httpx + Playwright + trafilatura + 部分 extraction |
| **增量价值** | LLM 驱动的自适应爬取、自动处理动态内容、结构化输出 |
| **安装** | ❌ 未安装，需 playwright + Python 依赖 |
| **许可证** | Apache 2.0 |
| **风险** | 引入 AI 推理延迟；对公开网页可能过度采集；与现有 Celery pipeline 配合需改造 |
| **合适方式** | 仅作为 OpenClaw 外部 Agent 的采集引擎，不直接接入 CPIS pipeline |
| **建议** | 🟡 **中优先级 feature flag** — 适合 OpenClaw 侧使用，不适合 CPIS 后端直接集成 |

## 4. 对比总表

| 能力 | 当前栈 | +Scrapling | +crawl4ai |
|------|--------|------------|-----------|
| **HTTP 请求** | ✅ httpx | → 不变 | → 内置 |
| **JS 渲染** | ✅ Playwright | → 不变 | → 内置 |
| **HTML 解析** | ✅ bs4 + lxml | → 增强 | → 内置 |
| **正文提取** | ✅ trafilatura | → 不变 | → 内置 |
| **AI 自适应爬取** | ❌ | ❌ | ✅ |
| **反爬检测** | ❌ | 🟡 部分 | ✅ |
| **结构化输出** | ✅ Celery pipeline | → 不变 | 🟡 需适配 |
| **安装复杂度** | 已在 poetry | 低 | 中 |
| **适合 CPIS 后端直接集成** | — | 🟢 可 | 🟡 不建议 |
| **适合 OpenClaw Agent 使用** | — | 🟡 可 | 🟢 推荐 |

## 5. 建议

### 短期（阶段 H 之后，不进入当前迭代）
- **不做任何替换** — 当前 httpx + Playwright + trafilatura 栈满足 V1 需求
- 在 `CollectorSelector` 中预留 feature flag 接口

### 中期（V1.5 / V2）
- **Scrapling** → 当遇到动态 CSS 选择器或反爬升级时，作为 `CollectorSelector` 的一个 feature flag 切换选项
- **crawl4ai** → 推荐给 OpenClaw `cpis-info-collector` 作为外部采集引擎，不直接接入 CPIS 后端 pipeline

### 不建议
- 直接替换当前 `HttpxCollector` / `PlaywrightCollector`
- 将 crawl4ai 加入 Celery pipeline 依赖
- 在阶段 H 内安装或集成

## 6. Verdict

| 项 | 结论 |
|----|------|
| 当前栈是否充足 | ✅ 满足 V1 需求 |
| Scrapling 是否建议 feature flag | 🟢 **建议低优先级** — 遇到反爬时切换 |
| crawl4ai 是否建议 feature flag | 🟡 **建议中优先级** — 仅给 OpenClaw 使用 |
| 是否进入当前阶段 | ❌ **禁止** — 仅评估，不集成 |
