"""搜索引擎封装 - 用 ddgs 库 (DuckDuckGo Search).

设计:
1. ddgs 库专门处理 DDG 反爬, 返回真实 URL (不需要解码)
2. 失败返回空列表 - 不 fallback 写死 URL (修 legacy/bing_search.py:42-47)
3. 函数名保留 search_bing 兼容现有 search_web tool 调用

为什么不用直接 httpx 爬 DDG:
- DDG 反爬严重, 短时间内多次请求会触发 anomaly-modal 验证
- ddgs 库内部处理了反爬 (随机 UA + 请求间隔)

为什么不用 Bing 爬虫:
- Bing 对中文招聘类 query 默认返回招聘网站首页 (zhaopin.com 等)
- ddgs 返回的中文结果质量高 (知乎/MBA智库/Moka 等真实文章)
"""
from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


async def search_bing(query: str, num_results: int = 15) -> list[dict]:
    """用 ddgs 库异步搜索 (函数名保留 search_bing 兼容 tool 调用).

    Args:
        query: 搜索关键词
        num_results: 最多返回结果数

    Returns:
        List[{title, url, snippet}]. 失败时返回空列表, 不抛异常, 不 fallback.
    """
    if not query.strip():
        log.warning("search_engine_empty_query")
        return []

    log.info("search_engine_start", query=query, num_results=num_results)

    # ddgs 库是同步的, 用 asyncio.to_thread 跑在 thread pool
    import asyncio

    try:
        results = await asyncio.to_thread(_sync_ddg_search, query, num_results)
    except Exception as e:
        log.error(
            "search_engine_unexpected_error",
            query=query,
            error=str(e),
            error_type=type(e).__name__,
        )
        return []

    log.info(
        "search_engine_done",
        query=query,
        result_count=len(results),
    )
    return results


def _sync_ddg_search(query: str, num_results: int) -> list[dict]:
    """同步调 ddgs 库 (会阻塞, 必须在 thread pool 跑)."""
    from ddgs import DDGS

    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=num_results))

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw
        if r.get("href", "").startswith("http")
    ]
