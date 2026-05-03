# agents/renderer.py
from __future__ import annotations

from pathlib import Path

from src.services.manim_runner import RenderError, render_manim_scene
from src.core.agent import Agent
from src.core.context import TaskContext, TaskResult
from src.core.events import Event, EventType


class RendererAgent(Agent):
    """渲染执行Agent：执行Manim渲染，处理渲染错误"""

    name = "Renderer"
    listens_to = [EventType.CODE_APPROVED]

    async def handle(self, event: Event, context: TaskContext) -> Event:
        """执行渲染"""
        code = event.payload["code"]

        try:
            job_dir = context.job_dir or Path("data/jobs/default")
            job_dir.mkdir(parents=True, exist_ok=True)

            result = render_manim_scene(
                cumulative_code=code,
                settings=context.render_settings,
                job_dir=job_dir,
                logger=None,
            )

            context.result = TaskResult(
                success=True,
                video_path=str(result.video_path),
                code=code,
            )

            return Event(
                type=EventType.RENDER_COMPLETED,
                payload={
                    "video_path": str(result.video_path),
                    "script_path": str(result.script_path),
                    "section_videos": [str(p) for p in result.section_videos],
                },
                correlation_id=event.correlation_id,
            )

        except RenderError as exc:
            error_msg = str(exc)

            if "Scene 子类" in error_msg or "SyntaxError" in error_msg:
                return Event(
                    type=EventType.CODE_NEEDS_FIX,
                    payload={"feedback": f"渲染错误（可修复）: {error_msg}"},
                    correlation_id=event.correlation_id,
                )

            return Event(
                type=EventType.RENDER_FAILED,
                payload={"error": error_msg},
                correlation_id=event.correlation_id,
            )

        except Exception as exc:
            return Event(
                type=EventType.TASK_FAILED,
                payload={"error": f"渲染异常: {exc}"},
                correlation_id=event.correlation_id,
            )
