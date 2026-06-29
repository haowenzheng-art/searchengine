"""Orchestrator unit tests - 用 mock LLM 验证 tool use 循环.

测试覆盖:
1. happy path - 多步 tool use 后 save_report 完成
2. tool 失败时返回 is_error 给 LLM
3. max_iterations 强制终止 (没调 save_report -> failed)
4. resume 从中断的 agent_run 继续
5. tool_calls 持久化到 DB
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.agent.orchestrator import Orchestrator
from app.agent.tools.registry import ToolRegistry
from app.config import settings
from app.models import AgentRun, ToolCall
from app.search.fetcher import FetchResult
from tests.conftest import MockLLMResponse, make_tool_use_block


def make_test_registry() -> ToolRegistry:
    """独立 registry - 不污染全局单例."""
    return ToolRegistry()


def _save_report_input(summary: str = "done") -> dict:
    """构造合法的 save_report input."""
    return {
        "query": "test",
        "workflow_json": json.dumps({"steps": []}),
        "pain_points_json": json.dumps([]),
        "agent_flow_json": json.dumps({}),
        "roi_json": json.dumps({}),
        "summary": summary,
    }


def _score_evidence_response(score: float = 8.0, reason: str = "真实流程文章") -> dict:
    """构造 score_evidence 内部 LLM 调用应返回的 score_evidence_response tool_use."""
    return {
        "type": "tool_use",
        "id": "toolu_score_resp",
        "name": "score_evidence_response",
        "input": {
            "score": score,
            "reason": reason,
            "is_homepage": False,
            "is_disambiguation": False,
        },
    }


@pytest.mark.asyncio
async def test_happy_path(session_factory, db_session, mock_llm, monkeypatch, workflow):
    """完整 happy path - 批量评分/抓取后 save_report 完成.

    Mock LLM 序列:
    - mock 0: orchestrator → search_web
    - mock 1: orchestrator → score_evidence_batch
    - mock 2: score_evidence_batch 内部 LLM → score_evidence_response (高分)
    - mock 3: orchestrator → fetch_page_batch
    - mock 4: orchestrator → save_report
    """
    async def fake_score_evidence(**kwargs):
        return 8.0, "真实流程文章", False, False, 2

    async def fake_fetch_page(url: str):
        return FetchResult(
            url=url,
            content="招聘筛选流程包括简历收集、简历筛选、初筛面试和专业面试。",
            word_count=32,
            fetch_time_ms=10,
            title="招聘筛选流程",
        )

    monkeypatch.setattr("app.agent.tools.score_evidence_batch._score_evidence", fake_score_evidence)
    monkeypatch.setattr("app.agent.tools.fetch_page_batch._fetch_page", fake_fetch_page)

    mock = mock_llm([
        MockLLMResponse(
            content=[make_tool_use_block("search_web", {"query": "招聘筛选流程", "num_results": 3})],
            stop_reason="tool_use",
        ),
        MockLLMResponse(
            content=[make_tool_use_block("score_evidence_batch", {
                "query": "招聘筛选流程",
                "items": [{
                    "url": "https://hr.example.com/articles/recruitment-screening-process",
                    "snippet": "招聘筛选流程6个步骤",
                    "title": "招聘筛选流程",
                }],
            })],
            stop_reason="tool_use",
        ),
        MockLLMResponse(
            content=[make_tool_use_block("fetch_page_batch", {
                "urls": ["https://hr.example.com/articles/recruitment-screening-process"],
            })],
            stop_reason="tool_use",
        ),
        MockLLMResponse(
            content=[make_tool_use_block("save_report", _save_report_input("招聘筛选流程已优化"))],
            stop_reason="tool_use",
        ),
    ])
    registry = make_test_registry()
    orch = Orchestrator(session_factory, llm=mock, registry=registry)

    agent_run = await orch.run(query="招聘筛选流程", workflow_id=workflow.id)

    assert agent_run.status == "completed"
    assert agent_run.final_output is not None
    assert agent_run.final_output["query"] == "test"
    # 4 次 LLM 调用: search → score batch → fetch batch → save_report
    assert mock.call_count == 4

    # 验证 tool_calls 持久化 (4 个 orchestrator tool_use block → 4 个 tool_call)
    result = await db_session.execute(select(ToolCall).order_by(ToolCall.id))
    tool_calls = result.scalars().all()
    assert len(tool_calls) == 4
    assert tool_calls[0].tool_name == "search_web"
    assert tool_calls[1].tool_name == "score_evidence_batch"
    assert tool_calls[2].tool_name == "fetch_page_batch"
    assert tool_calls[3].tool_name == "save_report"
    assert all(tc.error is None for tc in tool_calls)


@pytest.mark.asyncio
async def test_tool_error_persists_and_continues(session_factory, db_session, mock_llm, workflow):
    """tool 执行失败 - 错误持久化到 DB，orchestrator 把 is_error 返回给 LLM，继续."""
    mock = mock_llm([
        # 调用不存在的 tool
        MockLLMResponse(
            content=[make_tool_use_block("nonexistent_tool", {"x": 1})],
            stop_reason="tool_use",
        ),
        # 第二次 LLM 调用 save_report 结束
        MockLLMResponse(
            content=[make_tool_use_block("save_report", _save_report_input())],
            stop_reason="tool_use",
        ),
    ])
    registry = make_test_registry()
    orch = Orchestrator(session_factory, llm=mock, registry=registry)

    agent_run = await orch.run(query="test", workflow_id=workflow.id)

    assert agent_run.status == "completed"
    result = await db_session.execute(select(ToolCall).order_by(ToolCall.id))
    tool_calls = result.scalars().all()
    assert len(tool_calls) == 2
    assert tool_calls[0].tool_name == "nonexistent_tool"
    assert tool_calls[0].error is not None
    assert tool_calls[1].tool_name == "save_report"
    assert tool_calls[1].error is None


@pytest.mark.asyncio
async def test_max_iterations_force_terminates(session_factory, db_session, mock_llm, monkeypatch, workflow):
    """达到 max_iterations 时强制 tool_choice=save_report.

    但 mock 永远返回 search_web，所以最后会失败 (LLM 拒绝 save_report).
    验证：status=failed，error 含 "did not call save_report".
    """
    infinite_search = MockLLMResponse(
        content=[make_tool_use_block("search_web", {"query": "test", "num_results": 1})],
        stop_reason="tool_use",
    )
    # 给 25 次响应，但 max_iterations 设为 3
    mock = mock_llm([infinite_search] * 25)
    monkeypatch.setattr(settings, "agent_max_iterations", 3)

    registry = make_test_registry()
    orch = Orchestrator(session_factory, llm=mock, registry=registry)

    agent_run = await orch.run(query="test", workflow_id=workflow.id)

    assert agent_run.status == "failed"
    assert "did not call save_report" in (agent_run.error or "")
    # max_iterations=3，循环跑了 3 次
    assert mock.call_count == 3


@pytest.mark.asyncio
async def test_resume_from_interrupted(session_factory, db_session, mock_llm, workflow):
    """断点续跑 - 从已有 agent_run 恢复."""
    # 第一次：mock 只给 1 次响应，第二次调用会 raise (exhausted)
    mock_first = mock_llm([
        MockLLMResponse(
            content=[make_tool_use_block("search_web", {"query": "招聘"})],
            stop_reason="tool_use",
        ),
    ])
    registry = make_test_registry()
    orch1 = Orchestrator(session_factory, llm=mock_first, registry=registry)

    with pytest.raises(RuntimeError, match="MockLLMClient exhausted"):
        await orch1.run(query="招聘", workflow_id=workflow.id)

    # 验证 agent_run 创建了且状态 failed
    result = await db_session.execute(select(AgentRun).where(AgentRun.workflow_id == workflow.id))
    interrupted_run = result.scalars().first()
    assert interrupted_run is not None
    assert interrupted_run.status == "failed"
    interrupted_id = interrupted_run.id
    # messages 应该有 user query + assistant tool_use + user tool_result
    assert len(interrupted_run.messages) >= 2

    # 第二次：用新 mock 续跑
    mock_resume = mock_llm([
        MockLLMResponse(
            content=[make_tool_use_block("save_report", _save_report_input("resumed"))],
            stop_reason="tool_use",
        ),
    ])
    orch2 = Orchestrator(session_factory, llm=mock_resume, registry=registry)
    resumed = await orch2.run(query="招聘", workflow_id=workflow.id, resume_from=interrupted_id)

    assert resumed.id == interrupted_id
    assert resumed.status == "completed"
    assert resumed.final_output is not None
    assert resumed.final_output["summary"] == "resumed"
