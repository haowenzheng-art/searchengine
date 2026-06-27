"""Celery tasks - 异步执行 Agent 工作流.

入口: run_agent_task(workflow_id)
流程:
1. 加载 workflow, 校验存在
2. 更新 workflow.status = running
3. 调 orchestrator 跑 agent loop
4. 汇总 tool_calls, 写 usage_records
5. 更新 workflow.status = completed/failed

设计要点:
- 每个 task 用独立 SQLAlchemy engine + event loop.
  全局 engine 跨 event loop 复用会触发 asyncpg 'Future attached to a different loop'.
- 不静默 fallback: orchestrator 异常直接标 failed + 写 error.
- 重试: 默认 1 次 (再失败说明有 bug, 不浪费资源).
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.orchestrator import Orchestrator
from app.config import settings
from app.core.logging import get_logger, setup_logging
from app.models import ToolCall, Workflow
from app.usage.service import record_workflow_completion
from app.worker.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(
    name="wda.run_agent_task",
    bind=True,
    max_retries=1,
    acks_late=True,
)
def run_agent_task(self, workflow_id: int) -> dict[str, Any]:
    """Celery task 入口 (sync, 内部 asyncio.run 跑 async orchestrator).

    Returns:
        {workflow_id, status, agent_run_id, error?}
    """
    setup_logging()
    log.info("celery_task_start", task_id=self.request.id, workflow_id=workflow_id)
    try:
        result = asyncio.run(_run_agent_async(workflow_id))
        log.info("celery_task_done", task_id=self.request.id, workflow_id=workflow_id, status=result["status"])
        return result
    except Exception as e:
        # 重试一次, 还失败就标 workflow failed
        log.error("celery_task_failed", task_id=self.request.id, workflow_id=workflow_id, error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)
        # 重试用完了, 把 workflow 标 failed
        asyncio.run(_mark_workflow_failed(workflow_id, str(e)))
        raise


async def _run_agent_async(workflow_id: int) -> dict[str, Any]:
    """跑 agent 的 async 实现 - 独立 engine + session factory."""
    # 独立 engine, 避免跨 event loop 复用 asyncpg
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=2)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            wf = await session.get(Workflow, workflow_id)
            if wf is None:
                raise ValueError(f"workflow {workflow_id} not found")
            wf.status = "running"
            await session.commit()

            query = wf.query
            user_id = wf.user_id

        # orchestrator 用自己的 session factory (内部多次 session)
        orch = Orchestrator(factory)
        agent_run = await orch.run(query=query, workflow_id=workflow_id)

        # 汇总 tool_calls + 写 usage + 更新 workflow
        async with factory() as session:
            wf = await session.get(Workflow, workflow_id)
            if wf is not None:
                wf.status = agent_run.status
                if agent_run.status in ("completed", "failed"):
                    wf.completed_at = datetime.utcnow()
                    if agent_run.error:
                        wf.error = agent_run.error
                await session.commit()

            # 取 tool_calls 用于 usage
            tcs = (
                await session.execute(
                    select(ToolCall).where(ToolCall.agent_run_id == agent_run.id).order_by(ToolCall.id)
                )
            ).scalars().all()

            # 写 usage_records (即使失败也记录用了多少 token)
            if wf is not None:
                await record_workflow_completion(session, user_id, agent_run, list(tcs))

        return {
            "workflow_id": workflow_id,
            "status": agent_run.status,
            "agent_run_id": agent_run.id,
            "iterations": agent_run.current_iteration,
            "error": agent_run.error,
        }
    finally:
        await engine.dispose()


async def _mark_workflow_failed(workflow_id: int, error: str) -> None:
    """Celery 重试用完, 把 workflow 标 failed (避免一直显示 running)."""
    engine = create_async_engine(settings.database_url, pool_size=1)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            wf = await session.get(Workflow, workflow_id)
            if wf is not None:
                wf.status = "failed"
                wf.error = f"celery task failed after retries: {error}"
                wf.completed_at = datetime.utcnow()
                await session.commit()
    finally:
        await engine.dispose()


# Import OPC tasks so Celery autodiscover picks them up
from app.worker.opc_tasks import generate_project_task  # noqa: E402
