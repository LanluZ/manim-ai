# core/agent.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from core.events import Event, EventType

if TYPE_CHECKING:
    from core.context import TaskContext


class Agent(ABC):
    """
    Agent 基类：每个Agent订阅感兴趣的事件，处理后发布新事件

    子类必须定义:
    - name: Agent 名称
    - listens_to: 订阅的事件类型列表
    - handle(): 处理事件的方法
    """

    name: str
    listens_to: list[EventType]

    @abstractmethod
    async def handle(self, event: Event, context: TaskContext) -> Event | None:
        """
        处理事件并返回新事件。

        Args:
            event: 接收到的事件
            context: 任务上下文，包含累积状态

        Returns:
            要发布的新事件，或 None（不触发新事件）
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
