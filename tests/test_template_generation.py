from __future__ import annotations

from src.services.template_generator import generate_fast_template_scene


def test_generate_fast_template_scene_returns_valid_scene_code() -> None:
    code = generate_fast_template_scene('plot "sin"')

    assert "from manim import *" in code
    assert "class FastPreviewScene(Scene)" in code
    assert "MathTex" not in code
    assert "run_time=0.2" in code
