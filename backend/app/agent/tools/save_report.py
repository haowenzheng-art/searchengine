"""save_report tool - LLM 决定结束分析时调用，编译最终报告.

设计：tool 本身只做结构化和校验，不直接写 DB.
DB 持久化由 orchestrator 在 tool_use 返回后处理.
这样 tool 是纯函数，可独立测试.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import Field

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger

log = get_logger(__name__)


class SaveReportInput(ToolInput):
    query: str
    workflow_json: Any
    pain_points_json: Any
    agent_flow_json: Any
    roi_json: Any
    summary: str = Field(description="200字以内的整体结论")


class SaveReportOutput(ToolOutput):
    query: str
    workflow: dict
    pain_points: list
    agent_flow: dict
    roi: dict
    summary: str


class SaveReportTool(Tool):
    name = "save_report"
    description = (
        "编译最终报告并保存. "
        "在所有分析完成后调用此 tool 结束 agent 循环. "
        "传入工作流、痛点、AI 方案、ROI 的 JSON 字符串或对象和总结."
    )
    input_schema = SaveReportInput
    output_schema = SaveReportOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, SaveReportInput)
        log.info("save_report_called", query=input.query, summary_len=len(input.summary))
        # Phase 1: 只做结构化校验，DB 持久化由 orchestrator 处理

        try:
            workflow = json.loads(input.workflow_json) if isinstance(input.workflow_json, str) else input.workflow_json
            pain_points = json.loads(input.pain_points_json) if isinstance(input.pain_points_json, str) else input.pain_points_json
            agent_flow = json.loads(input.agent_flow_json) if isinstance(input.agent_flow_json, str) else input.agent_flow_json
            roi = json.loads(input.roi_json) if isinstance(input.roi_json, str) else input.roi_json
        except json.JSONDecodeError as e:
            log.error("save_report_invalid_json", error=str(e))
            raise ValueError(f"Invalid JSON in report: {e}") from e

        return SaveReportOutput(
            query=input.query,
            workflow=workflow,
            pain_points=pain_points,
            agent_flow=agent_flow,
            roi=roi,
            summary=input.summary,
        )
