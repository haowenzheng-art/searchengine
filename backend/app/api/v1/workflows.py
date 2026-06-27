"""Workflow API - 创建/查询/删除工作流.

POST   /api/v1/workflows              创建 + 入队 Celery 任务 → {workflow_id, status}
GET    /api/v1/workflows              列出当前用户的 workflows (分页)
GET    /api/v1/workflows/{id}         单个 workflow 详情
DELETE /api/v1/workflows/{id}         删除 (级联删 agent_runs/evidence/tool_calls)
GET    /api/v1/workflows/{id}/runs     workflow 的 agent 执行记录
GET    /api/v1/workflows/{id}/evidence workflow 的证据链
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db.session import get_db
from app.models import AgentRun, Evidence, ToolCall, Workflow
from app.usage.service import increment_workflow_started
from app.worker.tasks import run_agent_task

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


# ============ Schemas ============

class WorkflowCreateRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(None, max_length=4096)


class WorkflowResponse(BaseModel):
    id: int
    user_id: int
    query: str
    notes: str | None
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int
    page: int
    page_size: int


class WorkflowCreateResponse(BaseModel):
    workflow_id: int
    status: str
    task_id: str | None


class AgentRunSummary(BaseModel):
    id: int
    status: str
    current_iteration: int
    started_at: datetime
    ended_at: datetime | None
    error: str | None
    final_output: dict[str, Any] | None


class EvidenceResponse(BaseModel):
    id: int
    url: str
    title: str | None
    snippet: str | None
    score: float
    score_reason: str | None
    is_homepage: bool
    is_disambiguation: bool
    score_layer: int
    word_count: int
    fetched_at: datetime | None


class ToolCallResponse(BaseModel):
    id: int
    tool_name: str
    iteration: int
    input_args: dict[str, Any]
    output_result: dict[str, Any] | None
    error: str | None
    input_tokens: int
    output_tokens: int
    duration_ms: int
    created_at: datetime


# ============ Helpers ============

def _wf_to_response(wf: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=wf.id,
        user_id=wf.user_id,
        query=wf.query,
        notes=wf.notes,
        status=wf.status,
        error=wf.error,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        completed_at=wf.completed_at,
    )


async def _get_owned_workflow(
    workflow_id: int, user: CurrentUser, db: AsyncSession
) -> Workflow:
    """加载 workflow + 验证 owner. 跨用户访问 → 404 (不暴露 existence)."""
    wf = await db.get(Workflow, workflow_id)
    if wf is None or wf.user_id != user.id:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


# ============ Endpoints ============

@router.post("", response_model=WorkflowCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """创建 workflow 并入队 Celery agent task.

    立即返回 workflow_id, agent 异步跑. 客户端轮询 GET /workflows/{id} 看状态.
    """
    wf = Workflow(
        user_id=user.id,
        query=request.query,
        notes=request.notes,
        status="pending",
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)

    # 写 usage (workflow_started)
    await increment_workflow_started(db, user.id)

    # 入队 Celery task
    task = run_agent_task.delay(wf.id)

    return WorkflowCreateResponse(
        workflow_id=wf.id,
        status=wf.status,
        task_id=task.id,
    )


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
):
    """列出当前用户的 workflows (分页, 按 created_at desc)."""
    base = select(Workflow).where(Workflow.user_id == user.id)
    if status_filter:
        base = base.where(Workflow.status == status_filter)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        base.order_by(desc(Workflow.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return WorkflowListResponse(
        items=[_wf_to_response(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    wf = await _get_owned_workflow(workflow_id, user, db)
    return _wf_to_response(wf)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    wf = await _get_owned_workflow(workflow_id, user, db)
    await db.delete(wf)
    await db.commit()


@router.get("/{workflow_id}/runs", response_model=list[AgentRunSummary])
async def list_workflow_runs(
    workflow_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """列出 workflow 的 agent 执行记录. 一个 workflow 可能重跑多次."""
    await _get_owned_workflow(workflow_id, user, db)
    stmt = (
        select(AgentRun)
        .where(AgentRun.workflow_id == workflow_id)
        .order_by(desc(AgentRun.started_at))
    )
    runs = (await db.execute(stmt)).scalars().all()
    return [
        AgentRunSummary(
            id=r.id,
            status=r.status,
            current_iteration=r.current_iteration,
            started_at=r.started_at,
            ended_at=r.ended_at,
            error=r.error,
            final_output=r.final_output,
        )
        for r in runs
    ]


@router.get("/{workflow_id}/evidence", response_model=list[EvidenceResponse])
async def list_workflow_evidence(
    workflow_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """列出 workflow 的证据链 (按 score 降序)."""
    await _get_owned_workflow(workflow_id, user, db)
    stmt = (
        select(Evidence)
        .where(Evidence.workflow_id == workflow_id)
        .order_by(desc(Evidence.score))
    )
    items = (await db.execute(stmt)).scalars().all()
    return [
        EvidenceResponse(
            id=e.id,
            url=e.url,
            title=e.title,
            snippet=e.snippet,
            score=e.score,
            score_reason=e.score_reason,
            is_homepage=e.is_homepage,
            is_disambiguation=e.is_disambiguation,
            score_layer=e.score_layer,
            word_count=e.word_count,
            fetched_at=e.fetched_at,
        )
        for e in items
    ]


@router.get("/{workflow_id}/runs/{run_id}/tool_calls", response_model=list[ToolCallResponse])
async def list_run_tool_calls(
    workflow_id: int,
    run_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """列出某次 agent run 的 tool 调用序列 (调试 + 可视化用)."""
    await _get_owned_workflow(workflow_id, user, db)
    # 校验 run 属于这个 workflow
    run = await db.get(AgentRun, run_id)
    if run is None or run.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="agent run not found")
    stmt = (
        select(ToolCall)
        .where(ToolCall.agent_run_id == run_id)
        .order_by(ToolCall.id)
    )
    items = (await db.execute(stmt)).scalars().all()
    return [
        ToolCallResponse(
            id=tc.id,
            tool_name=tc.tool_name,
            iteration=tc.iteration,
            input_args=tc.input_args,
            output_result=tc.output_result,
            error=tc.error,
            input_tokens=tc.input_tokens,
            output_tokens=tc.output_tokens,
            duration_ms=tc.duration_ms,
            created_at=tc.created_at,
        )
        for tc in items
    ]
