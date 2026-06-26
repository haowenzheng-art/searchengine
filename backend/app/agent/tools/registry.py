"""Tool registry - 注册所有 tool，按名字查找.

Orchestrator 用 registry 把 Anthropic SDK 的 tool_use 块映射到实际执行.
"""
from __future__ import annotations

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.agent.tools.analysis import (
    CalculateROI,
    DesignAgentFlow,
    ExtractWorkflow,
    IdentifyPainPoints,
)
from app.agent.tools.fetch_page import FetchPageTool
from app.agent.tools.save_report import SaveReportTool
from app.agent.tools.score_evidence import ScoreEvidenceTool
from app.agent.tools.search_web import SearchWebTool


class ToolRegistry:
    """Tool 注册表 - 单例."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for tool_cls in [
            SearchWebTool,
            ScoreEvidenceTool,
            FetchPageTool,
            ExtractWorkflow,
            IdentifyPainPoints,
            DesignAgentFlow,
            CalculateROI,
            SaveReportTool,
        ]:
            self.register(tool_cls())

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def to_anthropic(self) -> list[dict]:
        """转成 Anthropic SDK tools 参数."""
        return [tool.to_anthropic() for tool in self._tools.values()]


_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
