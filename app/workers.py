from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from app.ai_clients import generate_manim_code, sanitize_code, ensure_section_addition
from app.config import AISettings, RenderSettings
from app.manim_runner import RenderResult, render_manim_scene


@dataclass(frozen=True)
class TaskResult:
    ai_provider: str
    render_result: RenderResult
    manim_code: str


class RenderWorker(QObject):
    started = Signal()
    progress = Signal(str)
    finished = Signal(TaskResult)
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
        try:
            self.started.emit()
            self.progress.emit("调用 AI 生成代码...")
            provider, code = generate_manim_code(
                self._ai_settings,
                self._ai_mode,
                self._prompt,
                self._previous_code,
                debug=self.progress.emit,
            )
            code = sanitize_code(code, previous_code=self._previous_code)
            # 确保正确添加了分段
            code = ensure_section_addition(self._previous_code, code, self._prompt)
            self.progress.emit(f"AI ({provider}) 已返回代码，开始渲染...")
            render_result = render_manim_scene(
                code,
                self._settings,
                self._job_dir,
                logger=self.progress.emit,
            )
            self.progress.emit("渲染完成")
            self.finished.emit(
                TaskResult(
                    ai_provider=provider,
                    render_result=render_result,
                    manim_code=code,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


def start_worker(worker: RenderWorker) -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    return thread
