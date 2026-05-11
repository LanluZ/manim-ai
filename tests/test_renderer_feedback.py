from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.agents import renderer as renderer_module
from src.agents.renderer import RendererAgent
from src.core.context import TaskContext
from src.core.events import Event, EventType
from src.services.config import AgentConfig, RenderSettings
from src.services.manim_runner import RenderError


def _context(tmp_path: Path, *, enable_auto_fix: bool) -> TaskContext:
    context = TaskContext(prompt="prompt", workspace=tmp_path, job_dir=tmp_path / "job")
    context.render_settings = RenderSettings(width=320, height=240, fps=15, quality="l")  # type: ignore[attr-defined]
    context.agent_config = AgentConfig(enable_auto_fix=enable_auto_fix)  # type: ignore[attr-defined]
    return context


def test_renderer_returns_code_needs_fix_for_repairable_errors_when_auto_fix_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    asyncio.run(
        _run_renderer_returns_code_needs_fix_for_repairable_errors_when_auto_fix_enabled(
            monkeypatch,
            tmp_path,
        )
    )


async def _run_renderer_returns_code_needs_fix_for_repairable_errors_when_auto_fix_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_render(**_kwargs: object) -> object:
        raise RenderError("NameError: name 'axes' is not defined")

    monkeypatch.setattr(renderer_module, "render_manim_scene", fail_render)
    event = await RendererAgent().handle(
        Event(EventType.CODE_APPROVED, {"code": "from manim import *"}, "cid"),
        _context(tmp_path, enable_auto_fix=True),
    )

    assert event.type == EventType.CODE_NEEDS_FIX
    assert "渲染错误" in event.payload["feedback"]


def test_renderer_returns_render_failed_for_repairable_errors_when_auto_fix_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    asyncio.run(
        _run_renderer_returns_render_failed_for_repairable_errors_when_auto_fix_disabled(
            monkeypatch,
            tmp_path,
        )
    )


async def _run_renderer_returns_render_failed_for_repairable_errors_when_auto_fix_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_render(**_kwargs: object) -> object:
        raise RenderError("NameError: name 'axes' is not defined")

    monkeypatch.setattr(renderer_module, "render_manim_scene", fail_render)
    event = await RendererAgent().handle(
        Event(EventType.CODE_APPROVED, {"code": "from manim import *"}, "cid"),
        _context(tmp_path, enable_auto_fix=False),
    )

    assert event.type == EventType.RENDER_FAILED
    assert "NameError" in event.payload["error"]
