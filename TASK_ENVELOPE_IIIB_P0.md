# TaskEnvelope: Phase III-B Maden + P0 Reality Alignment

## 前置修复 (A1+B 共享)
### A1: CollectorExecutionReport 写入修复
1. `cd /home/ctyun/Competitive-Product-Intelligence-System/backend`
2. 检查 PostgreSQL 运行: `docker ps | grep postgres` 或启动 demo compose
3. `alembic current` — 检查 migration 版本
4. `alembic upgrade head` — 应用未运行 migration
5. 检查表: `psql -U ... -d ... -c "\d collector_execution_reports"`
6. 创建测试任务验证 report 写入:
   - POST /api/v1/collection-tasks {url: "https://example.com"}
   - 等待完成
   - GET /api/v1/collection-tasks/{task_id}/execution-reports
7. 如果 celery session 无自动 commit，修复 `backend/app/core/database.py` get_celery_session
8. 如果 validation 失败路径不写 report，修复 `backend/app/services/task_service.py`

## 任务 A: 马登工装真实品牌采集

### A2: DuckDuckGo 搜索发现
1. 创建 `scripts/discover_maden_urls.py` (使用 DuckDuckGoSearchProvider, 4 组查询)
2. 执行: `cd /home/ctyun/Competitive-Product-Intelligence-System/backend && python3 scripts/discover_maden_urls.py`
3. 输出 `maden_discovery_results.json`
4. 写入 `PHASE_III_B_MADEN_DISCOVERY_REPORT.md`

### A3: URL 风险评估
- blocked 域: xiaohongshu/douyin/bilibili/zhihu/weibo/tieba.baidu.com
- blocked 高风险: taobao/tmall/1688/alibaba
- 只选 risk_level="low" 的最多 3 个 URL

### A4: 完整 CPIS Pipeline 采集
1. 对每个 safe URL 创建 CollectionTask
2. 通过 CollectorSelector → DirectHttpCollector 采集
3. 记录 SourceSnapshot, ProductVersion
4. 验证 CollectorExecutionReport 写入

### A5: 验证
- DB 写入检查
- Pipeline stages 完整
- 马登品牌相关确认
- 采集报告输出

## 任务 B: P0 Reality Alignment

### B1: README.md 首屏
- "AI 驱动" → "V1 Core Pipeline + Provider-Ready Architecture"
- 增加 ⚠️ Stub/Mock 提示

### B2: README.md 核心功能
- "AI 来源发现" → "来源发现 (Mock Mode)"
- "AI 结构化提取" → "AI 提取框架 (Stub Mode)"
- 所有 overclaim 修正

### B3: README.md 架构图
- Provider 子图标签修正 (Mock/Stub 标注)

### B4: README.md 技术栈
- "AI 层" → "AI 层 (Mock/Stub)"

### B5: README.md 路线图
- 增加 [🔲 REAL] [⚙️ CODE] 状态前缀

### B6: RELEASE_NOTES.md
- "AI-powered extraction" → "stub AI provider"

### B7: CHANGELOG.md
- "AI-powered discovery" → "discovery provider interface layer"

### B8: 多语言 README 同步
- en.md/ja.md/ko.md 同样修正 overclaim

### B9: Discovery 页面文案
- 增加 Mock Mode 指示器

### B10: Provider 状态 API
- 新建 GET /api/v1/system/provider-status
- 新建 frontend ProviderStatusPage

### B11: Overclaim 保护测试
- 新建 tests/test_overclaim_protection.py

### B12: REAL_PROVIDER_INTEGRATION_PLAN.md

## 验证项
1. CollectorExecutionReport 写入成功
2. DuckDuckGo 搜索真实结果
3. 马登 URL 正确定义
4. README 无 overclaim
5. Release Notes 无 overclaim
6. Provider status API 可用
7. Overclaim 测试通过
8. backend pytest 全部通过
9. frontend build 通过
