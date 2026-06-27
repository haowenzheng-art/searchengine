"""Ops Agent - 生成部署配置和说明."""
from __future__ import annotations

from typing import Any

from app.agent.projects.base_agent import AgentAction, AgentState, ProjectAgent
from app.core.logging import get_logger

log = get_logger(__name__)


class OpsAgent(ProjectAgent):
    role = "ops"

    def __init__(self, project_id: int, context: dict[str, Any]):
        super().__init__(project_id, context)
        self.files = context.get("files", {})
        self.deploy_url = ""

    async def perceive(self) -> AgentState:
        return AgentState(
            project_id=self.project_id,
            role=self.role,
            data={"files": list(self.files.keys())},
        )

    async def reason(self, state: AgentState) -> AgentAction:
        if "DEPLOYMENT.md" not in self.files:
            return AgentAction(type="GENERATE_OPS", payload=state.data)
        return AgentAction(type="WAIT")

    async def act(self, action: AgentAction) -> None:
        if action.type == "GENERATE_OPS":
            log.info("ops_generating", project_id=self.project_id)
            self.files["docker-compose.yml"] = self._docker_compose()
            self.files["DEPLOYMENT.md"] = self._deployment_md()
            self.deploy_url = f"http://localhost:{self.project_id % 10000 + 30000}"

            self.record_action("GENERATE_OPS")
            await self.save_memory(
                observation="生成部署配置",
                insight="docker-compose 是最小可运行的部署方式",
                importance=6,
            )
            self.mark_done()

    def _docker_compose(self) -> str:
        return """version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - \"${BACKEND_PORT:-3001}:3001\"
    environment:
      - PORT=3001
      - DATABASE_URL=file:./dev.db
    volumes:
      - ./backend:/app
      - /app/node_modules

  frontend:
    build: ./frontend
    ports:
      - \"${FRONTEND_PORT:-3000}:3000\"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:3001
    depends_on:
      - backend
"""

    def _deployment_md(self) -> str:
        return """# 部署说明

## 本地开发

```bash
cd backend
npm install
npm run dev

cd ../frontend
npm install
npm run dev
```

## Docker Compose

```bash
docker compose up --build
```

访问:
- 前端: http://localhost:3000
- 后端 API: http://localhost:3001/api/v1
"""

    def get_files(self) -> dict[str, str]:
        return self.files

    def get_deploy_url(self) -> str:
        return self.deploy_url
