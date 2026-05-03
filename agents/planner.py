# agents/planner.py
from __future__ import annotations

import json
from typing import Any

from core.agent import Agent
from core.context import TaskContext
from core.events import Event, EventType

PLANNER_PROMPT = """你是一个动画任务规划专家。请分析用户需求并分解为具体步骤。

用户需求：{prompt}

请输出 JSON 格式的任务列表：
{{"tasks": ["任务1描述", "任务2描述", ...]}}

规则：
1. 每个任务对应一段 1-3 秒的动画
2. 任务之间要有逻辑连贯性
3. 不要使用 FadeOut 清空画面
4. 保持场景连续性"""


class PlannerAgent(Agent):
    """需求分析Agent：分析用户需求，分解为可执行的任务列表"""

    name = "Planner"
    listens_to = [EventType.TASK_RECEIVED]

    async def handle(self, event: Event, context: TaskContext) -> Event | None:
        """处理 TASK_RECEIVED 事件，返回 PLAN_CREATED"""
        prompt = event.payload["prompt"]

        try:
            # 构建完整提示词
            full_prompt = PLANNER_PROMPT.format(prompt=prompt)

            # 调用AI
            from app.ai_clients import generate_manim_code
            ai_mode = self._get_ai_mode(context)

            _, response = generate_manim_code(
                settings=context.ai_settings,
                mode=ai_mode,
                prompt=full_prompt,
                previous_code="",
                timeout=context.agent_config.ai_timeout,
            )

            # 解析JSON响应
            tasks = self._parse_tasks(response)

            return Event(
                type=EventType.PLAN_CREATED,
                payload={"tasks": tasks, "original_prompt": prompt},
                correlation_id=event.correlation_id,
            )

        except Exception as exc:
            return Event(
                type=EventType.TASK_FAILED,
                payload={"error": f"规划失败: {exc}"},
                correlation_id=event.correlation_id,
            )

    def _get_ai_mode(self, context: TaskContext) -> str:
        """获取AI模式"""
        return getattr(context, 'ai_mode', 'deepseek')

    def _parse_tasks(self, response: str) -> list[str]:
        """解析AI返回的任务列表"""
        try:
            if "```" in response:
                parts = response.split("```")
                for part in parts:
                    if part.strip().startswith("json"):
                        response = part.strip()[4:]
                        break

            data = json.loads(response)
            return data.get("tasks", [])
        except json.JSONDecodeError:
            return [line.strip() for line in response.split("\n") if line.strip()]
