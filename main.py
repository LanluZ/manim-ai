# main.py
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """统一入口：根据参数选择CLI或GUI模式"""
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "jobs").mkdir(parents=True, exist_ok=True)

    if "--cli" in sys.argv:
        # CLI模式：移除--cli参数后传递给CLI解析器
        sys.argv.remove("--cli")
        from src.cli.main import main as cli_main
        cli_main()
    else:
        # GUI模式（默认）
        from src.services.database import Database
        from src.gui.main_window import run_app

        db = Database(data_dir / "manimai.db")
        jobs_dir = data_dir / "jobs"
        run_app(db, jobs_dir)


if __name__ == "__main__":
    main()
