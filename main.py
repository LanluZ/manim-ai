from pathlib import Path

from app.config import DATA_DIR, DB_NAME, JOBS_DIR
from app.database import Database
from app.ui_main import run_app


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = Database(DATA_DIR / DB_NAME)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    run_app(db, JOBS_DIR)


if __name__ == "__main__":
    main()
