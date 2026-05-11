from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.agents.coder import CoderAgent
from src.agents.planner import PlannerAgent
from src.agents.renderer import RendererAgent
from src.agents.reviewer import ReviewerAgent
from src.core.coordinator import Coordinator
from src.core.events import EventType
from src.evaluation.dataset import DEFAULT_DATASET, PromptCase, load_prompt_cases
from src.evaluation.reporting import PromptRunRecord, aggregate_records, write_reports
from src.services.config import AISettings, AgentConfig, RenderSettings
from src.services.manim_runner import RenderResult
from src.services.providers import FaultyProvider, ProviderRegistry, StaticProvider


VALID_FAKE_CODE = """from manim import *

class EvaluationScene(Scene):
    def construct(self):
        title = Text("Manimai evaluation", font_size=36)
        self.play(Write(title))
        self.wait(0.1)
"""


@dataclass(frozen=True)
class Variant:
    name: str
    config: AgentConfig
    provider_registry: ProviderRegistry | None = None


def default_variants(base_config: AgentConfig, *, fake_providers: bool) -> list[Variant]:
    return [
        Variant("baseline", base_config, _provider_registry(fake_providers)),
        Variant("no_reviewer", replace(base_config, enable_reviewer=False), _provider_registry(fake_providers)),
        Variant("no_static_review", replace(base_config, enable_static_review=False), _provider_registry(fake_providers)),
        Variant("no_auto_fix", replace(base_config, enable_auto_fix=False), _provider_registry(fake_providers)),
        Variant(
            "deepseek_timeout",
            base_config,
            _provider_registry(fake_providers, faulty_provider="deepseek", error_kind="timeout"),
        ),
        Variant(
            "gemini_error",
            base_config,
            _provider_registry(fake_providers, faulty_provider="gemini", error_kind="server"),
        ),
    ]


async def run_cases(
    cases: list[PromptCase],
    variants: list[Variant],
    ai_settings: AISettings,
    render_settings: RenderSettings,
    ai_mode: str,
    output_root: Path,
    fake_render: bool = False,
) -> list[PromptRunRecord]:
    records: list[PromptRunRecord] = []
    with _fake_render_enabled(fake_render):
        for variant in variants:
            for case in cases:
                records.append(
                    await _run_one_case(
                        case=case,
                        variant=variant,
                        ai_settings=ai_settings,
                        render_settings=render_settings,
                        ai_mode=ai_mode,
                        output_root=output_root,
                    )
                )
    return records


async def _run_one_case(
    case: PromptCase,
    variant: Variant,
    ai_settings: AISettings,
    render_settings: RenderSettings,
    ai_mode: str,
    output_root: Path,
) -> PromptRunRecord:
    job_dir = output_root / "jobs" / variant.name / case.id
    job_dir.mkdir(parents=True, exist_ok=True)
    agents = [PlannerAgent(), CoderAgent(), ReviewerAgent(), RendererAgent()]
    coordinator = Coordinator(
        agents=agents,
        ai_settings=ai_settings,
        render_settings=render_settings,
        agent_config=variant.config,
        ai_mode=ai_mode,
        provider_registry=variant.provider_registry,
    )
    result = await coordinator.run(case.prompt, output_root, job_dir)
    metrics = result.metrics
    repair_rounds = sum(1 for event in result.events if event.type == EventType.CODE_NEEDS_FIX)
    provider_sequence = [call.provider for call in metrics.provider_calls]
    first_render_success = bool(metrics.first_render_success) if metrics.first_render_success is not None else False
    return PromptRunRecord(
        variant=variant.name,
        prompt_id=case.id,
        category=case.category,
        success=result.success,
        first_render_success=first_render_success,
        repair_rounds=repair_rounds,
        elapsed_seconds=metrics.elapsed_seconds,
        estimated_api_cost_usd=metrics.estimated_api_cost_usd,
        provider_sequence=provider_sequence,
        error=result.error,
    )


def _provider_registry(
    fake_providers: bool,
    faulty_provider: str | None = None,
    error_kind: str = "server",
) -> ProviderRegistry | None:
    if not fake_providers and faulty_provider is None:
        return None

    registry = ProviderRegistry()
    for provider in ("deepseek", "gemini"):
        if provider == faulty_provider:
            registry.register(FaultyProvider(provider, error_kind=error_kind))
        else:
            registry.register(StaticProvider(provider, VALID_FAKE_CODE))
    return registry


@contextmanager
def _fake_render_enabled(enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    from src.agents import renderer as renderer_module

    original = renderer_module.render_manim_scene

    def fake_render_manim_scene(
        cumulative_code: str,
        settings: RenderSettings,
        job_dir: Path,
        logger: object | None = None,
    ) -> RenderResult:
        script_path = job_dir / "scene.py"
        script_path.write_text(cumulative_code, encoding="utf-8")
        video_path = job_dir / "render.mp4"
        video_path.write_bytes(b"fake mp4")
        return RenderResult(
            video_path=video_path,
            script_path=script_path,
            class_name="EvaluationScene",
            section_videos=[],
        )

    renderer_module.render_manim_scene = fake_render_manim_scene
    try:
        yield
    finally:
        renderer_module.render_manim_scene = original


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Manimai math animation evaluation")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("data/evaluation/runs"))
    parser.add_argument("--ai-mode", choices=["deepseek", "gemini"], default="deepseek")
    parser.add_argument("--fake-providers", action="store_true")
    parser.add_argument("--fake-render", action="store_true")
    parser.add_argument("--variant", action="append", default=None, help="Run one or more named variants")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--quality", default="l", choices=["l", "m", "h", "k"])
    parser.add_argument("--deepseek-key", default="")
    parser.add_argument("--deepseek-base", default="https://api.deepseek.com")
    parser.add_argument("--deepseek-model", default="deepseek-chat")
    parser.add_argument("--gemini-key", default="")
    parser.add_argument("--gemini-model", default="gemini-1.5-flash")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_prompt_cases(args.dataset, args.limit)
    ai_settings = AISettings(
        deepseek_api_key=args.deepseek_key,
        deepseek_base_url=args.deepseek_base,
        deepseek_model=args.deepseek_model,
        gemini_api_key=args.gemini_key,
        gemini_model=args.gemini_model,
    )
    render_settings = RenderSettings(
        width=args.width,
        height=args.height,
        fps=args.fps,
        quality=args.quality,
    )
    base_config = AgentConfig()
    variants = default_variants(base_config, fake_providers=args.fake_providers)
    if args.variant:
        wanted = set(args.variant)
        variants = [variant for variant in variants if variant.name in wanted]
    run_dir = args.output_root / datetime.now().strftime("%Y%m%d-%H%M%S")
    records = asyncio.run(
        run_cases(
            cases=cases,
            variants=variants,
            ai_settings=ai_settings,
            render_settings=render_settings,
            ai_mode=args.ai_mode,
            output_root=run_dir,
            fake_render=args.fake_render,
        )
    )
    json_path, csv_path = write_reports(records, run_dir)
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    for variant, aggregate in aggregate_records(records).items():
        print(
            f"{variant}: first={aggregate['first_render_success_rate']:.2%} "
            f"final={aggregate['final_success_rate']:.2%} "
            f"repairs={aggregate['average_repair_rounds']:.2f} "
            f"elapsed={aggregate['average_elapsed_seconds']:.2f}s "
            f"cost=${aggregate['average_api_cost_usd']:.6f}"
        )


if __name__ == "__main__":
    main()
