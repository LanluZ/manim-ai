# tests/test_core_events.py
"""核心事件模块单元测试"""

from core.events import Event, EventType


def test_event_creation():
    """测试事件创建"""
    event = Event(
        type=EventType.TASK_RECEIVED,
        payload={"prompt": "测试"},
        correlation_id="test-123",
    )
    assert event.type == EventType.TASK_RECEIVED
    assert event.payload == {"prompt": "测试"}
    assert event.correlation_id == "test-123"


def test_event_type_enum():
    """测试事件类型枚举"""
    assert EventType.TASK_RECEIVED.value == "task_received"
    assert EventType.CODE_GENERATED.value == "code_generated"
    assert EventType.RENDER_COMPLETED.value == "render_completed"
    assert EventType.TASK_COMPLETED.value == "task_completed"
    assert EventType.TASK_FAILED.value == "task_failed"
