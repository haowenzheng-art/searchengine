"""Tool 基类 - 所有 tool 必须继承并定义 pydantic I/O schema.

设计原则:
1. 输入输出都是 pydantic 模型 - 强类型，避免 dict in dict out 的混乱
2. to_anthropic() 返回 Anthropic SDK 需要的 JSON schema
3. execute() 是 async - 抓取/LLM 调用都是 IO 密集
4. 每个 tool 独立可测 - 不依赖 orchestrator 状态
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Type

from pydantic import BaseModel


class ToolInput(BaseModel):
    """所有 tool 输入的基类."""
    model_config = {"arbitrary_types_allowed": True}


class ToolOutput(BaseModel):
    """所有 tool 输出的基类."""
    model_config = {"arbitrary_types_allowed": True}


class Tool(ABC):
    """Tool 抽象基类.

    Class attributes:
        name: 工具名，Anthropic SDK 用这个名字调用
        description: 给 LLM 看的描述，决定何时调用此工具
        input_schema: pydantic 模型类，用于校验输入和生成 JSON schema
        output_schema: pydantic 模型类，用于校验输出

    Instance methods:
        execute: 实际执行逻辑，返回 ToolOutput 子类实例
    """

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[Type[ToolInput]]
    output_schema: ClassVar[Type[ToolOutput]]

    @abstractmethod
    async def execute(self, input: ToolInput) -> ToolOutput:
        """执行工具逻辑."""
        raise NotImplementedError

    def to_anthropic(self) -> dict[str, Any]:
        """转成 Anthropic SDK tools 参数格式."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
        }

    def validate_input(self, raw: dict[str, Any]) -> ToolInput:
        return self.input_schema.model_validate(raw)

    def serialize_output(self, output: ToolOutput) -> dict[str, Any]:
        return output.model_dump(mode="json")
