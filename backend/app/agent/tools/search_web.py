"""search_web tool - 调用 DuckDuckGo 搜索 (无 API key).

Phase 2: 用 DuckDuckGo HTML 接口, 返回真实搜索结果.
失败返回空列表, 不 fallback 写死 URL (修 legacy/bing_search.py:52-79).
"""
from __future__ import annotations

from pydantic import BaseModel

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger
from app.search.bing_scraper import search_bing

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
        raw_results = await search_bing(input.query, num_results=input.num_results)
        results = [SearchResultItem(**r) for r in raw_results]
        log.info("search_web_done", query=input.query, result_count=len(results))
        return SearchWebOutput(results=results, query=input.query)

