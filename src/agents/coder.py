# agents/coder.py
from __future__ import annotations

from src.core.agent import Agent
from src.core.context import TaskContext
from src.core.events import Event, EventType

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

CODER_PROMPT_FAST_NEW = """创建一个极简、快速渲染的 Manim 预览场景来表达以下数学动画需求：

{task}

硬性要求：
1. 只输出 Python 代码，不要解释文字
2. 必须包含: from manim import *
3. 必须定义且只定义一个 Scene 子类
4. 总代码不超过 35 行
5. 不要使用 MathTex、Tex、LaTeX、DecimalNumber、NumberPlane、ThreeDScene
6. 不要在 Axes 中显示数字，不要使用 include_numbers=True
7. 最多调用一次 self.play，run_time 不超过 0.25
8. self.wait 不超过 0.1
9. 对象数量少于 12 个，用 Text、Line、Dot、VGroup、Axes、VMobject 即可
10. 目标是 320x180 低分辨率下 15 秒内渲染出有效 mp4"""

CODER_PROMPT_REPAIR = """以下是当前 Manim 场景代码：

```python
{code}
```

原始需求：{prompt}

修复反馈：
{feedback}

请返回完整修正后的 Python 代码。
严格遵守以下规则：
1. 代码必须包含: from manim import *
2. 必须定义且只定义一个 Scene 子类
3. 不要输出解释文字，只输出代码
4. 修复反馈中指出的问题，不要只返回新增片段
5. 不要使用 `{marker}` 或 self.next_section()"""


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
            from src.services.ai_clients import generate_manim_code, sanitize_code
            from src.services.template_generator import generate_fast_template_scene

            if context.agent_config.optimize_for_speed:
                prompt = CODER_PROMPT_FAST_NEW.format(task="；".join(str(task) for task in tasks))
            else:
                prompt = CODER_PROMPT_NEW.format(tasks="\n".join(f"- {t}" for t in tasks))
            ai_mode = self._get_ai_mode(context)

            if context.agent_config.use_template_generation:
                code = generate_fast_template_scene("；".join(str(task) for task in tasks))
            else:
                try:
                    _, code = generate_manim_code(
                        settings=context.ai_settings,
                        mode=ai_mode,
                        prompt=prompt,
                        previous_code="",
                        timeout=context.agent_config.ai_timeout,
                        agent_config=context.agent_config,
                        metrics=getattr(context, "metrics", None),
                        provider_registry=getattr(context, "provider_registry", None),
                    )
                except Exception:
                    if not context.agent_config.optimize_for_speed:
                        raise
                    code = generate_fast_template_scene("；".join(str(task) for task in tasks))

            code = sanitize_code(code)
            if context.agent_config.optimize_for_speed:
                from src.services.code_optimizer import optimize_manim_code_for_speed

                code = optimize_manim_code_for_speed(code)
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
            from src.services.ai_clients import generate_manim_code, sanitize_code
            from src.services.template_generator import generate_fast_template_scene

            prompt = CODER_PROMPT_REPAIR.format(
                code=context.current_code,
                prompt=context.prompt,
                feedback=feedback,
                marker=SECTION_MARKER,
            )

            ai_mode = self._get_ai_mode(context)
            if context.agent_config.use_template_generation:
                code = generate_fast_template_scene(context.prompt)
            else:
                _, code = generate_manim_code(
                    settings=context.ai_settings,
                    mode=ai_mode,
                    prompt=prompt,
                    previous_code="",
                    timeout=context.agent_config.ai_timeout,
                    agent_config=context.agent_config,
                    metrics=getattr(context, "metrics", None),
                    provider_registry=getattr(context, "provider_registry", None),
                )

            code = sanitize_code(code)
            if context.agent_config.optimize_for_speed:
                from src.services.code_optimizer import optimize_manim_code_for_speed

                code = optimize_manim_code_for_speed(code)
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
