.PHONY: help dev dev-backend dev-frontend docker-up docker-down docker-logs migrate makemigrations test test-backend test-frontend lint format clean install

PYTHON := uv run --directory backend
NPM := npm --prefix frontend
COMPOSE := docker compose -f infra/docker-compose.yml

help: ## 显示所有命令
	@echo "Workflow Discovery Agent - 开发命令"
	@echo ""
	@echo "  make install          安装所有依赖（uv sync + npm install）"
	@echo "  make docker-up        启动 postgres + redis 容器"
	@echo "  make docker-down      停止容器"
	@echo "  make docker-logs      查看容器日志"
	@echo ""
	@echo "  make dev-backend      启动 FastAPI (port 8000)"
	@echo "  make dev-frontend     启动 Vite (port 5173)"
	@echo "  make dev              启动 docker + 提示如何启动 api/web"
	@echo ""
	@echo "  make migrate          跑 alembic 迁移"
	@echo "  make makemigrations   生成新迁移 (MSG=description)"
	@echo ""
	@echo "  make test             跑所有测试"
	@echo "  make test-backend     跑 backend 测试"
	@echo "  make test-frontend    跑 frontend build 测试"
	@echo "  make lint             lint (ruff + tsc)"
	@echo "  make format           格式化 (ruff format)"
	@echo "  make clean            清理缓存"

install: ## 安装所有依赖
	uv sync --directory backend
	npm install --prefix frontend

dev: docker-up ## 启动基础设施 + 提示
	@echo ""
	@echo "============================================"
	@echo "  Postgres + Redis 已启动"
	@echo "============================================"
	@echo ""
	@echo "在两个终端分别运行："
	@echo "  make dev-backend    (FastAPI on http://localhost:8000)"
	@echo "  make dev-frontend   (Vite on http://localhost:5173)"
	@echo ""

dev-backend: ## 启动 FastAPI dev server
	$(PYTHON) uvicorn app.main:app --reload --port 8000 --host 127.0.0.1

dev-frontend: ## 启动 Vite dev server
	$(NPM) run dev

docker-up: ## 启动 postgres + redis
	$(COMPOSE) up -d
	@echo "等待服务健康..."
	sleep 5
	$(COMPOSE) ps

docker-down: ## 停止容器
	$(COMPOSE) down

docker-logs: ## 查看容器日志
	$(COMPOSE) logs -f

migrate: ## 跑 alembic 迁移
	$(PYTHON) alembic upgrade head

makemigrations: ## 生成新迁移，用法：make makemigrations MSG=add_users
	@test -n "$(MSG)" || (echo "Usage: make makemigrations MSG=add_users" && exit 1)
	$(PYTHON) alembic revision --autogenerate -m "$(MSG)"

test: test-backend test-frontend ## 跑所有测试

test-backend: ## 跑 backend pytest
	$(PYTHON) pytest

test-frontend: ## 跑 frontend build
	$(NPM) run build

lint: ## lint
	$(PYTHON) ruff check .
	$(NPM) run build

format: ## 格式化 backend
	$(PYTHON) ruff format .

clean: ## 清理缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
	rm -rf frontend/dist
	@echo "cleaned"
