"""search_web tool - 调用 SerpAPI 返回搜索结果.

Phase 1: stub 实现，返回写死的测试数据让 orchestrator 能跑通.
Phase 2: 接 SerpAPI，带 Redis 缓存，失败不 fallback (修 legacy/bing_search.py:52-79).
"""
from __future__ import annotations

from pydantic import BaseModel

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger

log = get_logger(__name__)


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str


class SearchWebInput(ToolInput):
    query: str
    num_results: int = 10


class SearchWebOutput(ToolOutput):
    results: list[SearchResultItem]
    query: str


_STUB_RESULTS: list[SearchResultItem] = [
    SearchResultItem(
        title="招聘筛选流程详解：从简历投递到录用的完整步骤",
        url="https://hr.example.com/articles/recruitment-screening-process",
        snippet="本文详细解析企业招聘筛选流程的6个关键步骤：简历初筛、电话面试、专业测试、复试、背景调查、录用决策...",
    ),
    SearchResultItem(
        title="HR必读：如何设计高效的简历筛选标准",
        url="https://hr.example.com/blog/resume-screening-criteria",
        snippet="设计简历筛选标准的核心维度：硬技能匹配、软技能评估、经验相关性、文化契合度。附实操模板...",
    ),
    SearchResultItem(
        title="大厂招聘面试流程拆解：字节跳动/阿里/腾讯",
        url="https://tech.example.com/hr/big-tech-interview-flow",
        snippet="字节跳动5轮面试、阿里4轮+HR、腾讯技术面+群面。每轮考察点、淘汰率、决策标准...",
    ),
]


class SearchWebTool(Tool):
    name = "search_web"
    description = (
        "搜索互联网，返回与查询关键词相关的网页列表. "
        "每个结果包含标题、URL 和摘要. "
        "用于在分析开始时收集证据."
    )
    input_schema = SearchWebInput
    output_schema = SearchWebOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, SearchWebInput)
        log.info("search_web_called", query=input.query, num_results=input.num_results)
        results = _STUB_RESULTS[: input.num_results]
        log.info("search_web_done", query=input.query, result_count=len(results))
        return SearchWebOutput(results=results, query=input.query)
