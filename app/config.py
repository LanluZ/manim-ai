from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Manimai"
DB_NAME = "manimai.db"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"
LOG_DIR = DATA_DIR / "logs"

DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_QUALITY = "k"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


@dataclass(frozen=True)
class RenderSettings:
    width: int
    height: int
    fps: int
    quality: str


@dataclass(frozen=True)
class AISettings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    gemini_api_key: str
    gemini_model: str
