"""4 个 LLM 分析 tools - extract_workflow / identify_pain_points / design_agent_flow / calculate_roi.

每个 tool:
1. 接收 orchestrator 传来的结构化输入
2. 内部调用 LLM (sonnet 或 opus) 用 tool_use 强制结构化输出
3. 返回 pydantic 模型给 orchestrator
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agent.llm import LLMClient
from app.agent.prompts import (
    CALCULATE_ROI_SYSTEM,
    DESIGN_AGENT_FLOW_SYSTEM,
    EXTRACT_WORKFLOW_SYSTEM,
    IDENTIFY_PAIN_POINTS_SYSTEM,
)
from app.agent.tools._llm_helper import call_llm_for_json
from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger

log = get_logger(__name__)


# ============ extract_workflow ============

class WorkflowStep(BaseModel):
    step_name: str
    description: str
    roles: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    duration_hours: float = 0.0


class ExtractWorkflowInput(ToolInput):
    corpus: str
    query: str


class ExtractWorkflowOutput(ToolOutput):
    steps: list[WorkflowStep]
    summary: str
    missing_info: list[str] = Field(default_factory=list)


class ExtractWorkflow(Tool):
    name = "extract_workflow"
    description = (
        "从抓取的 corpus 中提取结构化的企业工作流. "
        "只在累计 3 个或更多高质量 corpus 后调用. "
        "返回步骤列表、整体摘要、缺失信息."
    )
    input_schema = ExtractWorkflowInput
    output_schema = ExtractWorkflowOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, ExtractWorkflowInput)
        log.info("extract_workflow_called", corpus_len=len(input.corpus), query=input.query)
        user_content = f"Query: {input.query}\n\nCorpus:\n{input.corpus}"
        result = await call_llm_for_json(
            tier="sonnet",
            system=EXTRACT_WORKFLOW_SYSTEM,
            user_content=user_content,
            output_schema=ExtractWorkflowOutput,
            tool_name="extract_workflow_response",
            temperature=0.0,
        )
        return ExtractWorkflowOutput.model_validate(result)


# ============ identify_pain_points ============

class PainPoint(BaseModel):
    description: str
    step_name: str
    time_pct: float = Field(ge=0.0, le=100.0)
    root_cause: str


class IdentifyPainPointsInput(ToolInput):
    workflow_json: str | dict[str, Any]
    corpus: str


class IdentifyPainPointsOutput(ToolOutput):
    pain_points: list[PainPoint]


class IdentifyPainPoints(Tool):
    name = "identify_pain_points"
    description = (
        "基于工作流和 corpus 识别可被 AI 优化的痛点. "
        "在 extract_workflow 之后调用. "
        "返回痛点列表，每个痛点含描述、所在步骤、耗时占比、根因."
    )
    input_schema = IdentifyPainPointsInput
    output_schema = IdentifyPainPointsOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, IdentifyPainPointsInput)
        log.info("identify_pain_points_called", workflow_len=len(input.workflow_json) if isinstance(input.workflow_json, str) else 0)
        workflow_json = input.workflow_json if isinstance(input.workflow_json, str) else json.dumps(input.workflow_json, ensure_ascii=False)
        user_content = f"Workflow JSON:\n{workflow_json}\n\nCorpus:\n{input.corpus[:4000]}"
        result = await call_llm_for_json(
            tier="sonnet",
            system=IDENTIFY_PAIN_POINTS_SYSTEM,
            user_content=user_content,
            output_schema=IdentifyPainPointsOutput,
            tool_name="identify_pain_points_response",
            temperature=0.0,
        )
        return IdentifyPainPointsOutput.model_validate(result)


# ============ design_agent_flow ============

class InterventionPoint(BaseModel):
    step_name: str
    ai_action: str
    human_approval: bool
    expected_effect: str


class DesignAgentFlowInput(ToolInput):
    workflow_json: str | dict[str, Any]
    pain_points_json: str | list[dict[str, Any]]


class DesignAgentFlowOutput(ToolOutput):
    intervention_points: list[InterventionPoint]
    overall_strategy: str


class DesignAgentFlow(Tool):
    name = "design_agent_flow"
    description = (
        "基于工作流和痛点设计 AI 介入方案. "
        "在 identify_pain_points 之后调用. "
        "返回介入点列表，每个介入点含所在步骤、AI 动作、是否需人工审批、预期效果."
    )
    input_schema = DesignAgentFlowInput
    output_schema = DesignAgentFlowOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, DesignAgentFlowInput)
        log.info("design_agent_flow_called")
        workflow_json = input.workflow_json if isinstance(input.workflow_json, str) else json.dumps(input.workflow_json, ensure_ascii=False)
        pain_points_json = input.pain_points_json if isinstance(input.pain_points_json, str) else json.dumps(input.pain_points_json, ensure_ascii=False)
        user_content = (
            f"Workflow JSON:\n{workflow_json}\n\n"
            f"Pain Points JSON:\n{pain_points_json}"
        )
        result = await call_llm_for_json(
            tier="sonnet",
            system=DESIGN_AGENT_FLOW_SYSTEM,
            user_content=user_content,
            output_schema=DesignAgentFlowOutput,
            tool_name="design_agent_flow_response",
            temperature=0.3,
        )
        return DesignAgentFlowOutput.model_validate(result)


# ============ calculate_roi ============

class ROIBreakdown(BaseModel):
    annual_cost: float
    annual_savings: float
    roi_pct: float
    confidence: str  # low / medium / high
    assumptions: list[str] = Field(default_factory=list)


class CalculateROIInput(ToolInput):
    workflow_json: str | dict[str, Any]
    agent_flow_json: str | dict[str, Any]


class CalculateROIOutput(ToolOutput):
    roi: ROIBreakdown


class CalculateROI(Tool):
    name = "calculate_roi"
    description = (
        "基于工作流和 AI 介入方案计算 ROI. "
        "在 design_agent_flow 之后调用. "
        "返回年化成本、年化收益、ROI 百分比、置信度、关键假设."
    )
    input_schema = CalculateROIInput
    output_schema = CalculateROIOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, CalculateROIInput)
        log.info("calculate_roi_called")
        workflow_json = input.workflow_json if isinstance(input.workflow_json, str) else json.dumps(input.workflow_json, ensure_ascii=False)
        agent_flow_json = input.agent_flow_json if isinstance(input.agent_flow_json, str) else json.dumps(input.agent_flow_json, ensure_ascii=False)
        user_content = (
            f"Workflow JSON:\n{workflow_json}\n\n"
            f"Agent Flow JSON:\n{agent_flow_json}"
        )
        result = await call_llm_for_json(
            tier="sonnet",
            system=CALCULATE_ROI_SYSTEM,
            user_content=user_content,
            output_schema=CalculateROIOutput,
            tool_name="calculate_roi_response",
            temperature=0.0,
        )
        return CalculateROIOutput.model_validate(result)
