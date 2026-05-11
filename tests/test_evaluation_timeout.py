from __future__ import annotations

import asyncio
from pathlib import Path

from src.evaluation.dataset import PromptCase
from src.evaluation.runner import Variant, run_cases
from src.services.config import AgentConfig, AISettings, RenderSettings
from src.services.providers import ProviderRegistry, StaticProvider


def test_run_cases_records_timeout_when_case_exceeds_limit(monkeypatch, tmp_path: Path) -> None:
    asyncio.run(_run_cases_records_timeout_when_case_exceeds_limit(monkeypatch, tmp_path))


async def _run_cases_records_timeout_when_case_exceeds_limit(monkeypatch, tmp_path: Path) -> None:
    async def slow_run_one_case(**_kwargs):
        await asyncio.sleep(1)

    monkeypatch.setattr("src.evaluation.runner._run_one_case", slow_run_one_case)
    registry = ProviderRegistry()
    registry.register(StaticProvider("deepseek", "from manim import *"))

    records = await run_cases(
        cases=[PromptCase(id="p1", category="test", prompt="test")],
        variants=[Variant("baseline", AgentConfig(), registry)],
        ai_settings=AISettings("", "", "", "", ""),
        render_settings=RenderSettings(width=320, height=180, fps=8, quality="l"),
        ai_mode="deepseek",
        output_root=tmp_path,
        case_timeout=0.01,
    )

    assert len(records) == 1
    assert records[0].success is False
    assert records[0].error == "case_timeout(0.01s)"
