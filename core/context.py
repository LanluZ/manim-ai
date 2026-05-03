# core/context.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.events import Event


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    video_path: str = ""
    code: str = ""
    error: str = ""
    events: list[Event] = field(default_factory=list)


@dataclass
class TaskContext:
    """任务上下文：存储任务状态和累积数据"""

    prompt: str
    workspace: str
    job_dir: Path | None = None

    # 规划相关
    plan: list[str] = field(default_factory=list)
    current_task_index: int = 0

    # 代码相关
    current_code: str = ""
    review_feedback: str = ""

    # 迭代控制
    iteration_count: int = 0
    max_iterations: int = 5

    # 事件历史
    events: list[Event] = field(default_factory=list)

    # 结果
    result: TaskResult | None = None

    def add_event(self, event: Event) -> None:
        """添加事件到历史"""
        self.events.append(event)

    def can_iterate(self) -> bool:
        """检查是否可以继续迭代"""
        return self.iteration_count < self.max_iterations

    def increment_iteration(self) -> None:
        """增加迭代计数"""
        self.iteration_count += 1
