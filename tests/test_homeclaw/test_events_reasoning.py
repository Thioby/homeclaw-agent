"""Tests for ReasoningEvent dataclass."""

from custom_components.homeclaw.core.events import AgentEvent, ReasoningEvent


def test_reasoning_event_carries_content() -> None:
    event = ReasoningEvent(content="thinking out loud")
    assert event.content == "thinking out loud"
    assert event.type == "reasoning"


def test_reasoning_event_is_agent_event() -> None:
    event = ReasoningEvent(content="x")
    assert isinstance(event, AgentEvent)
