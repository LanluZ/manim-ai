# core/events.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """事件类型枚举"""

    # 生命周期事件
    TASK_RECEIVED = "task_received"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Planner 事件
    PLAN_CREATED = "plan_created"

    # Coder 事件
    CODE_GENERATED = "code_generated"

    # Reviewer 事件
    CODE_APPROVED = "code_approved"
    CODE_NEEDS_FIX = "code_needs_fix"

    # Renderer 事件
    RENDER_STARTED = "render_started"
    RENDER_COMPLETED = "render_completed"
    RENDER_FAILED = "render_failed"


@dataclass
class Event:
    """事件数据类"""
    type: EventType
    payload: dict[str, Any]
    correlation_id: str  # 关联同一任务的所有事件
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
