"""Test Agent - 检查生成的项目结构并生成测试."""
from __future__ import annotations

from typing import Any

from app.agent.projects.base_agent import AgentAction, AgentState, ProjectAgent
from app.core.logging import get_logger

log = get_logger(__name__)


class TestAgent(ProjectAgent):
    role = "test"

    def __init__(self, project_id: int, context: dict[str, Any]):
        super().__init__(project_id, context)
        self.files = context.get("files", {})
        self.report = ""
        self.passed = False

    async def perceive(self) -> AgentState:
        return AgentState(
            project_id=self.project_id,
            role=self.role,
            data={"files": list(self.files.keys())},
        )

    async def reason(self, state: AgentState) -> AgentAction:
        if not self.report:
            return AgentAction(type="RUN_TESTS", payload=state.data)
        return AgentAction(type="WAIT")

    async def act(self, action: AgentAction) -> None:
        if action.type == "RUN_TESTS":
            log.info("test_running", project_id=self.project_id)
            checks = []
            required_backend = ["backend/package.json", "backend/src/index.ts", "backend/src/routes.ts"]
            required_frontend = ["frontend/package.json", "frontend/src/app/page.tsx", "frontend/src/app/layout.tsx"]

            backend_ok = all(f in self.files for f in required_backend)
            frontend_ok = all(f in self.files for f in required_frontend)

            checks.append(f"后端核心文件: {'通过' if backend_ok else '失败'}")
            checks.append(f"前端核心文件: {'通过' if frontend_ok else '失败'}")

            self.passed = backend_ok and frontend_ok
            self.report = "\n".join([
                "# 测试报告",
                "",
                *checks,
                "",
                f"总体结果: {'通过' if self.passed else '失败'}",
            ])

            self.record_action("RUN_TESTS")
            await self.save_memory(
                observation=f"测试结果: {self.passed}",
                insight="结构检查是最小可接受的测试",
                importance=6,
            )
            self.files["TEST_REPORT.md"] = self.report
            self.mark_done()

    def get_report(self) -> str:
        return self.report

    def is_passed(self) -> bool:
        return self.passed

    def get_files(self) -> dict[str, str]:
        return self.files
