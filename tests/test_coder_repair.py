from __future__ import annotations

import asyncio
from pathlib import Path

from src.agents.coder import CoderAgent
from src.core.context import TaskContext
from src.core.events import Event, EventType
from src.services.ai_clients import sanitize_code
from src.services.config import AgentConfig, AISettings


def test_code_needs_fix_replaces_current_code_with_complete_fixed_scene(
    monkeypatch,
    tmp_path: Path,
) -> None:
    asyncio.run(_run_code_needs_fix_replaces_current_code_with_complete_fixed_scene(monkeypatch, tmp_path))


async def _run_code_needs_fix_replaces_current_code_with_complete_fixed_scene(
    monkeypatch,
    tmp_path: Path,
) -> None:
    context = TaskContext(prompt="plot sine and cosine", workspace=tmp_path, job_dir=tmp_path / "job")
    context.current_code = "from manim import *\n\nclass Broken(Scene):\n    def construct(self):\n        axes\n"
    context.agent_config = AgentConfig(max_iterations=2)  # type: ignore[attr-defined]
    context.ai_settings = AISettings("", "", "", "", "")  # type: ignore[attr-defined]
    context.ai_mode = "deepseek"  # type: ignore[attr-defined]

    fixed_code = (
        "from manim import *\n\n"
        "class Fixed(Scene):\n"
        "    def construct(self):\n"
        "        dot = Dot()\n"
        "        self.add(dot)\n"
    )

    def fake_generate_manim_code(**_kwargs):
        return "deepseek", fixed_code

    monkeypatch.setattr("src.services.ai_clients.generate_manim_code", fake_generate_manim_code)

    result = await CoderAgent().handle(
        Event(
            type=EventType.CODE_NEEDS_FIX,
            payload={"feedback": "渲染错误（可修复）: NameError"},
            correlation_id="cid",
        ),
        context,
    )

    assert result is not None
    assert result.type == EventType.CODE_GENERATED
    assert context.current_code == fixed_code
    assert "from manim import *" in context.current_code
    assert "class Fixed(Scene)" in context.current_code


def test_sanitize_code_extracts_python_from_mixed_streaming_response() -> None:
    response = """我们需要生成一个快速预览场景。

```python
from manim import *

class Demo(Scene):
    def construct(self):
        self.add(Text("ok"))
```
"""

    code = sanitize_code(response)

    assert code.startswith("from manim import *")
    assert "我们需要" not in code
    assert "class Demo(Scene)" in code
