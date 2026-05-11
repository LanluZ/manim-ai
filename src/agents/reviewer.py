# agents/reviewer.py
from __future__ import annotations

import ast
import json

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
        agent_config = getattr(context, "agent_config", None)
        enable_static_review = getattr(agent_config, "enable_static_review", True)

        static_result = {"approved": True, "issues": []}
        if enable_static_review:
            static_result = self._static_review(code)

        if not static_result["approved"]:
            issues = [str(issue) for issue in static_result["issues"]]
            context.review_feedback = "; ".join(issues)
            self._log(context, f"静态审查不通过: {context.review_feedback}")
            return Event(
                type=EventType.CODE_NEEDS_FIX,
                payload={"feedback": context.review_feedback},
                correlation_id=event.correlation_id,
            )

        if enable_static_review:
            self._log(context, "静态审查通过，进行AI审查...")
        else:
            self._log(context, "静态审查已关闭，进行AI审查...")

        # AI审查（可选）
        try:
            ai_result = await self._ai_review(code, context)
            if not ai_result.get("approved", True):
                feedback = ai_result.get("suggested_fix", "代码需要修复")
                issues = [str(issue) for issue in ai_result.get("issues", [])]
                if issues:
                    feedback = f"{feedback} | 问题: {'; '.join(issues)}"
                context.review_feedback = feedback
                self._log(context, f"AI审查不通过: {feedback}")
                return Event(
                    type=EventType.CODE_NEEDS_FIX,
                    payload={"feedback": feedback},
                    correlation_id=event.correlation_id,
                )
        except Exception as exc:
            # AI审查失败不影响流程，静态检查已通过
            self._log(context, f"AI审查异常（跳过）: {exc}")

        self._log(context, "审查通过")
        return Event(
            type=EventType.CODE_APPROVED,
            payload={"code": code},
            correlation_id=event.correlation_id,
        )

    def _log(self, context: TaskContext, message: str) -> None:
        """输出审查日志"""
        callback = getattr(context, "progress_callback", None)
        if callback:
            callback(f"[Reviewer] {message}")

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
        from src.services.ai_clients import call_ai

        prompt = REVIEWER_PROMPT.format(code=code)
        ai_mode = self._get_ai_mode(context)

        response = call_ai(
            settings=context.ai_settings,
            mode=ai_mode,
            prompt=prompt,
            timeout=context.agent_config.ai_timeout // 2,
            agent_config=context.agent_config,
            metrics=getattr(context, "metrics", None),
            provider_registry=getattr(context, "provider_registry", None),
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
