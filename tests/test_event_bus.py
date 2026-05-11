from __future__ import annotations

import asyncio
from pathlib import Path

from src.core.agent import Agent
from src.core.context import TaskContext
from src.core.events import Event, EventType
from src.core.message_bus import EventBus


class EchoAgent(Agent):
    name = "Echo"
    listens_to = [EventType.TASK_RECEIVED]

    async def handle(self, event: Event, context: TaskContext) -> Event | None:
        return Event(
            type=EventType.PLAN_CREATED,
            payload={"prompt": event.payload["prompt"]},
            correlation_id=event.correlation_id,
        )


def test_dispatch_publishes_returned_result_event() -> None:
    asyncio.run(_run_dispatch_publishes_returned_result_event())


async def _run_dispatch_publishes_returned_result_event() -> None:
    bus = EventBus()
    bus.subscribe(EventType.TASK_RECEIVED, EchoAgent())
    context = TaskContext(prompt="p", workspace=Path("workspace"))
    event = Event(
        type=EventType.TASK_RECEIVED,
        payload={"prompt": "p"},
        correlation_id="cid",
    )

    result = await bus.dispatch(event, context)
    queued = await bus.get_result(timeout=0.1)

    assert result is queued
    assert queued.type == EventType.PLAN_CREATED
    assert queued.payload == {"prompt": "p"}
