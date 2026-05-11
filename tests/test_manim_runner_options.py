from __future__ import annotations

from pathlib import Path

from src.services.config import RenderSettings
from src.services.manim_runner import build_manim_command


def test_build_manim_command_can_disable_section_output(tmp_path: Path) -> None:
    command = build_manim_command(
        script_path=tmp_path / "scene.py",
        class_name="SceneA",
        settings=RenderSettings(width=320, height=180, fps=8, quality="l", save_sections=False),
        output_dir=tmp_path,
    )

    assert "--save_sections" not in command
    assert "-r" in command
    assert "320,180" in command
    assert "--fps" in command
    assert "8" in command


def test_build_manim_command_keeps_section_output_by_default(tmp_path: Path) -> None:
    command = build_manim_command(
        script_path=tmp_path / "scene.py",
        class_name="SceneA",
        settings=RenderSettings(width=640, height=360, fps=15, quality="l"),
        output_dir=tmp_path,
    )

    assert "--save_sections" in command
