# Workflow Discovery Agent

> 企业级工作流发现 SaaS：基于 Anthropic 原生 tool use 的真 Agent，自动搜索、抓取、评估证据并生成结构化流程报告。

[![CI](https://github.com/haowenzheng-art/searchengine/actions/workflows/ci.yml/badge.svg)](https://github.com/haowenzheng-art/searchengine/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 这是什么

Workflow Discovery Agent（WDA）是一个帮你分析业务流程的 SaaS 产品。输入一句话（如"招聘筛选流程"），Agent 会：

1. **搜索**相关真实文章（DuckDuckGo）
2. **评估**每个 URL 的相关度（规则 + LLM 三层评分，砍掉首页/歧义/SEO 噪音）
3. **抓取**高分证据的正文（Playwright + BeautifulSoup）
4. **提取**结构化工作流、痛点、Agent 介入点
5. **计算** ROI 并生成报告

全程工具调用持久化到数据库，可在 UI 查看 Agent 执行时间线。

## 核心特性

- **真 Agent**：Anthropic SDK 原生 tool use 循环，LLM 自主决策调用哪个工具，不是硬编码流水线
- **真实证据链**：三层评分架构（规则 → Haiku → Sonnet），首页/歧义命中自动过滤，不注水
- **执行可视化**：每个 tool_call 持久化，UI 渲染时间线，可展开查看输入输出
- **断点续跑**：messages 存 JSONB，进程崩溃可从 DB 恢复
- **多用户隔离**：JWT + argon2，跨用户访问返回 404（不暴露存在性）
- **异步任务队列**：Celery + Redis，长任务不阻塞 API
- **用量统计**：每日/每月 token 消耗、工具调用次数、工作流数

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 async + Alembic |
| 数据库 | PostgreSQL 16 |
| 队列 | Redis 7 + Celery 5 |
| LLM | Anthropic SDK（火山引擎方舟 Claude 兼容协议，底层 GLM-5.2） |
| 搜索 | ddgs（DuckDuckGo Search） |
| 抓取 | Playwright + BeautifulSoup |
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| 状态 | TanStack Query + Zustand |
| 部署 | Docker Compose |

## 快速开始

### 前置要求

- Docker + Docker Compose
- Node.js 20+ (前端开发)
- Python 3.11+ (后端开发，或用 Docker)
- 火山引擎方舟 API Key（或 Anthropic API Key）

### 1. 克隆 + 配置

```bash
git clone https://github.com/haowenzheng-art/searchengine.git
cd searchengine
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入 VOLC_API_KEY / VOLC_BASE_URL / VOLC_MODEL
```

### 2. 启动基础设施

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis
# postgres 在 5433, redis 在 6380 (避让默认端口)
```

### 3. 启动后端

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
# API: http://localhost:8001
# Swagger: http://localhost:8001/docs
```

### 4. 启动 Celery worker（另一个终端）

```bash
cd backend
uv run celery -A app.worker.celery_app worker --loglevel=info --pool=solo -Q wda_default
```

### 5. 启动前端（第三个终端）

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

### 6. 使用

1. 打开前端，注册第一个账号（自动成为 admin）
2. 点"新建工作流"，输入"招聘筛选流程"
3. 在详情页查看 Agent 实时执行时间线
4. 完成后查看报告和证据链

## 真实中文 Workflow 基准结果

最新端到端验证使用火山引擎方舟 Claude 兼容协议（底层 GLM-5.2），查询词为 `招聘筛选流程`。

| 指标 | 优化前：串行工具调用（WF #11, Agnes） | 优化后：批量工具 + Volc（WF #18） | 改善 |
|------|--------------------------------------|-----------------------------------|------|
| 状态 | completed | completed | - |
| 总耗时 | 12m49s | 11m17s | 约 12% 更快 |
| Agent 迭代数 | 18 | 11 | -39% |
| Tool calls | 18 | 13 | -28% |
| 输入 tokens | 190,364 | 28,139 | -85% |
| 输出 tokens | 10,396 | 18,406 | 报告更完整 |
| 证据链 | 单条 score/fetch 串行 | 24 条证据、13 条高分、12 条已抓取 | 更完整 |

关键优化点：`score_evidence_batch` / `fetch_page_batch` 将多次串行工具调用合并为批量工具；Volc 限流后将评分并发降到 3，并加入 2s/4s/8s 指数退避重试。最新 #18 中 `score_evidence_batch` 用时 145.95s 但没有失败，证明重试逻辑生效。

产品截图见 `docs/screenshots/`：Dashboard、工作流时间线、证据链、报告页均已用 #18 的中文真实工作流重新捕获。

## 项目结构

```
searchengine/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # pydantic-settings
│   │   ├── core/security.py     # JWT + argon2
│   │   ├── db/                  # async session
│   │   ├── models/              # User/Workflow/AgentRun/ToolCall/Evidence/UsageRecord
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # tool use 主循环
│   │   │   ├── tools/            # 8 个工具
│   │   │   └── state.py          # DB 持久化
│   │   ├── search/              # 搜索 + 抓取 + 三层评分
│   │   ├── usage/service.py     # UPSERT + 聚合
│   │   ├── worker/              # Celery tasks
│   │   └── api/v1/              # auth/workflows/usage/feedback
│   ├── alembic/                 # 数据库迁移
│   └── tests/                   # 38+ 个单元测试
├── frontend/
│   ├── src/
│   │   ├── pages/               # Login/Register/Dashboard/NewWorkflow/WorkflowDetail/Usage
│   │   ├── components/          # AppLayout + shadcn/ui
│   │   ├── stores/auth.ts       # Zustand auth
│   │   └── lib/                 # api client + types
│   └── package.json
├── infra/
│   └── docker-compose.yml       # postgres 5433 + redis 6380
├── docs/
│   ├── deployment.md
│   ├── api.md
│   ├── architecture.md
│   ├── screenshots/             # 产品截图（真实中文 workflow #18）
│   └── product-pages.md         # 产品页面介绍 + 截图
└── legacy/                       # 旧代码归档
```

## 文档

- [部署指南](docs/deployment.md)
- [API 文档](docs/api.md)
- [架构设计](docs/architecture.md)
- [产品页面介绍](docs/product-pages.md)

## 开发

```bash
# 后端测试
cd backend && uv run pytest tests/

# 前端 build
cd frontend && npm run build

# 数据库迁移
cd backend && uv run alembic revision --autogenerate -m "description"
```

## 端口避让

本项目使用非默认端口避免冲突：
- Postgres: 5433（默认 5432）
- Redis: 6380（默认 6379）
- 后端 API: 8001（默认 8000）
- 前端: 5173

## License

MIT
