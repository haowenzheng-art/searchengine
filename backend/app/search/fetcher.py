"""网页正文抓取器 - Playwright async + BS4 fallback.

设计:
1. Playwright async 抓取 (能过 JS 渲染), 超时 15s, 并发最多 5
2. 智能正文提取: <article> / <main> / [role=main] 优先, fallback 到 <p> 聚合
3. 内容截断到 8000 字符 (保留首尾段, 不是粗暴 [:10000])
4. BS4 作为 fallback: 当 Playwright 启动失败或超时时用 httpx+BS4 抓静态 HTML
5. 失败返回 error, 不静默返回预设数据 (修 legacy/llm_client.py:160-162)

不选 requests 的理由: 很多页面是 SPA, 静态抓取拿不到正文.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from bs4 import BeautifulSoup

from app.core.logging import get_logger

log = get_logger(__name__)

_MAX_CONTENT_CHARS = 8000
_FETCH_TIMEOUT_S = 15
_MAX_CONCURRENT = 5
_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT)


@dataclass
class FetchResult:
    url: str
    content: str
    word_count: int
    fetch_time_ms: int
    title: str | None = None
    error: str | None = None


async def fetch_page(url: str) -> FetchResult:
    """抓取单个 URL 的正文.

    优先用 Playwright (能过 JS), 失败时 fallback 到 httpx+BS4.
    """
    async with _SEMAPHORE:
        log.info("fetch_page_start", url=url)
        try:
            return await _fetch_with_playwright(url)
        except Exception as e:
            log.warning(
                "fetch_page_playwright_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                fallback="httpx+bs4",
            )
            return await _fetch_with_httpx(url)


async def _fetch_with_playwright(url: str) -> FetchResult:
    """用 Playwright 抓取, 适合 SPA / JS 渲染页面."""
    import time

    from playwright.async_api import async_playwright

    start = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            try:
                await page.goto(url, timeout=_FETCH_TIMEOUT_S * 1000, wait_until="domcontentloaded")
                # 等一下让 JS 渲染完成 (网络空闲最好, 但慢; domcontentloaded 够用)
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass  # 网络一直忙就算了, 不阻塞
                html = await page.content()
                title = await page.title()
            finally:
                await context.close()
        finally:
            await browser.close()

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    content = _extract_main_content(html)
    if not content:
        raise RuntimeError("playwright extracted empty content")

    return FetchResult(
        url=url,
        content=content,
        word_count=len(content),
        fetch_time_ms=elapsed_ms,
        title=title,
    )


async def _fetch_with_httpx(url: str) -> FetchResult:
    """用 httpx+BS4 抓静态 HTML, 作为 Playwright 失败的 fallback."""
    import time

    import httpx

    start = time.perf_counter()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_S, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            html = r.text
    except httpx.HTTPError as e:
        return FetchResult(
            url=url,
            content="",
            word_count=0,
            fetch_time_ms=int((time.perf_counter() - start) * 1000),
            error=f"httpx_failed: {e}",
        )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    content = _extract_main_content(html)
    if not content:
        return FetchResult(
            url=url,
            content="",
            word_count=0,
            fetch_time_ms=elapsed_ms,
            error="httpx extracted empty content",
        )

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    return FetchResult(
        url=url,
        content=content,
        word_count=len(content),
        fetch_time_ms=elapsed_ms,
        title=title,
    )


def _extract_main_content(html: str) -> str:
    """智能正文提取: article/main 优先, fallback 到 <p> 聚合.

    截断到 8000 字符, 保留首尾段 (不是粗暴切).
    """
    soup = BeautifulSoup(html, "html.parser")

    # 移除明显的噪音元素
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe"]):
        tag.decompose()

    # 优先级: article > main > [role=main] > #content > .content > body
    candidates = [
        soup.find("article"),
        soup.find("main"),
        soup.find(attrs={"role": "main"}),
        soup.select_one("#content, .content, .article, .post"),
    ]
    container = None
    for c in candidates:
        if c and len(c.get_text(strip=True)) > 200:
            container = c
            break

    if container is None:
        # fallback: 聚合所有 <p>
        paragraphs = soup.find_all("p")
        if not paragraphs:
            return ""
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    else:
        # container 内取所有 <p>
        paragraphs = container.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        if len(text) < 200:
            # container 段落太少, fallback 到 container 全文
            text = container.get_text("\n", strip=True)

    return _truncate_keep_ends(text, _MAX_CONTENT_CHARS)


def _truncate_keep_ends(text: str, max_chars: int) -> str:
    """截断到 max_chars, 保留首尾段.

    不是粗暴切 [:max_chars], 而是保留前 N/2 字符 + 后 N/2 字符,
    中间用 [...] 标记省略, 这样既控制长度又保留首尾信息.
    """
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    head = text[:half].rsplit("\n", 1)[0]  # 在最近的换行处截断, 不切单词
    tail = text[-half:].split("\n", 1)[-1] if "\n" in text[-half:] else text[-half:]
    return f"{head}\n\n[... content truncated {len(text) - max_chars} chars ...]\n\n{tail}"
