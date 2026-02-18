from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import RenderSettings


@dataclass(frozen=True)
class RenderResult:
    """渲染结果：包含所有分段的视频文件"""
    video_path: Path
    script_path: Path
    class_name: str
    section_videos: list[Path]


class RenderError(RuntimeError):
    pass


SCENE_CLASS_RE = re.compile(r"class\s+(\w+)\s*\(\s*Scene\s*\)")


def extract_scene_class(code: str) -> str:
    match = SCENE_CLASS_RE.search(code)
    if not match:
        raise RenderError("未找到 Scene 子类，请检查 AI 输出")
    return match.group(1)


def write_cumulative_script(job_dir: Path, cumulative_code: str) -> Path:
    """写入累积的场景代码"""
    job_dir.mkdir(parents=True, exist_ok=True)
    script_path = job_dir / "scene.py"
    script_path.write_text(cumulative_code, encoding="utf-8")
    return script_path


def build_manim_command(
    script_path: Path,
    class_name: str,
    settings: RenderSettings,
    output_dir: Path,
) -> list[str]:
    return [
        "manim",
        "-q",
        settings.quality,
        "-r",
        f"{settings.width},{settings.height}",
        "--fps",
        str(settings.fps),
        "--format",
        "mp4",
        "--media_dir",
        str(output_dir),
        "--save_sections",
        str(script_path),
        class_name,
    ]


def run_manim(
    script_path: Path,
    class_name: str,
    settings: RenderSettings,
    output_dir: Path,
    timeout: int = 600,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = build_manim_command(script_path, class_name, settings, output_dir)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"Manim 渲染超时（{timeout}s）") from exc
    if result.returncode != 0:
        raise RenderError(result.stderr or result.stdout)

    candidates = list(output_dir.rglob("render.mp4"))
    if not candidates:
        candidates = list(output_dir.rglob("*.mp4"))
    if not candidates:
        raise RenderError("未找到渲染输出视频")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest


def find_section_videos(job_dir: Path, class_name: str) -> list[Path]:
    """查找分段视频文件"""
    sections_dir = job_dir / "videos" / "scene" / "1080p30" / "sections"
    if not sections_dir.exists():
        # fallback to other possible locations
        for quality_dir in job_dir.glob("videos/*/*/sections"):
            if quality_dir.exists():
                sections_dir = quality_dir
                break
    
    if not sections_dir.exists():
        return []
    
    # 查找所有分段视频，按名称排序
    section_files = list(sections_dir.glob("*.mp4"))
    return sorted(section_files, key=lambda p: p.name)


def render_manim_scene(
    cumulative_code: str,
    settings: RenderSettings,
    job_dir: Path,
    logger: Callable[[str], None] | None = None,
) -> RenderResult:
    """渲染累积的 manim 场景并返回分段视频"""
    class_name = extract_scene_class(cumulative_code)
    script_path = write_cumulative_script(job_dir, cumulative_code)
    if logger:
        logger(f"Scene: {class_name} | 脚本: {script_path}")
        command = build_manim_command(script_path, class_name, settings, job_dir)
        logger("Manim 命令: " + " ".join(command))
    
    video_path = run_manim(script_path, class_name, settings, job_dir)
    section_videos = find_section_videos(job_dir, class_name)
    
    if logger:
        logger(f"渲染完成: {video_path}")
        logger(f"分段视频数量: {len(section_videos)}")
    
    return RenderResult(
        video_path=video_path,
        script_path=script_path,
        class_name=class_name,
        section_videos=section_videos,
    )
