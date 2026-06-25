# Backend - Workflow Discovery Agent

FastAPI + SQLAlchemy + Celery + Anthropic SDK + Playwright

## Setup

```bash
# 安装依赖（uv 已替代 Poetry，10-100x 快）
uv sync

# 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY 和 SERPAPI_KEY

# 启动开发服务器
uv run uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/health 应返回 `{"status": "ok", ...}`
访问 http://localhost:8000/docs 查看 OpenAPI 文档（DEBUG=true 时）

## 项目结构

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # pydantic-settings 配置
│   ├── core/              # 通用工具（日志、安全）
│   ├── db/                # SQLAlchemy session
│   ├── models/            # ORM 模型（Phase 3）
│   ├── api/v1/            # REST 端点（Phase 3）
│   ├── agent/             # Agent 核心（Phase 1）
│   ├── search/            # 搜索+抓取+评分（Phase 2）
│   ├── worker/            # Celery 任务（Phase 3）
│   └── middleware/        # 多租户、限流（Phase 3）
├── alembic/               # 数据库迁移（Phase 3）
├── tests/                 # 测试
│   ├── agent/
│   ├── search/
│   ├── api/
│   └── golden_set/        # 证据链黄金集（Phase 2）
└── pyproject.toml
```

## 开发命令

```bash
uv run pytest                          # 跑测试
uv run ruff check .                    # lint
uv run ruff format .                   # 格式化
uv run mypy app/                       # 类型检查
uv run uvicorn app.main:app --reload   # 开发服务器
```
