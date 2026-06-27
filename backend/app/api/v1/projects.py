"""OPC Project API - 创建、查询、下载项目."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import CurrentUser
from app.db.session import get_db
from app.models import Artifact, Project, User, Workflow
from app.services.workflow_converter import mvp_plan_to_text
from app.worker.tasks import generate_project_task

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ============ Schemas ============

class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=4096)
    user_idea: str = Field(min_length=1, max_length=4096)
    workflow_id: int | None = Field(None, description="关联的 Workflow Thief Arena workflow ID")


class ProjectResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    workflow_id: int | None
    name: str
    description: str | None
    user_idea: str | None
    status: str
    deploy_url: str | None
    credits_used: int
    created_at: str
    updated_at: str
    completed_at: str | None

    model_config = ConfigDict(from_attributes=True)


class ArtifactResponse(BaseModel):
    id: int
    path: str
    type: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


# ============ Helpers ============

def _project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        user_id=project.user_id,
        workflow_id=project.workflow_id,
        name=project.name,
        description=project.description,
        user_idea=project.user_idea,
        status=project.status,
        deploy_url=project.deploy_url,
        credits_used=project.credits_used,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


async def _ensure_user_has_org(user: User, db: AsyncSession) -> int:
    """如果用户还没有组织, 自动创建一个 free 组织."""
    if user.organization_id:
        return user.organization_id
    from app.models import Organization
    org = Organization(name=f"Org of {user.email}", plan="free")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    user.organization_id = org.id
    await db.commit()
    return org.id


# ============ Endpoints ============

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_project(
    req: ProjectCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """创建项目并异步启动生成任务."""
    org_id = await _ensure_user_has_org(user, db)

    workflow_plan = ""
    if req.workflow_id:
        wf = await db.get(Workflow, req.workflow_id)
        if wf is None or wf.user_id != user.id:
            raise HTTPException(status_code=404, detail="workflow not found")
        if wf.mvp_plan:
            workflow_plan = mvp_plan_to_text(wf.mvp_plan)
        else:
            workflow_plan = wf.query  # fallback

    project = Project(
        organization_id=org_id,
        user_id=user.id,
        workflow_id=req.workflow_id,
        name=req.name,
        description=req.description,
        user_idea=req.user_idea,
        status="idle",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # 启动 Celery 任务
    generate_project_task.delay(project.id, req.user_idea, workflow_plan)

    log.info("project_created", project_id=project.id, user_id=user.id)
    return _project_to_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
) -> list[ProjectResponse]:
    """列出当前用户组织的项目."""
    if not user.organization_id:
        return []
    result = await db.execute(
        select(Project)
        .where(Project.organization_id == user.organization_id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    projects = result.scalars().all()
    return [_project_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await db.get(Project, project_id)
    if project is None or project.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="project not found")
    return _project_to_response(project)


@router.get("/{project_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    project_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ArtifactResponse]:
    project = await db.get(Project, project_id)
    if project is None or project.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="project not found")
    result = await db.execute(
        select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.path)
    )
    artifacts = result.scalars().all()
    return [
        ArtifactResponse(
            id=a.id,
            path=a.path,
            type=a.type,
            created_at=a.created_at.isoformat(),
        )
        for a in artifacts
    ]


@router.get("/{project_id}/artifacts/{artifact_id}")
async def get_artifact_content(
    project_id: int,
    artifact_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await db.get(Project, project_id)
    if project is None or project.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="project not found")
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None or artifact.project_id != project_id:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {"path": artifact.path, "content": artifact.content or ""}
