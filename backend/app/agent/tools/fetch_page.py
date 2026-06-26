"""fetch_page tool - Playwright 抓取页面正文.

Phase 1: stub 实现，返回写死的正文让 orchestrator 能跑通.
Phase 2: Playwright async + 智能正文提取 + 并发抓取 + 内容截断.
"""
from __future__ import annotations

from pydantic import Field

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger

log = get_logger(__name__)


class FetchPageInput(ToolInput):
    url: str


class FetchPageOutput(ToolOutput):
    url: str
    content: str
    word_count: int = Field(ge=0)
    fetch_time_ms: int = Field(ge=0)
    title: str | None = None


_STUB_CONTENT = """招聘筛选流程的完整解析

招聘筛选是企业人才获取的核心环节，直接影响用人质量和招聘成本。一个标准的招聘筛选流程通常包含以下六个阶段：

1. 简历初筛
HR 或招聘专员根据 JD（Job Description）要求，对投递的简历进行第一轮筛选。核心维度包括：硬技能匹配（学历、专业、工作年限）、经验相关性、行业背景、简历完整性。这一阶段通常使用 ATS（Applicant Tracking System）自动过滤，淘汰率约 60-70%。

2. 电话面试
对通过初筛的候选人进行 15-30 分钟电话沟通。主要确认：简历信息真实性、求职动机、薪资期望、到岗时间。电话面试淘汰率约 30-40%。

3. 专业测试
针对技术岗或专业岗，安排笔试或在线测试。考察专业能力、逻辑思维、问题解决能力。测试形式包括：编程题、案例分析、性格测评。

4. 复试（多轮面试）
通常 2-3 轮，包括：
- 用人部门主管面试：考察专业能力和团队契合度
- 跨部门面试：考察协作能力
- 高管面试（关键岗位）：考察战略思维和文化匹配

5. 背景调查
对通过复试的候选人进行背景核实。内容包括：工作经历验证、学历验证、reference check、犯罪记录查询（敏感岗位）。

6. 录用决策
综合所有面试反馈和背景调查结果，由用人部门负责人和 HR 共同决策。决策结果：录用、待定、不录用。录用后启动 offer 流程。

痛点分析：
- 简历初筛耗时：HR 平均每份简历 6-8 秒，大批量投递时人力不足
- 电话面试效率低：30% 的候选人爽约或电话无人接听
- 面试反馈不一致：不同面试官评价标准差异大
- 背景调查周期长：通常 5-10 个工作日，影响 offer 节奏

AI 介入机会：
- 简历自动筛选（基于 JD 匹配）
- 智能电话面试（语音机器人初筛）
- 面试评价标准化（结构化面试题库）
- 背景调查自动化（API 对接学信网、社保）
"""


class FetchPageTool(Tool):
    name = "fetch_page"
    description = (
        "抓取指定 URL 的页面正文. "
        "返回正文内容、字数、抓取耗时. "
        "只对 score >= 7 的 URL 调用，避免浪费."
    )
    input_schema = FetchPageInput
    output_schema = FetchPageOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, FetchPageInput)
        log.info("fetch_page_called", url=input.url)
        # Phase 1 stub: 返回写死正文
        # Phase 2 替换为 Playwright async + 智能正文提取
        return FetchPageOutput(
            url=input.url,
            content=_STUB_CONTENT,
            word_count=len(_STUB_CONTENT),
            fetch_time_ms=1200,
            title="招聘筛选流程的完整解析",
        )
