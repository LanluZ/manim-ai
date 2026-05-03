# agents/reviewer.py
from __future__ import annotations

import json
import ast

from src.core.agent import Agent
from src.core.context import TaskContext
from src.core.events import Event, EventType

REVIEWER_PROMPT = """审查以下 Manim 代码是否符合规范：

```python
{code}
```

规则：
1. 必须包含 from manim import *
2. 只能定义一个 Scene 子类
3. 语法正确，可直接运行
4. 每个分段不超过 3 秒
5. 不使用 FadeOut

输出 JSON 格式：
{{"approved": true/false, "issues": ["问题1", "问题2"], "suggested_fix": "修复建议"}}"""


class ReviewerAgent(Agent):
    """代码审查Agent：检查代码质量，决定是否通过"""

    name = "Reviewer"
    listens_to = [EventType.CODE_GENERATED]

    async def handle(self, event: Event, context: TaskContext) -> Event:
        """审查代码"""
        code = event.payload["code"]

        static_result = self._static_review(code)

        if not static_result["approved"]:
            context.review_feedback = "; ".join(static_result["issues"])
            return Event(
                type=EventType.CODE_NEEDS_FIX,
                payload={"feedback": context.review_feedback},
                correlation_id=event.correlation_id,
            )

        # AI审查（可选）
        try:
            ai_result = await self._ai_review(code, context)
            if not ai_result.get("approved", True):
                feedback = ai_result.get("suggested_fix", "代码需要修复")
                context.review_feedback = feedback
                return Event(
                    type=EventType.CODE_NEEDS_FIX,
                    payload={"feedback": feedback},
                    correlation_id=event.correlation_id,
                )
        except Exception as exc:
            # AI审查失败不影响流程，静态检查已通过
            pass

        return Event(
            type=EventType.CODE_APPROVED,
            payload={"code": code},
            correlation_id=event.correlation_id,
        )

    def _static_review(self, code: str) -> dict:
        """静态代码审查"""
        issues = []

        if "from manim import" not in code:
            issues.append("缺少 'from manim import *'")

        if "class " not in code or "(Scene)" not in code:
            issues.append("必须定义 Scene 子类")

        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"语法错误: {e}")

        return {"approved": len(issues) == 0, "issues": issues}

    async def _ai_review(self, code: str, context: TaskContext) -> dict:
        """AI增强审查"""
        from src.services.ai_clients import generate_manim_code

        prompt = REVIEWER_PROMPT.format(code=code)
        ai_mode = self._get_ai_mode(context)

        _, response = generate_manim_code(
            settings=context.ai_settings,
            mode=ai_mode,
            prompt=prompt,
            previous_code="",
            timeout=context.agent_config.ai_timeout // 2,
        )

        try:
            if "```" in response:
                parts = response.split("```")
                for part in parts:
                    if part.strip().startswith("json"):
                        response = part.strip()[4:]
                        break
            return json.loads(response)
        except json.JSONDecodeError:
            return {"approved": True}
