# core/coordinator.py
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable

from src.services.config import AgentConfig, AISettings, RenderSettings
from src.core.agent import Agent
from src.core.context import TaskContext, TaskResult
from src.core.events import Event, EventType
from src.core.message_bus import EventBus


class Coordinator:
    """
    中心协调器：管理Agent生命周期和任务执行

    职责:
    1. 注册Agent到事件总线
    2. 创建任务上下文
    3. 驱动事件循环直到任务完成
    4. 收集结果
    """

    def __init__(
        self,
        agents: list[Agent],
        ai_settings: AISettings,
        render_settings: RenderSettings,
        agent_config: AgentConfig | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.agents = agents
        self.ai_settings = ai_settings
        self.render_settings = render_settings
        self.agent_config = agent_config or AgentConfig()
        self.progress_callback = progress_callback
        self.event_bus = EventBus()
        self._register_agents()

    def _register_agents(self) -> None:
        """注册所有Agent到事件总线"""
        for agent in self.agents:
            for event_type in agent.listens_to:
                self.event_bus.subscribe(event_type, agent)
            self._log(f"已注册 Agent: {agent.name}")

    def _log(self, message: str) -> None:
        """输出进度信息"""
        if self.progress_callback:
            self.progress_callback(message)

    async def run(self, prompt: str, workspace: Path, job_dir: Path) -> TaskResult:
        """
        执行任务

        Args:
            prompt: 用户输入的动画描述
            workspace: 工作区路径
            job_dir: 工作区目录

        Returns:
            TaskResult: 任务执行结果
        """
        # 创建任务上下文
        context = TaskContext(
            prompt=prompt,
            workspace=workspace,
            job_dir=job_dir,
            max_iterations=self.agent_config.max_iterations,
        )

        # 将配置注入上下文（动态属性）
        context.ai_settings = self.ai_settings  # type: ignore[attr-defined]
        context.render_settings = self.render_settings  # type: ignore[attr-defined]
        context.agent_config = self.agent_config  # type: ignore[attr-defined]
        context.progress_callback = self.progress_callback  # type: ignore[attr-defined]

        # 初始事件
        event = Event(
            type=EventType.TASK_RECEIVED,
            payload={"prompt": prompt},
            correlation_id=str(uuid.uuid4()),
        )

        self._log(f"开始任务: {prompt}")

        # 最终状态
        final_events = {EventType.TASK_COMPLETED, EventType.TASK_FAILED, EventType.RENDER_COMPLETED}

        max_loop_iterations = 100  # 安全限制，防止无限循环
        loop_count = 0

        try:
            while event.type not in final_events:
                loop_count += 1
                if loop_count > max_loop_iterations:
                    return TaskResult(
                        success=False,
                        error=f"执行循环超限 ({max_loop_iterations}次)",
                        events=context.events,
                    )

                context.add_event(event)
                self._log(f"处理事件: {event.type.value}")

                # 分发事件给订阅的Agent
                result_event = await self.event_bus.dispatch(event, context)

                if result_event is None:
                    # 没有Agent处理此事件
                    self._log(f"警告: 没有Agent处理事件 {event.type.value}")
                    break

                event = result_event

            context.add_event(event)

            if event.type in (EventType.TASK_COMPLETED, EventType.RENDER_COMPLETED):
                self._log("任务完成: 渲染成功")
                result = context.result or TaskResult(
                    success=True,
                    video_path=event.payload.get("video_path", ""),
                    code=context.current_code,
                )
                result.events = context.events
                return result
            else:
                self._log(f"任务失败: {event.payload.get('error', '未知错误')}")
                result = TaskResult(
                    success=False,
                    error=event.payload.get("error", "任务失败"),
                    code=context.current_code,
                )
                result.events = context.events
                return result

        except Exception as exc:
            self._log(f"协调器异常: {exc}")
            return TaskResult(
                success=False,
                error=str(exc),
                events=context.events,
            )
