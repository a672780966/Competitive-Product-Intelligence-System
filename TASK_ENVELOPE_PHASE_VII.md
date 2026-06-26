# TaskEnvelope: Phase VII — Crawler Capability Upgrade

## 分区执行方案

### 分区 A: DirectHttpCollector 增强 + Failure Intelligence
- A1: 重写 `collectors/direct_http.py` — UA轮换/分隔超时/gzip-br/charset/Content-Type/Referer伪装/Retry退避/Failure Intel
- A2: 新增 `collectors/failure_intelligence.py` — FailureAnalysis 数据类 + 15种分类 + 分析函数
- A3: 修改 `collectors/base.py` — CollectResult 增加 failure_intelligence 字段
- A4: 修改 `collectors/registry.py` — CollectResult 对齐
- A5: 安装 `chardet` 依赖
- A6: Migration 新增 failure_intelligence 字段到 CollectorExecutionReport

### 分区 B: Sitemap/RSS/Robots Discovery
- B1: 新增 `collectors/sitemap_discovery.py` — 从 sitemap.xml 发现公开 URL
- B2: 新增 `collectors/robots_discovery.py` — 从 robots.txt 发现公开 URL
- B3: 修改 RunPlanExecutor._resolve_urls() — 集成 sitemap/search discovery
- B4: 默认限制 ≤10 URL

### 分区 C: Playwright/Scrapling/Crawl4AI Feature Flags + 马登重测
- C1: 确认 PlaywrightCollector feature flag (默认false)
- C2: 确认 Playwright 失败写 CollectorExecutionReport
- C3: Scrapling/Crawl4AI adapter (feature flag, 默认false)
- C4: 重新测试马登工装 — 先用增强 DirectHttpCollector
- C5: 如果失败，记录 FailureIntelligence

### 分区 D: 测试
- D1: DirectHttp enhanced tests
- D2: Failure Intelligence tests
- D3: Sitemap discovery tests
- D4: Playwright flag disabled tests
- D5: Blocked source tests
- D6: Maden safe-url discovery test with mocked fixture

## 验证
1. Enhanced DirectHttpCollector 采集 example.com 正常
2. Charset 检测 (非UTF8页面)
3. gzip/br 请求头
4. Failure Intelligence 分类正确 (403→retryable, DNS→non-retryable)
5. Sitemap discovery 解析 sitemap.xml
6. Playwright flag 关闭时不使用 Playwright
7. CollectorExecutionReport 含 failure_type/retryable 字段
8. 全量 pytest 通过
9. Frontend build 通过
