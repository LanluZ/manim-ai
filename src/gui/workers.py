"""GUI 后台工作线程：基于多Agent协调系统的异步任务执行器"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from src.core.context import TaskResult
from src.core.coordinator import Coordinator
from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.renderer import RendererAgent
from src.services.config import AISettings, RenderSettings


@dataclass(frozen=True)
class GuiTaskResult:
    """GUI 层的任务结果，适配旧接口"""
    ai_provider: str
    video_path: str
    manim_code: str
    section_videos: list[Path]


class AgentWorker(QObject):
    """基于多Agent协调系统的后台工作器"""

    started = Signal()
    progress = Signal(str)
    finished = Signal(GuiTaskResult)
    failed = Signal(str)

    def __init__(
        self,
        ai_settings: AISettings,
        ai_mode: str,
        prompt: str,
        previous_code: str,
        settings: RenderSettings,
        job_dir: Path,
    ) -> None:
        super().__init__()
        self._ai_settings = ai_settings
        self._ai_mode = ai_mode
        self._prompt = prompt
        self._previous_code = previous_code
        self._settings = settings
        self._job_dir = job_dir

    def run(self) -> None:
        """在工作线程中运行多Agent系统"""
        # 在当前线程中创建并设置事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.started.emit()
            self.progress.emit("初始化多Agent系统...")

            # 创建所有Agent
            agents = [
                PlannerAgent(),
                CoderAgent(),
                ReviewerAgent(),
                RendererAgent(),
            ]

            # 创建协调器
            coordinator = Coordinator(
                agents=agents,
                ai_settings=self._ai_settings,
                render_settings=self._settings,
                ai_mode=self._ai_mode,
                progress_callback=self.progress.emit,
            )

            # 准备工作区
            workspace = self._job_dir.parent
            self._job_dir.mkdir(parents=True, exist_ok=True)

            # 运行异步任务
            result: TaskResult = loop.run_until_complete(
                coordinator.run(
                    prompt=self._prompt,
                    workspace=workspace,
                    job_dir=self._job_dir,
                )
            )

            # 处理结果
            if result.success:
                # 收集分段视频
                section_videos: list[Path] = []
                if result.video_path:
                    from src.services.manim_runner import extract_scene_class, find_section_videos
                    try:
                        class_name = extract_scene_class(result.code)
                        section_videos = find_section_videos(self._job_dir, class_name)
                    except Exception:
                        pass

                self.finished.emit(
                    GuiTaskResult(
                        ai_provider=self._ai_mode,
                        video_path=result.video_path,
                        manim_code=result.code,
                        section_videos=section_videos,
                    )
                )
            else:
                self.failed.emit(result.error or "任务失败")

        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            loop.close()


class _WorkerThread(QThread):
    """内部线程类，直接在新线程中运行工作器"""

    def __init__(self, worker: AgentWorker) -> None:
        super().__init__()
        self._worker = worker

    def run(self) -> None:
        self._worker.run()


def start_worker(worker: AgentWorker) -> QThread:
    """启动工作线程"""
    thread = _WorkerThread(worker)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    return thread
