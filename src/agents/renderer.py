# agents/renderer.py
from __future__ import annotations

from pathlib import Path
from time import perf_counter

from src.core.agent import Agent
from src.core.context import TaskContext, TaskResult
from src.core.events import Event, EventType
from src.core.metrics import RenderAttempt
from src.services.manim_runner import RenderError, render_manim_scene


class RendererAgent(Agent):
    """渲染执行Agent：执行Manim渲染，处理渲染错误"""

    name = "Renderer"
    listens_to = [EventType.CODE_APPROVED]

    async def handle(self, event: Event, context: TaskContext) -> Event:
        """执行渲染"""
        code = event.payload["code"]
        started = perf_counter()

        try:
            job_dir = context.job_dir or Path("data/jobs/default")
            job_dir.mkdir(parents=True, exist_ok=True)

            result = render_manim_scene(
                cumulative_code=code,
                settings=context.render_settings,
                job_dir=job_dir,
                logger=None,
                timeout=context.agent_config.render_timeout,
            )
            context.metrics.render_attempts.append(
                RenderAttempt(success=True, duration_seconds=perf_counter() - started)
            )
            if context.metrics.first_render_success is None:
                context.metrics.first_render_success = True

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
            context.metrics.render_attempts.append(
                RenderAttempt(
                    success=False,
                    duration_seconds=perf_counter() - started,
                    error=error_msg,
                )
            )
            if context.metrics.first_render_success is None:
                context.metrics.first_render_success = False

            agent_config = getattr(context, "agent_config", None)
            enable_auto_fix = getattr(agent_config, "enable_auto_fix", True)
            if enable_auto_fix and _is_repairable_render_error(error_msg):
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
            context.metrics.render_attempts.append(
                RenderAttempt(
                    success=False,
                    duration_seconds=perf_counter() - started,
                    error=str(exc),
                )
            )
            if context.metrics.first_render_success is None:
                context.metrics.first_render_success = False
            return Event(
                type=EventType.TASK_FAILED,
                payload={"error": f"渲染异常: {exc}"},
                correlation_id=event.correlation_id,
            )


def _is_repairable_render_error(error_msg: str) -> bool:
    repairable_markers = (
        "Scene 子类",
        "SyntaxError",
        "NameError",
        "AttributeError",
        "TypeError",
        "ValueError",
        "ImportError",
        "ModuleNotFoundError",
    )
    return any(marker in error_msg for marker in repairable_markers)
