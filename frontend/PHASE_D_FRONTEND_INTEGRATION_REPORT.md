# Phase D Frontend Integration Report

## 概述
将阶段 C 完成的所有非飞书后端 API 接入前端界面，替换占位数据为真实 API 调用。

## 修改文件列表（14 files）

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `src/types/index.ts` | 新增 SnapshotResponse, PipelineStageStatus, PipelineStatusResponse, VersionSummary, ProductDetailResponse, PaginatedProductResponse, SyncRecord, PaginatedSyncResponse; 扩展 ProductSummary, TaskDetailResponse, ReviewDetailResponse |
| 修改 | `src/api/client.ts` | 新增 productsApi, syncApi, reviewsApi.update; 修复所有 API 路径为 /api/v1/; 统一类型导入 |
| 修改 | `src/features/products/ProductList.tsx` | 替换占位数据为 productsApi.list; 新增 status/domain/keyword 筛选 |
| 新增 | `src/features/products/ProductDetail.tsx` | Product detail 页面: 产品信息 + 版本历史 |
| 修改 | `src/features/tasks/TaskDetail.tsx` | 新增 snapshot 快照信息卡片 + pipeline_status 管道状态卡片 |
| 修改 | `src/features/reviews/ReviewDetail.tsx` | 新增 PATCH 保存修改按钮; 展示已保存 corrections/changed_fields; 使用 source_text |
| 修改 | `src/features/reviews/ReviewList.tsx` | 修复 unused import |
| 修改 | `src/features/sync/SyncRecords.tsx` | 替换代理调用为 syncApi.list; 新增 status 筛选 |
| 修改 | `src/features/tasks/TaskList.tsx` | 修复 unused import |
| 修改 | `src/features/reports/ReportPage.tsx` | 修复 unused import |
| 修改 | `src/components/Layout.tsx` | 改用 Outlet 支持嵌套路由; 移除 unused import |
| 修改 | `src/App.tsx` | 新增 products/:id → ProductDetail 路由 |
| 删除 | `src/routes/index.tsx` | 删除 stale 路由配置（App.tsx 未使用） |
| 修改 | `tsconfig.node.json` | 修复 composite + allowImportingTsExtensions |

## 新增页面列表
- `/products/:id` → ProductDetailPage（产品详情含版本历史）

## 前端 API client 变更
- **productsApi.list(params?)** → `GET /api/v1/products`
- **productsApi.get(id)** → `GET /api/v1/products/{id}`
- **syncApi.list(params?)** → `GET /api/v1/sync-records`
- **syncApi.get(id)** → `GET /api/v1/sync-records/{id}`
- **reviewsApi.update(versionId, body)** → `PATCH /api/v1/reviews/{version_id}`

## Build 结果
```bash
npm run build
> tsc -b && vite build
✓ built in 8.59s
```
TypeScript 编译 + Vite 构建均通过，无错误。

## 后端测试结果
```bash
pytest -q
241 passed, 1 warning in 25.02s
```
基线 241 无回归。

## Codex Final Gate 验证
- ✅ 所有 API 端点与后端匹配
- ✅ TypeScript 类型与 Pydantic schema 对齐
- ✅ 无飞书误接入（仅展示已有 feishu_record_id）
- ✅ 无硬编码 secret/env
- ✅ 无占位数据残留
- ✅ Build 通过
- ✅ 后端 241 测试通过
