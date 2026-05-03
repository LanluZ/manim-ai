# gui/main.py
from __future__ import annotations

from pathlib import Path

from app.database import Database
from app.ui_main import run_app


def run_gui() -> None:
    """运行GUI应用"""
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    db = Database(data_dir / "manimai.db")

    jobs_dir = data_dir / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    run_app(db, jobs_dir)


if __name__ == "__main__":
    run_gui()
