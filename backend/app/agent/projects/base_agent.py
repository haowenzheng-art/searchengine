"""OPC Project Agent 基类.

复用原 OPC 的 perceive-reason-act 循环, 但用 Python 实现,
并与 WTA 的 LLMClient / ToolRegistry 风格保持一致.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.agent.llm import LLMClient


@dataclass
class AgentState:
    project_id: int
    role: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAction:
    type: str
    payload: Any = None


class ProjectAgent(ABC):
    """OPC 项目生成 Agent 基类."""

    def __init__(self, project_id: int, context: dict[str, Any], llm: LLMClient | None = None):
        self.project_id = project_id
        self.context = context
        self.llm = llm or LLMClient.get()
        self.actions: list[str] = []
        self.memories: list[dict] = []
        self._done = False

    @property
    @abstractmethod
    def role(self) -> str:
        ...

    @abstractmethod
    async def perceive(self) -> AgentState:
        ...

    @abstractmethod
    async def reason(self, state: AgentState) -> AgentAction:
        ...

    @abstractmethod
    async def act(self, action: AgentAction) -> Any:
        ...

    def is_done(self) -> bool:
        return self._done

    def mark_done(self) -> None:
        self._done = True

    def record_action(self, action: str) -> None:
        self.actions.append(action)

    async def save_memory(self, observation: str, insight: str = "", importance: int = 5) -> None:
        self.memories.append({
            "action": self.actions[-1] if self.actions else "",
            "observation": observation,
            "insight": insight,
            "importance": importance,
        })

    async def run(self) -> None:
        while not self.is_done():
            state = await self.perceive()
            action = await self.reason(state)
            if action.type == "WAIT":
                break
            await self.act(action)
