# agents/coder.py
from __future__ import annotations

from core.agent import Agent
from core.context import TaskContext
from core.events import Event, EventType

SECTION_MARKER = "# <<SECTION_BREAK>>"

CODER_PROMPT_NEW = """创建一个新的 manim 场景来实现以下任务：

任务列表：
{tasks}

要求：
1. 代码必须包含: from manim import *
2. 必须定义且只定义一个 Scene 子类
3. 不要输出任何解释文字，只输出代码
4. 每段动画控制在1-3秒以内
5. 动画要保持场景连续性，不要使用 FadeOut 清空画面
6. 保证动画结束时场景可见居中"""

CODER_PROMPT_CONTINUE = """以下是当前场景的完整代码：

```python
{code}
```

需求：{prompt}

请在 `construct` 方法的末尾续写代码以实现上述需求。
{feedback_section}
严格遵守以下规则：
1. 仅返回新增的代码片段，不要重复已有代码
2. 新增代码必须以 `{marker}` 开头
3. 不要包含 `class` 定义或 `def construct`
4. 保持变量名和场景状态的连贯性
5. 不要使用 `self.next_section()`，使用标记代替"""


class CoderAgent(Agent):
    """代码生成Agent：根据任务生成或续写Manim代码"""

    name = "Coder"
    listens_to = [EventType.PLAN_CREATED, EventType.CODE_NEEDS_FIX]

    async def handle(self, event: Event, context: TaskContext) -> Event | None:
        """处理事件，生成Manim代码"""
        if event.type == EventType.PLAN_CREATED:
            return await self._handle_plan_created(event, context)
        elif event.type == EventType.CODE_NEEDS_FIX:
            return await self._handle_code_needs_fix(event, context)
        return None

    async def _handle_plan_created(self, event: Event, context: TaskContext) -> Event:
        """处理规划完成事件，生成新代码"""
        tasks = event.payload["tasks"]

        try:
            from app.ai_clients import generate_manim_code, sanitize_code

            prompt = CODER_PROMPT_NEW.format(tasks="\n".join(f"- {t}" for t in tasks))
            ai_mode = self._get_ai_mode(context)

            _, code = generate_manim_code(
                settings=context.ai_settings,
                mode=ai_mode,
                prompt=prompt,
                previous_code="",
                timeout=context.agent_config.ai_timeout,
            )

            code = sanitize_code(code)
            context.current_code = code
            context.increment_iteration()

            return Event(
                type=EventType.CODE_GENERATED,
                payload={"code": code},
                correlation_id=event.correlation_id,
            )

        except Exception as exc:
            return Event(
                type=EventType.TASK_FAILED,
                payload={"error": f"代码生成失败: {exc}"},
                correlation_id=event.correlation_id,
            )

    async def _handle_code_needs_fix(self, event: Event, context: TaskContext) -> Event:
        """处理代码修复请求"""
        feedback = event.payload.get("feedback", "")

        if not context.can_iterate():
            return Event(
                type=EventType.TASK_FAILED,
                payload={"error": f"迭代次数超限 ({context.max_iterations}次)"},
                correlation_id=event.correlation_id,
            )

        try:
            from app.ai_clients import generate_manim_code, sanitize_code

            feedback_section = f"\n审查反馈：{feedback}\n请根据反馈修复代码。\n"
            prompt = CODER_PROMPT_CONTINUE.format(
                code=context.current_code,
                prompt=context.prompt,
                feedback_section=feedback_section,
                marker=SECTION_MARKER,
            )

            ai_mode = self._get_ai_mode(context)
            _, code = generate_manim_code(
                settings=context.ai_settings,
                mode=ai_mode,
                prompt=prompt,
                previous_code=context.current_code,
                timeout=context.agent_config.ai_timeout,
            )

            code = sanitize_code(code, previous_code=context.current_code)
            context.current_code = code
            context.increment_iteration()

            return Event(
                type=EventType.CODE_GENERATED,
                payload={"code": code},
                correlation_id=event.correlation_id,
            )

        except Exception as exc:
            return Event(
                type=EventType.TASK_FAILED,
                payload={"error": f"代码修复失败: {exc}"},
                correlation_id=event.correlation_id,
            )

