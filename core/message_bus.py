# core/message_bus.py
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING

from core.events import Event, EventType

if TYPE_CHECKING:
    from core.agent import Agent
    from core.context import TaskContext


class EventBus:
    """异步事件总线：Agent 通过订阅/发布事件通信"""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Agent]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._result_queue: asyncio.Queue[Event] = asyncio.Queue()

    def subscribe(self, event_type: EventType, agent: Agent) -> None:
        """订阅事件类型"""
        if agent not in self._subscribers[event_type]:
            self._subscribers[event_type].append(agent)

    def unsubscribe(self, event_type: EventType, agent: Agent) -> None:
        """取消订阅"""
        if agent in self._subscribers[event_type]:
            self._subscribers[event_type].remove(agent)

    async def publish(self, event: Event) -> None:
        """发布事件到队列"""
        await self._queue.put(event)

    async def publish_result(self, event: Event) -> None:
        """发布处理结果事件"""
        await self._result_queue.put(event)

    async def get_event(self, timeout: float | None = None) -> Event:
        """获取待处理事件"""
        if timeout:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        return await self._queue.get()

    async def get_result(self, timeout: float | None = None) -> Event:
        """获取结果事件"""
        if timeout:
            return await asyncio.wait_for(self._result_queue.get(), timeout=timeout)
        return await self._result_queue.get()

    async def dispatch(self, event: Event, context: TaskContext) -> Event | None:
        """分发事件给订阅者，返回处理结果"""
        subscribers = list(self._subscribers.get(event.type, []))
        if not subscribers:
            return None

        # 按顺序处理订阅者（通常每个事件类型只有一个订阅者）
        for agent in subscribers:
            result = await agent.handle(event, context)
            if result is not None:
                await self.publish_result(result)
                return result

        return None
