"""端到端冒烟测试 - 验证 search -> score -> fetch 串起来能跑通.

不跑完整 orchestrator (太慢), 只验证 Phase 2 三个核心组件协作.
完整 orchestrator 端到端在 e2e_orchestrator.py 跑.
"""
from __future__ import annotations

import asyncio
import json

from app.core.logging import setup_logging
from app.search.bing_scraper import search_bing
from app.search.fetcher import fetch_page
from app.search.scorer import score_evidence


async def main():
    setup_logging()
    query = "招聘筛选流程"
    print(f"\n=== Phase 2 End-to-End Smoke Test ===")
    print(f"Query: {query}\n")

    # 1. 搜索
    print("--- Step 1: Search ---")
    results = await search_bing(query, num_results=8)
    print(f"Got {len(results)} search results\n")

    if not results:
        print("FAIL: search returned empty, cannot continue")
        return 1

    # 2. 评分 + 抓取
    print("--- Step 2: Score + Fetch ---")
    good_evidence = []
    for i, r in enumerate(results, 1):
        url = r["url"]
        snippet = r.get("snippet", "")
        title = r.get("title")
        print(f"\n[{i}/{len(results)}] Scoring: {url[:80]}")
        try:
            score, reason, is_home, is_disamb, layer = await score_evidence(
                url=url, snippet=snippet, query=query, title=title
            )
            print(f"  Score: {score} (layer {layer}) | is_homepage={is_home} | reason: {reason[:80]}")
            if score >= 7.0 and not is_home and not is_disamb:
                print(f"  -> Fetching (score >= 7)...")
                fetch_result = await fetch_page(url)
                if fetch_result.error:
                    print(f"  -> Fetch FAILED: {fetch_result.error}")
                else:
                    print(f"  -> Fetch OK: {fetch_result.word_count} chars, {fetch_result.fetch_time_ms}ms")
                    good_evidence.append({
                        "url": url,
                        "title": title,
                        "snippet": snippet,
                        "score": score,
                        "content_preview": fetch_result.content[:200],
                    })
            else:
                print(f"  -> Skipped (score < 7 or filtered)")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")

    # 3. 汇总
    print(f"\n=== Summary ===")
    print(f"Search results: {len(results)}")
    print(f"Evidence with score >= 7 and fetched: {len(good_evidence)}")
    if good_evidence:
        print(f"\nTop evidence:")
        for ev in good_evidence[:3]:
            print(f"  - score={ev['score']}: {ev['title']}")
            print(f"    {ev['url']}")
            print(f"    content preview: {ev['content_preview'][:100]}...")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    import sys
    sys.exit(exit_code)
