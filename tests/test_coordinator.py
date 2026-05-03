# tests/test_coordinator.py
"""协调器模块单元测试"""

import pytest

from app.config import AISettings, RenderSettings, AgentConfig
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.renderer import RendererAgent
from core.coordinator import Coordinator
from core.events import EventType


def test_coordinator_creation():
    """测试协调器创建"""
    ai_settings = AISettings(
        deepseek_api_key="test",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
        gemini_api_key="",
        gemini_model="gemini-1.5-flash",
    )
    render_settings = RenderSettings(width=1920, height=1080, fps=30, quality="k")

    agents = [
        PlannerAgent(),
        CoderAgent(),
        ReviewerAgent(),
        RendererAgent(),
    ]

    coordinator = Coordinator(
        agents=agents,
        ai_settings=ai_settings,
        render_settings=render_settings,
    )

    assert len(coordinator.agents) == 4


def test_coordinator_agent_registration():
    """测试Agent注册"""
    ai_settings = AISettings(
        deepseek_api_key="test",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
        gemini_api_key="",
        gemini_model="gemini-1.5-flash",
    )
    render_settings = RenderSettings(width=1920, height=1080, fps=30, quality="k")

    agents = [
        PlannerAgent(),
        CoderAgent(),
        ReviewerAgent(),
        RendererAgent(),
    ]

    coordinator = Coordinator(
        agents=agents,
        ai_settings=ai_settings,
        render_settings=render_settings,
    )

    # 验证PlannerAgent注册了TASK_RECEIVED
    assert EventType.TASK_RECEIVED in coordinator.event_bus._subscribers
    # 验证CoderAgent注册了PLAN_CREATED
    assert EventType.PLAN_CREATED in coordinator.event_bus._subscribers
    # 验证ReviewerAgent注册了CODE_GENERATED
    assert EventType.CODE_GENERATED in coordinator.event_bus._subscribers
    # 验证RendererAgent注册了CODE_APPROVED
    assert EventType.CODE_APPROVED in coordinator.event_bus._subscribers


def test_agent_config_defaults():
    """测试AgentConfig默认值"""
    config = AgentConfig()
    assert config.max_iterations == 5
    assert config.ai_timeout == 60
    assert config.render_timeout == 600
    assert config.temperature == 0.2
