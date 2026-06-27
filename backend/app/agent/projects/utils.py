"""OPC Agent 工具函数."""
from __future__ import annotations

from typing import Any

from app.agent.llm import LLMClient, LLMResponse
from app.core.logging import get_logger

log = get_logger(__name__)


async def llm_chat(
    system: str,
    user: str,
    *,
    llm: LLMClient | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """简单封装：system + user 直接返回文本."""
    client = llm or LLMClient.get()
    response: LLMResponse = await client.create_message(
        messages=[{"role": "user", "content": user}],
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    # 兼容 MockLLMClient (返回单个 dict block) 和真实 LLMResponse
    if isinstance(response, dict):
        return response.get("text", "").strip()

    # Anthropic 返回 content blocks, 取 text 类型拼接
    texts: list[str] = []
    for block in response.content:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(block.get("text", ""))
    return "".join(texts).strip()


def extract_code_block(text: str, language: str = "") -> str:
    """从 markdown 文本中提取 ```language ... ``` 代码块."""
    marker = f"```{language}" if language else "```"
    start = text.find(marker)
    if start == -1:
        # 尝试任意代码块
        start = text.find("```")
        if start == -1:
            return text.strip()
    start = text.find("\n", start) + 1
    end = text.find("```", start)
    if end == -1:
        return text[start:].strip()
    return text[start:end].strip()
