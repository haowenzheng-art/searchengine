"""
网页抓取模块
抓取真实网页内容
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin
import time


def fetch_webpage(url: str, timeout: int = 10) -> str:
    """
    抓取单个网页内容

    Args:
        url: 网页 URL
        timeout: 超时时间（秒）

    Returns:
        网页文本内容
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # 提取正文文本
        paragraphs = soup.find_all('p')
        text_parts = []

        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 20:  # 只保留有意义的段落
                text_parts.append(text)

        # 如果没有找到 p 标签，尝试获取所有文本
        if not text_parts:
            text_parts = [soup.get_text(separator=' ', strip=True)]

        full_text = '\n'.join(text_parts)

        # 限制长度
        if len(full_text) > 10000:
            full_text = full_text[:10000] + '...[内容截断]'

        return full_text

    except Exception as e:
        print(f"[Scraper] 抓取失败 {url}: {e}")
        return ""


def fetch_multiple_pages(urls: List[str], max_pages: int = 5) -> List[Dict]:
    """
    批量抓取网页

    Args:
        urls: URL 列表
        max_pages: 最大抓取页数

    Returns:
        抓取结果列表，格式为 [{"url": "...", "content": "..."}, ...]
    """
    results = []

    for i, url in enumerate(urls[:max_pages]):
        print(f"[Scraper] 抓取 {i+1}/{min(len(urls), max_pages)}: {url}")
        content = fetch_webpage(url)

        if content:
            results.append({
                'url': url,
                'content': content
            })

        # 避免请求过快
        if i < len(urls) - 1:
            time.sleep(0.5)

    print(f"[Scraper] 成功抓取 {len(results)} 个网页")
    return results


def enrich_search_results(search_results: List[Dict]) -> List[Dict]:
    """
    为搜索结果补充网页内容

    Args:
        search_results: 搜索结果列表

    Returns:
        补充内容后的搜索结果
    """
    enriched = []

    for result in search_results:
        url = result.get('url', '')
        if url:
            content = fetch_webpage(url)
            if content:
                result['snippet'] = content[:500]  # 截取前 500 字符作为摘要
                result['content'] = content

        enriched.append(result)

    return enriched


if __name__ == "__main__":
    # 测试抓取
    test_urls = [
        "https://www.example.com"
    ]

    print("网页抓取模块测试")
    results = fetch_multiple_pages(test_urls, max_pages=1)

    for r in results:
        print(f"\nURL: {r['url']}")
        print(f"内容长度: {len(r['content'])}")
        print(f"预览: {r['content'][:200]}...")
