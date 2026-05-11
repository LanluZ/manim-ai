from __future__ import annotations

import pytest

from src.services.config import AgentConfig, AISettings
from src.services.providers import ProviderCallRecord


def _settings() -> AISettings:
    return AISettings(
        deepseek_api_key="deepseek-key",
        deepseek_base_url="https://api.deepseek.test",
        deepseek_model="deepseek-test",
        gemini_api_key="gemini-key",
        gemini_model="gemini-test",
    )


def test_provider_router_retries_primary_then_falls_back() -> None:
    from src.services.providers import (
        FaultyProvider,
        ProviderRegistry,
        ProviderRequest,
        ProviderRouter,
        StaticProvider,
    )

    registry = ProviderRegistry()
    registry.register(FaultyProvider("deepseek", error_kind="timeout"))
    registry.register(StaticProvider("gemini", content="ok from gemini"))
    config = AgentConfig(
        provider_fallback_order=("deepseek", "gemini"),
        max_provider_retries=1,
    )
    records: list[ProviderCallRecord] = []

    router = ProviderRouter(registry, config)
    response = router.complete(
        ProviderRequest(prompt="hello", system_prompt="system", timeout=1),
        settings=_settings(),
        preferred_provider="deepseek",
        records=records,
    )

    assert response.provider == "gemini"
    assert response.content == "ok from gemini"
    assert [record.provider for record in records] == ["deepseek", "deepseek", "gemini"]
    assert records[0].success is False
    assert records[0].error_kind == "timeout"
    assert records[-1].success is True


def test_provider_router_estimates_cost_for_successful_call() -> None:
    from src.services.providers import (
        ProviderRegistry,
        ProviderRequest,
        ProviderRouter,
        StaticProvider,
    )

    registry = ProviderRegistry()
    registry.register(StaticProvider("deepseek", content="from manim import *"))
    config = AgentConfig(
        provider_fallback_order=("deepseek",),
        provider_prices_per_1k_tokens={"deepseek": (0.1, 0.2)},
    )
    records: list[ProviderCallRecord] = []

    response = ProviderRouter(registry, config).complete(
        ProviderRequest(prompt="plot a sine wave", system_prompt="", timeout=1),
        settings=_settings(),
        preferred_provider="deepseek",
        records=records,
    )

    assert response.provider == "deepseek"
    assert response.estimated_cost_usd > 0
    assert records[0].estimated_cost_usd == response.estimated_cost_usd


def test_provider_router_raises_last_error_when_all_providers_fail() -> None:
    from src.services.providers import (
        FaultyProvider,
        ProviderError,
        ProviderRegistry,
        ProviderRequest,
        ProviderRouter,
    )

    registry = ProviderRegistry()
    registry.register(FaultyProvider("deepseek", error_kind="server"))
    registry.register(FaultyProvider("gemini", error_kind="invalid_response"))
    config = AgentConfig(
        provider_fallback_order=("deepseek", "gemini"),
        max_provider_retries=0,
    )

    with pytest.raises(ProviderError) as exc_info:
        ProviderRouter(registry, config).complete(
            ProviderRequest(prompt="hello", system_prompt="", timeout=1),
            settings=_settings(),
            preferred_provider="deepseek",
            records=[],
        )

    assert exc_info.value.provider == "gemini"
    assert exc_info.value.kind == "invalid_response"
