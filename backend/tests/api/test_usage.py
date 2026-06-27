"""Usage API 测试."""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_celery_task():
    """Mock run_agent_task.delay (跟 test_workflows 一样)."""
    fake_task = MagicMock()
    fake_task.id = "fake-task-id"
    with patch("app.api.v1.workflows.run_agent_task") as mock_task:
        mock_task.delay = MagicMock(return_value=fake_task)
        yield mock_task


@pytest.mark.asyncio
async def test_usage_today_empty(auth_client):
    """没创建过 workflow, 今日用量全 0."""
    r = await auth_client.get("/api/v1/usage/today")
    assert r.status_code == 200
    data = r.json()
    assert data["workflows_started"] == 0
    assert data["tool_calls"] == 0


@pytest.mark.asyncio
async def test_usage_today_after_workflow(auth_client, mock_celery_task):
    """创建 workflow 后, workflows_started=1."""
    await auth_client.post("/api/v1/workflows", json={"query": "x", "notes": None})
    r = await auth_client.get("/api/v1/usage/today")
    assert r.status_code == 200
    data = r.json()
    assert data["workflows_started"] == 1
    # workflows_completed 还是 0, 因为 mock 没跑 agent
    assert data["workflows_completed"] == 0


@pytest.mark.asyncio
async def test_usage_month_includes_today(auth_client, mock_celery_task):
    """本月用量包含今日."""
    await auth_client.post("/api/v1/workflows", json={"query": "x", "notes": None})
    r = await auth_client.get("/api/v1/usage/month")
    assert r.status_code == 200
    data = r.json()
    assert data["workflows_started"] == 1


@pytest.mark.asyncio
async def test_usage_today_with_completed_workflow(auth_client, db_session, test_user):
    """直接写一条 completed workflow + usage_record, 验证 API 能查."""
    from app.models import Workflow, AgentRun
    from app.usage.service import increment_workflow_started, record_workflow_completion

    # 建 workflow + agent_run + tool_call
    wf = Workflow(user_id=test_user.id, query="completed-test", status="completed")
    db_session.add(wf)
    await db_session.commit()
    await db_session.refresh(wf)
    ar = AgentRun(
        workflow_id=wf.id, status="completed", current_iteration=1, messages=[]
    )
    db_session.add(ar)
    await db_session.commit()
    await db_session.refresh(ar)

    # 写 usage
    await increment_workflow_started(db_session, test_user.id)
    from app.models import ToolCall
    tc = ToolCall(
        agent_run_id=ar.id, tool_name="search_web", tool_call_id="x",
        iteration=0, input_args={}, input_tokens=200, output_tokens=100, duration_ms=10,
    )
    db_session.add(tc)
    await db_session.commit()
    await record_workflow_completion(db_session, test_user.id, ar, [tc])

    r = await auth_client.get("/api/v1/usage/today")
    assert r.status_code == 200
    data = r.json()
    assert data["workflows_started"] == 1
    assert data["workflows_completed"] == 1
    assert data["tool_calls"] == 1
    assert data["input_tokens"] == 200
    assert data["output_tokens"] == 100
    assert data["search_queries"] == 1
