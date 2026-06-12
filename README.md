# CPIS V1

Competitive Product Intelligence System V1 — 竞品公开信息自动采集与分析系统

## 项目定位

企业内部使用的竞品公开信息采集与分析系统，将公开产品页面整理为可复用的结构化竞品资产。

**服务对象：** 产品团队、外贸销售团队、市场团队、研发团队、管理层

## 核心闭环

```
公开链接录入 → 合规校验 → 网页采集 → 内容清洗
→ AI 结构化抽取 → 产品入库与版本管理 → 人工复核
→ 飞书多维表格同步 → 竞品简报生成
```

## 快速启动

### 前置要求

- Docker & Docker Compose
- Python 3.12+
- Node.js 22+

### 1. 环境变量

```bash
cp .env.example .env
# 编辑 .env，填入飞书、AI 等配置
```

### 2. Docker 启动

```bash
docker compose up -d
```

启动后访问：
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 前端页面：http://localhost:3000

### 3. 本地开发

#### 后端

```bash
cd backend
poetry install
cp ../.env .
uvicorn app.main:app --reload
```

#### 前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 数据库迁移

```bash
cd backend
alembic upgrade head
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI (Python 3.12) |
| ORM | SQLAlchemy 2 + Alembic |
| 数据库 | PostgreSQL 16 |
| 缓存/消息 | Redis 7 + Celery 5 |
| 数据采集 | httpx + BeautifulSoup4 + trafilatura + Playwright |
| 前端框架 | React 19 + TypeScript + Vite |
| UI 组件 | Ant Design 5 |
| 状态管理 | TanStack Query |
| 日志 | structlog |
| 部署 | Docker Compose |

## 开发策略

1. **先完成最小闭环**，不做临时 Demo
2. 第一阶段优先：链接录入 → 合规校验 → 网页采集 → 内容清洗 → AI 抽取 → 入库 → 飞书同步 → 简报生成
3. 后续迭代：仪表盘、RBAC、竞品对比、PDF 导出

## 目录结构

```
cpis-v1/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 配置、日志、数据库
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── schemas/      # Pydantic 校验
│   │   ├── repositories/ # 数据访问层
│   │   ├── services/     # 业务逻辑
│   │   ├── collectors/   # 网页采集
│   │   ├── cleaners/     # 内容清洗
│   │   ├── extractors/   # AI 抽取
│   │   ├── analyzers/    # 分析
│   │   ├── integrations/ # 飞书等外部集成
│   │   ├── tasks/        # Celery 任务
│   │   └── prompts/      # AI Prompt
│   ├── alembic/          # 数据库迁移
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/          # API 调用
│       ├── components/   # 通用组件
│       ├── features/     # 业务模块
│       ├── layouts/      # 布局
│       ├── routes/       # 路由
│       ├── stores/       # 状态管理
│       └── types/        # TS 类型
├── docker-compose.yml
└── .env.example
```

## V1 明确不做

- 不绕过登录、验证码、付费墙和反爬机制
- 不做代理池和高并发爬虫
- 不采集私域、客户、个人敏感信息
- 不做自动发布营销内容
- 不做无人工复核的高风险业务决策
- 不做完整知识库问答
- 不做企业级 SSO
