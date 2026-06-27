"""Celery task for OPC project generation."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.project_orchestrator import ProjectOrchestrator
from app.config import settings
from app.core.logging import get_logger
from app.models import Artifact, Project
from app.worker.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(
    name="opc.generate_project_task",
    bind=True,
    max_retries=1,
    acks_late=True,
)
def generate_project_task(
    self,
    project_id: int,
    user_idea: str,
    workflow_plan: str = "",
) -> dict[str, Any]:
    """异步生成 OPC 项目.

    Returns:
        {project_id, status, error?}
    """
    setup_logging()
    log.info("generate_project_task_start", task_id=self.request.id, project_id=project_id)
    try:
        result = asyncio.run(_generate_project_async(project_id, user_idea, workflow_plan))
        log.info("generate_project_task_done", task_id=self.request.id, project_id=project_id, status=result["status"])
        return result
    except Exception as e:
        log.error("generate_project_task_failed", task_id=self.request.id, project_id=project_id, error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)
        asyncio.run(_mark_project_failed(project_id, str(e)))
        raise


async def _generate_project_async(
    project_id: int,
    user_idea: str,
    workflow_plan: str,
) -> dict[str, Any]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=2)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            project = await session.get(Project, project_id)
            if project is None:
                raise ValueError(f"project {project_id} not found")
            project.status = "planning"
            await session.commit()

        orchestrator = ProjectOrchestrator(
            project_id=project_id,
            user_idea=user_idea,
            workflow_plan=workflow_plan,
        )
        await orchestrator.run()

        async with factory() as session:
            await orchestrator.persist(session)
            project = await session.get(Project, project_id)
            status = project.status if project else "unknown"
            error = project.error if project else None

        return {
            "project_id": project_id,
            "status": status,
            "error": error,
        }
    finally:
        await engine.dispose()


async def _mark_project_failed(project_id: int, error: str) -> None:
    engine = create_async_engine(settings.database_url, pool_size=1)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            project = await session.get(Project, project_id)
            if project is not None:
                project.status = "failed"
                project.error = f"celery task failed after retries: {error}"
                project.completed_at = datetime.utcnow()
                await session.commit()
    finally:
        await engine.dispose()


def setup_logging() -> None:
    from app.core.logging import setup_logging as _setup
    _setup()
