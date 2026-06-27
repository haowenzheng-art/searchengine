"""OPC Project Orchestrator - 协调 6 个 Agent 完成项目生成.

状态机: idle -> planning -> developing -> testing -> deploying -> learning -> done
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.projects.backend_agent import BackendAgent
from app.agent.projects.ceo_agent import CeoAgent
from app.agent.projects.frontend_agent import FrontendAgent
from app.agent.projects.ops_agent import OpsAgent
from app.agent.projects.pm_agent import PMAgent
from app.agent.projects.test_agent import TestAgent
from app.core.logging import get_logger
from app.models import Artifact, Project
from app.services.storage import StorageBackend, get_storage_backend

log = get_logger(__name__)


class ProjectStateMachine:
    states = ["idle", "planning", "developing", "testing", "deploying", "learning", "done", "failed"]

    def __init__(self, user_idea: str):
        self.current_state = "idle"
        self.context: dict[str, Any] = {
            "user_idea": user_idea,
            "prd": None,
            "frontend_ready": False,
            "backend_ready": False,
            "tests_passed": False,
            "deploy_url": None,
            "errors": [],
        }

    def send(self, event: str, payload: Any = None) -> None:
        old = self.current_state
        if self.current_state == "idle" and event == "START":
            self.current_state = "planning"
        elif self.current_state == "planning" and event == "PRD_DONE":
            self.context["prd"] = payload
            self.current_state = "developing"
        elif self.current_state == "developing":
            if event == "BACKEND_DONE":
                self.context["backend_ready"] = True
            elif event == "FRONTEND_DONE":
                self.context["frontend_ready"] = True
            if self.context["backend_ready"] and self.context["frontend_ready"]:
                self.current_state = "testing"
        elif self.current_state == "testing":
            if event == "TESTS_PASS":
                self.context["tests_passed"] = True
                self.current_state = "deploying"
            elif event == "TESTS_FAIL":
                self.current_state = "developing"
        elif self.current_state == "deploying" and event == "DEPLOYED":
            self.context["deploy_url"] = payload
            self.current_state = "learning"
        elif self.current_state == "learning" and event == "LEARNING_DONE":
            self.current_state = "done"
        elif event == "ERROR":
            self.context["errors"].append(payload)
            self.current_state = "failed"
        log.info("state_transition", old_state=old, new_state=self.current_state, transition_event=event)

    def get_state(self) -> str:
        return self.current_state


class ProjectOrchestrator:
    """OPC 项目编排器."""

    def __init__(
        self,
        project_id: int,
        user_idea: str,
        workflow_plan: str = "",
        storage: StorageBackend | None = None,
    ):
        self.project_id = project_id
        self.user_idea = user_idea
        self.workflow_plan = workflow_plan
        self.storage = storage or get_storage_backend()
        self.state_machine = ProjectStateMachine(user_idea)
        self.files: dict[str, str] = {}
        self.credits_used = 0

    async def run(self) -> None:
        log.info("project_orchestrator_start", project_id=self.project_id)
        self.state_machine.send("START")

        try:
            # 1. CEO 制定策略
            ceo = CeoAgent(self.project_id, {
                "user_idea": self.user_idea,
                "workflow_plan": self.workflow_plan,
            })
            await ceo.run()

            # 2. PM 写 PRD
            pm = PMAgent(self.project_id, {
                "user_idea": self.user_idea,
                "workflow_plan": self.workflow_plan,
            })
            await pm.run()
            prd = pm.get_prd()
            self.state_machine.send("PRD_DONE", prd)

            # 3. Backend 生成 API 和模型
            backend = BackendAgent(self.project_id, {"prd": prd})
            await backend.run()
            backend_files = backend.get_files()
            api_spec = backend.get_api_spec()
            self.files.update(backend_files)
            self.state_machine.send("BACKEND_DONE")

            # 4. Frontend 生成页面
            frontend = FrontendAgent(self.project_id, {"prd": prd, "api_spec": api_spec})
            await frontend.run()
            frontend_files = frontend.get_files()
            self.files.update(frontend_files)
            self.state_machine.send("FRONTEND_DONE")

            # 5. Test 检查
            test = TestAgent(self.project_id, {"files": self.files})
            await test.run()
            self.files = test.get_files()
            if test.is_passed():
                self.state_machine.send("TESTS_PASS")
            else:
                self.state_machine.send("TESTS_FAIL")
                raise RuntimeError("Tests failed")

            # 6. Ops 生成部署配置
            ops = OpsAgent(self.project_id, {"files": self.files})
            await ops.run()
            self.files = ops.get_files()
            deploy_url = ops.get_deploy_url()
            self.state_machine.send("DEPLOYED", deploy_url)

            # 7. Learning / 完成
            self.state_machine.send("LEARNING_DONE")

        except Exception as e:
            log.error("project_orchestrator_error", project_id=self.project_id, error=str(e))
            self.state_machine.send("ERROR", str(e))
            raise

    async def persist(self, session: AsyncSession) -> Project:
        """把生成的文件持久化到存储和数据库."""
        prefix = f"projects/{self.project_id}"
        for path, content in self.files.items():
            await self.storage.write(prefix, path, content)

        # 创建 artifact 记录
        artifacts = []
        for path, content in self.files.items():
            artifact = Artifact(
                project_id=self.project_id,
                path=path,
                type=self._infer_type(path),
                content=content if len(content) < 64000 else None,
            )
            artifacts.append(artifact)
        session.add_all(artifacts)

        project = await session.get(Project, self.project_id)
        if project:
            project.status = self.state_machine.get_state()
            project.storage_prefix = prefix
            project.deploy_url = self.state_machine.context.get("deploy_url")
            project.credits_used = self.credits_used
            if project.status == "done":
                project.completed_at = datetime.utcnow()
            await session.commit()
        return project

    def _infer_type(self, path: str) -> str:
        if path.endswith((".tsx", ".ts", ".jsx", ".js")):
            return "code"
        if path.endswith((".prisma", ".sql")):
            return "config"
        if path.endswith((".md", ".txt")):
            return "doc"
        if path.startswith("test") or "test" in path.lower():
            return "test"
        if path.endswith("Dockerfile") or path.endswith(".yml") or path.endswith(".yaml"):
            return "docker"
        return "other"
