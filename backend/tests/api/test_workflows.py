"""Workflow API 测试.

覆盖:
- POST /workflows 创建 + 入队 Celery task (mock delay 不实际跑 agent)
- GET /workflows 分页 + 过滤
- GET /workflows/{id} 详情
- DELETE /workflows/{id} 删除
- 跨用户访问 → 404
- /workflows/{id}/runs + /evidence + /runs/{id}/tool_calls 子资源
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_celery_task():
    """Mock run_agent_task.delay, 避免 API 测试时真的入队 + 跑 agent."""
    fake_task = MagicMock()
    fake_task.id = "fake-task-id-123"

    with patch("app.api.v1.workflows.run_agent_task") as mock_task:
        mock_task.delay = MagicMock(return_value=fake_task)
        yield mock_task


@pytest.mark.asyncio
async def test_create_workflow_returns_id_and_task(auth_client, mock_celery_task):
    """POST /workflows → 201, 返回 workflow_id + task_id."""
    r = await auth_client.post(
        "/api/v1/workflows",
        json={"query": "招聘筛选流程", "notes": "test"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["workflow_id"] > 0
    assert data["status"] == "pending"
    assert data["task_id"] == "fake-task-id-123"
    mock_celery_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_create_workflow_empty_query_422(auth_client, mock_celery_task):
    r = await auth_client.post(
        "/api/v1/workflows",
        json={"query": "", "notes": None},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_workflows(auth_client, mock_celery_task):
    """分页 + total 计数."""
    for i in range(3):
        await auth_client.post(
            "/api/v1/workflows",
            json={"query": f"q{i}", "notes": None},
        )
    r = await auth_client.get("/api/v1/workflows")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_workflows_status_filter(auth_client, mock_celery_task):
    """按 status 过滤."""
    await auth_client.post("/api/v1/workflows", json={"query": "q1", "notes": None})
    # 手动改一个 workflow status 为 completed
    # (mock_celery_task.delay 不会真跑, 所以 workflow 还是 pending)
    r = await auth_client.get("/api/v1/workflows?status=pending")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = await auth_client.get("/api/v1/workflows?status=completed")
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_workflow_detail(auth_client, mock_celery_task):
    r = await auth_client.post(
        "/api/v1/workflows",
        json={"query": "招聘", "notes": "abc"},
    )
    wf_id = r.json()["workflow_id"]

    r = await auth_client.get(f"/api/v1/workflows/{wf_id}")
    assert r.status_code == 200
    wf = r.json()
    assert wf["id"] == wf_id
    assert wf["query"] == "招聘"
    assert wf["notes"] == "abc"
    assert wf["status"] == "pending"


@pytest.mark.asyncio
async def test_get_nonexistent_workflow_404(auth_client):
    r = await auth_client.get("/api/v1/workflows/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_workflow(auth_client, mock_celery_task):
    r = await auth_client.post("/api/v1/workflows", json={"query": "to-delete", "notes": None})
    wf_id = r.json()["workflow_id"]

    r = await auth_client.delete(f"/api/v1/workflows/{wf_id}")
    assert r.status_code == 204

    r = await auth_client.get(f"/api/v1/workflows/{wf_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_access_404(auth_client, second_auth_client, mock_celery_task):
    """用户 A 创建的 workflow, 用户 B 访问 → 404 (不暴露 existence)."""
    r = await auth_client.post("/api/v1/workflows", json={"query": "private", "notes": None})
    wf_id = r.json()["workflow_id"]

    # B 访问 A 的 workflow
    r = await second_auth_client.get(f"/api/v1/workflows/{wf_id}")
    assert r.status_code == 404
    # B 也不能删
    r = await second_auth_client.delete(f"/api/v1/workflows/{wf_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_workflow_runs_empty(auth_client, mock_celery_task):
    """没跑过 agent, runs 应为空 list."""
    r = await auth_client.post("/api/v1/workflows", json={"query": "x", "notes": None})
    wf_id = r.json()["workflow_id"]

    r = await auth_client.get(f"/api/v1/workflows/{wf_id}/runs")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_workflow_evidence_empty(auth_client, mock_celery_task):
    r = await auth_client.post("/api/v1/workflows", json={"query": "x", "notes": None})
    wf_id = r.json()["workflow_id"]

    r = await auth_client.get(f"/api/v1/workflows/{wf_id}/evidence")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_workflow_with_agent_run(auth_client, mock_celery_task, db_session):
    """直接在 DB 插入 agent_run + tool_call, 验证 API 能查到."""
    from app.models import Workflow, AgentRun, ToolCall

    # 创建 workflow
    r = await auth_client.post("/api/v1/workflows", json={"query": "wf-with-run", "notes": None})
    wf_id = r.json()["workflow_id"]

    # 直接 DB 插 agent_run + tool_call (mock_celery_task 不会跑 agent, 所以手动建)
    ar = AgentRun(
        workflow_id=wf_id,
        status="completed",
        current_iteration=2,
        messages=[{"role": "user", "content": "wf-with-run"}],
        final_output={"steps": ["a", "b"]},
    )
    db_session.add(ar)
    await db_session.commit()
    await db_session.refresh(ar)

    tc = ToolCall(
        agent_run_id=ar.id,
        tool_name="search_web",
        tool_call_id="tuid_test",
        iteration=0,
        input_args={"query": "wf-with-run"},
        output_result={"results": []},
        input_tokens=100,
        output_tokens=50,
        duration_ms=500,
    )
    db_session.add(tc)
    await db_session.commit()

    # API 查 runs
    r = await auth_client.get(f"/api/v1/workflows/{wf_id}/runs")
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["final_output"] == {"steps": ["a", "b"]}

    # API 查 tool_calls
    run_id = runs[0]["id"]
    r = await auth_client.get(f"/api/v1/workflows/{wf_id}/runs/{run_id}/tool_calls")
    assert r.status_code == 200
    tcs = r.json()
    assert len(tcs) == 1
    assert tcs[0]["tool_name"] == "search_web"
    assert tcs[0]["input_tokens"] == 100


@pytest.mark.asyncio
async def test_tool_calls_wrong_run_404(auth_client, mock_celery_task, db_session):
    """run_id 不属于这个 workflow → 404."""
    from app.models import Workflow, AgentRun

    # 创建两个 workflow, 各插一个 agent_run
    r = await auth_client.post("/api/v1/workflows", json={"query": "wf1", "notes": None})
    wf1_id = r.json()["workflow_id"]
    r = await auth_client.post("/api/v1/workflows", json={"query": "wf2", "notes": None})
    wf2_id = r.json()["workflow_id"]

    ar1 = AgentRun(workflow_id=wf1_id, status="completed", current_iteration=1, messages=[])
    ar2 = AgentRun(workflow_id=wf2_id, status="completed", current_iteration=1, messages=[])
    db_session.add_all([ar1, ar2])
    await db_session.commit()
    await db_session.refresh(ar1)
    await db_session.refresh(ar2)

    # 用 wf1 + ar2 的 id 查 → 应该 404 (ar2 不属于 wf1)
    r = await auth_client.get(f"/api/v1/workflows/{wf1_id}/runs/{ar2.id}/tool_calls")
    assert r.status_code == 404
