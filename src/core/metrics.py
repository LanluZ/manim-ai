from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.providers import ProviderCallRecord


@dataclass
class RenderAttempt:
    success: bool
    duration_seconds: float
    error: str = ""


@dataclass
class TaskMetrics:
    """Per-task runtime metrics used by evaluation runs."""

    started_at: float = field(default_factory=perf_counter)
    ended_at: float | None = None
    provider_calls: list[ProviderCallRecord] = field(default_factory=list)
    render_attempts: list[RenderAttempt] = field(default_factory=list)
    first_render_success: bool | None = None
    final_success: bool = False

    def finish(self, success: bool) -> None:
        self.ended_at = perf_counter()
        self.final_success = success

    @property
    def elapsed_seconds(self) -> float:
        end = self.ended_at if self.ended_at is not None else perf_counter()
        return end - self.started_at

    @property
    def estimated_api_cost_usd(self) -> float:
        return sum(call.estimated_cost_usd for call in self.provider_calls)

    @property
    def repair_rounds(self) -> int:
        return max(0, len(self.render_attempts) - 1)


def success_rate(values: list[bool]) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value) / len(values)
