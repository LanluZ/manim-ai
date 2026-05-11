from __future__ import annotations

from src.services.code_optimizer import optimize_manim_code_for_speed


def test_optimize_manim_code_replaces_latex_and_shortens_animation_runtime() -> None:
    code = """from manim import *

class Demo(Scene):
    def construct(self):
        axes = Axes(axis_config={"include_numbers": True})
        label = MathTex("y = \\\\sin(x)")
        self.play(Create(axes), Write(label), run_time=2)
        self.wait(1)
"""

    optimized = optimize_manim_code_for_speed(code)

    assert "MathTex" not in optimized
    assert "Text" in optimized
    assert "'include_numbers': False" in optimized or '"include_numbers": False' in optimized
    assert "run_time=0.25" in optimized
    assert "self.wait(0.1)" in optimized
