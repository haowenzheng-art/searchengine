# 部署指南

## 开发环境

### 前置要求

- Docker 24+
- Docker Compose 2.20+
- Node.js 20+ (前端开发)
- Python 3.11+ (后端开发，或用 Docker)
- 火山引擎方舟 API Key（或 Anthropic API Key）

### 1. 启动基础设施

```bash
cd infra
docker compose up -d postgres redis
```

验证：
```bash
docker compose ps
# wda-postgres  healthy  0.0.0.0:5433->5432/tcp
# wda-redis     healthy  0.0.0.0:6380->6379/tcp
```

### 2. 配置后端环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env：
#   VOLC_API_KEY=your-key
#   JWT_SECRET=$(openssl rand -hex 32)
```

### 3. 安装依赖 + 跑迁移

```bash
cd backend
uv sync
uv run alembic upgrade head
```

### 4. 启动后端服务（两个终端）

终端 1 - FastAPI：
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8001
```

终端 2 - Celery worker：
```bash
cd backend
uv run celery -A app.worker.celery_app worker --loglevel=info --pool=solo
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

## 生产部署（Docker Compose）

### 完整栈

生产用 `infra/docker-compose.prod.yml`（待补）：

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: wda
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    env_file: ./backend/.env
    depends_on: [postgres, redis]
    restart: unless-stopped

  worker:
    build: ./backend
    command: celery -A app.worker.celery_app worker --loglevel=info --pool=solo
    env_file: ./backend/.env
    depends_on: [postgres, redis]
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on: [backend]
    restart: unless-stopped

volumes:
  pgdata:
```

### 环境变量（生产）

```bash
DEBUG=false
JWT_SECRET=$(openssl rand -hex 32)  # 必须改！
CORS_ORIGINS=["https://your-domain.com"]
DATABASE_URL=postgresql+asyncpg://postgres:STRONG_PASS@postgres:5432/wda
REDIS_URL=redis://redis:6379/0
VOLC_API_KEY=your-production-key
```

### 启动

```bash
docker compose -f infra/docker-compose.prod.yml up -d
docker compose -f infra/docker-compose.prod.yml exec backend alembic upgrade head
```

## 端口避让

开发环境用非默认端口避免冲突：

| 服务 | 端口 | 默认 |
|------|------|------|
| Postgres | 5433 | 5432 |
| Redis | 6380 | 6379 |
| 后端 API | 8001 | 8000 |
| 前端 dev | 5173 | - |

## 数据库备份

```bash
# 备份
docker exec wda-postgres pg_dump -U postgres wda > backup_$(date +%Y%m%d).sql

# 恢复
docker exec -i wda-postgres psql -U postgres wda < backup_YYYYMMDD.sql
```

建议生产环境配 cron 每日备份到 S3。

## 监控

### 日志

后端用 structlog 输出 JSON 格式日志：
```bash
docker compose logs -f backend worker
```

### 健康检查

```bash
curl http://localhost:8001/health
# {"status":"ok","version":"0.1.0","app":"Workflow Discovery Agent"}
```

### Celery worker 状态

```bash
cd backend
uv run celery -A app.worker.celery_app inspect active
uv run celery -A app.worker.celery_app inspect stats
```

## 故障排查

### asyncpg 'Future attached to a different loop'

测试 fixture 必须用 function-scoped，不能跨 event loop 复用 engine。见 `tests/conftest.py`。

### Celery worker 拿到旧任务

Redis queue 里有遗留任务，清理：
```bash
docker exec wda-redis redis-cli FLUSHDB
```

### 端口被占

```bash
# Windows
netstat -ano | grep ":8001 "
# 换端口或杀进程
```

### Playwright 抓取失败

```bash
cd backend
uv run playwright install chromium
```
