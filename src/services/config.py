from __future__ import annotations

from dataclasses import dataclass, field
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
    save_sections: bool = True


@dataclass(frozen=True)
class AISettings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    gemini_api_key: str
    gemini_model: str


@dataclass(frozen=True)
class AgentConfig:
    """Agent 配置"""
    max_iterations: int = 5      # Coder-Reviewer 最大迭代次数
    ai_timeout: int = 60         # AI 调用超时（秒）
    render_timeout: int = 600    # 渲染超时（秒）
    temperature: float = 0.2     # AI 生成温度
    enable_reviewer: bool = True
    enable_static_review: bool = True
    enable_auto_fix: bool = True
    provider_fallback_order: tuple[str, ...] = ("deepseek", "gemini")
    max_provider_retries: int = 1
    provider_prices_per_1k_tokens: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "deepseek": (0.00014, 0.00028),
            "gemini": (0.000075, 0.0003),
        }
    )
