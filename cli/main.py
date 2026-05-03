# cli/main.py
from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

from app.config import AISettings, RenderSettings
from app.database import Database
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.renderer import RendererAgent
from core.coordinator import Coordinator


class CLIProgressHandler:
    """CLI 进度处理器"""

    def __call__(self, message: str) -> None:
        print(f"[Manimai] {message}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Manimai - AI 驱动的 Manim 动画生成器")
    parser.add_argument("prompt", help="动画描述")
    parser.add_argument("-w", "--workspace", default="default", help="工作区名称")
    parser.add_argument("--width", type=int, default=1920, help="输出宽度")
    parser.add_argument("--height", type=int, default=1080, help="输出高度")
    parser.add_argument("--fps", type=int, default=30, help="帧率")
    parser.add_argument("-q", "--quality", default="k", choices=["l", "m", "h", "k"], help="质量")
    parser.add_argument("--ai-mode", default="deepseek", choices=["deepseek", "gemini"], help="AI模式")
    return parser.parse_args()


def load_settings(args: argparse.Namespace, db: Database) -> tuple[AISettings, RenderSettings]:
    """从数据库加载设置"""
    ai_settings = AISettings(
        deepseek_api_key=db.get_setting("deepseek_key", ""),
        deepseek_base_url=db.get_setting("deepseek_base", "https://api.deepseek.com"),
        deepseek_model=db.get_setting("deepseek_model", "deepseek-chat"),
        gemini_api_key=db.get_setting("gemini_key", ""),
        gemini_model=db.get_setting("gemini_model", "gemini-1.5-flash"),
    )

    render_settings = RenderSettings(
        width=args.width,
        height=args.height,
        fps=args.fps,
        quality=args.quality,
    )

    return ai_settings, render_settings


async def run_async(args: argparse.Namespace) -> int:
    """异步运行任务"""
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(data_dir / "manimai.db")

    ai_settings, render_settings = load_settings(args, db)

    jobs_dir = data_dir / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_dir = jobs_dir / args.workspace
    job_dir.mkdir(parents=True, exist_ok=True)

    agents = [
        PlannerAgent(),
        CoderAgent(),
        ReviewerAgent(),
        RendererAgent(),
    ]

    progress = CLIProgressHandler()
    coordinator = Coordinator(
        agents=agents,
        ai_settings=ai_settings,
        render_settings=render_settings,
        progress_callback=progress,
    )

    workspace_path = Path(args.workspace)
    result = await coordinator.run(
        prompt=args.prompt,
        workspace=workspace_path,
        job_dir=job_dir,
    )

    if result.success:
        print(f"\n[完成] 视频已生成: {result.video_path}")
        return 0
    else:
        print(f"\n[失败] {result.error}")
        return 1


def main() -> None:
    """CLI 入口"""
    args = parse_args()
    exit_code = asyncio.run(run_async(args))
    exit(exit_code)


if __name__ == "__main__":
    main()
