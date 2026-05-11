from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.agents.reviewer import ReviewerAgent
from src.core.agent import Agent
from src.core.context import TaskContext
from src.core.coordinator import Coordinator
from src.core.events import Event, EventType
from src.services.config import AISettings, AgentConfig, RenderSettings


def _ai_settings() -> AISettings:
    return AISettings("", "https://api.deepseek.com", "deepseek-chat", "", "gemini")


def _render_settings() -> RenderSettings:
    return RenderSettings(width=320, height=240, fps=15, quality="l")


class CodeAgent(Agent):
    name = "Code"
    listens_to = [EventType.TASK_RECEIVED]

    async def handle(self, event: Event, context: TaskContext) -> Event | None:
        context.current_code = "not valid python("
        return Event(
            type=EventType.CODE_GENERATED,
            payload={"code": context.current_code},
            correlation_id=event.correlation_id,
        )


class ApproverAgent(Agent):
    name = "Approver"
    listens_to = [EventType.CODE_APPROVED]

    async def handle(self, event: Event, context: TaskContext) -> Event | None:
        return Event(
            type=EventType.RENDER_COMPLETED,
            payload={"video_path": "ok.mp4"},
            correlation_id=event.correlation_id,
        )


def test_coordinator_bypasses_reviewer_when_disabled(tmp_path: Path) -> None:
    asyncio.run(_run_coordinator_bypasses_reviewer_when_disabled(tmp_path))


async def _run_coordinator_bypasses_reviewer_when_disabled(tmp_path: Path) -> None:
    coordinator = Coordinator(
        agents=[CodeAgent(), ReviewerAgent(), ApproverAgent()],
        ai_settings=_ai_settings(),
        render_settings=_render_settings(),
        agent_config=AgentConfig(enable_reviewer=False),
    )

    result = await coordinator.run("prompt", tmp_path, tmp_path / "job")

    assert result.success is True
    assert [event.type for event in result.events] == [
        EventType.TASK_RECEIVED,
        EventType.CODE_GENERATED,
        EventType.CODE_APPROVED,
        EventType.RENDER_COMPLETED,
    ]


def test_reviewer_skips_static_review_when_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    asyncio.run(_run_reviewer_skips_static_review_when_disabled(monkeypatch, tmp_path))


async def _run_reviewer_skips_static_review_when_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    context = TaskContext(prompt="prompt", workspace=tmp_path, job_dir=tmp_path / "job")
    context.agent_config = AgentConfig(enable_static_review=False)  # type: ignore[attr-defined]
    context.ai_settings = _ai_settings()  # type: ignore[attr-defined]

    async def approve(_code: str, _context: TaskContext) -> dict:
        return {"approved": True}

    reviewer = ReviewerAgent()
    monkeypatch.setattr(reviewer, "_ai_review", approve)

    event = await reviewer.handle(
        Event(
            type=EventType.CODE_GENERATED,
            payload={"code": "not valid python("},
            correlation_id="cid",
        ),
        context,
    )

    assert event.type == EventType.CODE_APPROVED
