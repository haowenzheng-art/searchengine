"""Agent 执行上下文 - 让 tool 能安全拿到 workflow_id 等元数据.

不通过 tool schema 传 workflow_id，避免 LLM 需要知道内部 ID。
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

current_workflow_id: ContextVar[int | None] = ContextVar("current_workflow_id", default=None)


def set_workflow_id(workflow_id: int) -> Any:
    """设置当前 tool 执行所属的 workflow_id，返回 token 用于恢复."""
    return current_workflow_id.set(workflow_id)


def reset_workflow_id(token: Any) -> None:
    """恢复 workflow_id 上下文."""
    current_workflow_id.reset(token)


def get_workflow_id() -> int | None:
    """获取当前 workflow_id；未设置时返回 None."""
    return current_workflow_id.get()
