"""Helper for LLM tools that need structured JSON output.

Pattern: use tool_use to force the LLM to call a "response" tool,
guaranteeing structured output that matches our pydantic schema.
"""
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from app.agent.llm import get_current_llm
from app.core.logging import get_logger

log = get_logger(__name__)


async def call_llm_for_json(
    *,
    tier: str,
    system: str,
    user_content: str,
    output_schema: Type[BaseModel],
    tool_name: str,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Call LLM, force structured output via tool_use, return parsed dict.

    Raises:
        RuntimeError: if LLM did not call the expected tool.
    """
    client = get_current_llm()
    # Agnes/OpenAI 兼容代理在强制 tool_choice 时可能不返回 tool_calls；
    # 只提供一个 tool 时 auto 仍会调用它，所以 OpenAI provider 不强制。
    tool_choice: dict[str, Any] | None = None
    if client.provider != "openai":
        tool_choice = {"type": "tool", "name": tool_name}

    response = await client.create_message(
        messages=[{"role": "user", "content": user_content}],
        tier=tier,
        system=system,
        tools=[
            {
                "name": tool_name,
                "description": "Return the structured result of the analysis.",
                "input_schema": output_schema.model_json_schema(),
            }
        ],
        tool_choice=tool_choice,
        temperature=temperature,
    )
    for block in response.content:
        if block.get("type") == "tool_use" and block.get("name") == tool_name:
            log.info(
                "llm_tool_json_ok",
                tool_name=tool_name,
                tier=tier,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            return block["input"]
    log.error("llm_tool_json_missing", tool_name=tool_name, tier=tier, blocks=response.content)
    raise RuntimeError(f"LLM did not call expected tool: {tool_name}")
