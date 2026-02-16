"""Tests for MessageIntake — centralized message entry point."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.homeclaw.channels.intake import MessageIntake
from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.core.events import (
    CompletionEvent,
    ErrorEvent,
    StatusEvent,
    TextEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockHass:
    """Minimal mock HomeAssistant for unit tests."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}


def _make_mock_agent(
    *,
    process_query_return: dict | None = None,
    stream_events: list | None = None,
) -> MagicMock:
    """Build a mock HomeclawAgent with controllable behaviour."""
    agent = MagicMock()
    agent.provider_name = "openai"

    # Non-streaming
    if process_query_return is None:
        process_query_return = {"success": True, "answer": "Hello from AI"}
    agent.process_query = AsyncMock(return_value=process_query_return)

    # Streaming — return an async generator that yields given events
    if stream_events is None:
        stream_events = [
            TextEvent(content="Hello "),
            TextEvent(content="world"),
            CompletionEvent(messages=[]),
        ]

    async def _stream(*_args: Any, **_kwargs: Any):
        for ev in stream_events:
            yield ev

    agent.stream_query = _stream

    return agent


def _setup_hass_with_agent(
    hass: MockHass,
    agent: MagicMock,
    provider: str = "openai",
) -> None:
    """Register a mock agent in hass.data."""
    hass.data[DOMAIN] = {"agents": {provider: agent}}


# ---------------------------------------------------------------------------
# Tests: _get_agent
# ---------------------------------------------------------------------------


class TestGetAgent:
    """Tests for MessageIntake._get_agent resolution."""

    def test_returns_agent_by_provider_name(self) -> None:
        hass = MockHass()
        agent = _make_mock_agent()
        _setup_hass_with_agent(hass, agent, "gemini")

        intake = MessageIntake(hass)
        resolved = intake._get_agent("gemini")
        assert resolved is agent

    def test_falls_back_to_first_agent_when_provider_is_none(self) -> None:
        hass = MockHass()
        agent = _make_mock_agent()
        _setup_hass_with_agent(hass, agent, "openai")

        intake = MessageIntake(hass)
        resolved = intake._get_agent(None)
        assert resolved is agent

    def test_falls_back_to_first_agent_when_provider_not_found(self) -> None:
        hass = MockHass()
        agent = _make_mock_agent()
        _setup_hass_with_agent(hass, agent, "openai")

        intake = MessageIntake(hass)
        resolved = intake._get_agent("nonexistent")
        assert resolved is agent

    def test_raises_when_no_agents_configured(self) -> None:
        hass = MockHass()
        hass.data[DOMAIN] = {"agents": {}}

        intake = MessageIntake(hass)
        with pytest.raises(HomeAssistantError, match="No AI agent configured"):
            intake._get_agent(None)

    def test_raises_when_domain_data_missing(self) -> None:
        hass = MockHass()

        intake = MessageIntake(hass)
        with pytest.raises(HomeAssistantError, match="No AI agent configured"):
            intake._get_agent(None)

    def test_selects_correct_agent_among_multiple(self) -> None:
        hass = MockHass()
        agent_a = _make_mock_agent()
        agent_b = _make_mock_agent()
        hass.data[DOMAIN] = {"agents": {"openai": agent_a, "gemini": agent_b}}

        intake = MessageIntake(hass)
        assert intake._get_agent("gemini") is agent_b
        assert intake._get_agent("openai") is agent_a


# ---------------------------------------------------------------------------
# Tests: process_message (non-streaming)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestProcessMessage:
    """Tests for MessageIntake.process_message (non-streaming)."""

    async def test_delegates_to_agent_process_query(self) -> None:
        hass = MockHass()
        agent = _make_mock_agent(
            process_query_return={"success": True, "answer": "Test answer"}
        )
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        result = await intake.process_message(
            "turn on lights",
            user_id="user123",
            session_id="session-abc",
        )

        assert result["success"] is True
        assert result["answer"] == "Test answer"
        agent.process_query.assert_awaited_once()

    async def test_passes_all_kwargs_through(self) -> None:
        hass = MockHass()
        agent = _make_mock_agent()
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        await intake.process_message(
            "hello",
            user_id="u1",
            session_id="s1",
            provider="openai",
            model="gpt-4o",
            debug=True,
            conversation_history=[{"role": "user", "content": "hi"}],
        )

        call_kwargs = agent.process_query.call_args
        assert call_kwargs.kwargs["user_id"] == "u1"
        assert call_kwargs.kwargs["session_id"] == "s1"
        assert call_kwargs.kwargs["debug"] is True
        assert call_kwargs.kwargs["model"] == "gpt-4o"
        assert call_kwargs.kwargs["provider"] == "openai"

    async def test_uses_specific_provider(self) -> None:
        hass = MockHass()
        agent_a = _make_mock_agent(
            process_query_return={"success": True, "answer": "from A"}
        )
        agent_b = _make_mock_agent(
            process_query_return={"success": True, "answer": "from B"}
        )
        hass.data[DOMAIN] = {"agents": {"openai": agent_a, "gemini": agent_b}}

        intake = MessageIntake(hass)
        result = await intake.process_message(
            "hello",
            user_id="u1",
            provider="gemini",
        )
        assert result["answer"] == "from B"

    async def test_error_result_propagated(self) -> None:
        hass = MockHass()
        agent = _make_mock_agent(
            process_query_return={"success": False, "error": "Rate limited"}
        )
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        result = await intake.process_message("hello", user_id="u1")
        assert result["success"] is False
        assert result["error"] == "Rate limited"


# ---------------------------------------------------------------------------
# Tests: process_message_stream (streaming)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestProcessMessageStream:
    """Tests for MessageIntake.process_message_stream (streaming)."""

    async def test_yields_text_events(self) -> None:
        hass = MockHass()
        events = [
            TextEvent(content="Hello "),
            TextEvent(content="world"),
            CompletionEvent(messages=[]),
        ]
        agent = _make_mock_agent(stream_events=events)
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        collected = []
        async for event in intake.process_message_stream(
            "hello", user_id="u1", session_id="s1"
        ):
            collected.append(event)

        assert len(collected) == 3
        assert collected[0].type == "text"
        assert collected[0].content == "Hello "
        assert collected[1].content == "world"
        assert collected[2].type == "complete"

    async def test_yields_status_events(self) -> None:
        hass = MockHass()
        events = [
            StatusEvent(message="Calling tool..."),
            TextEvent(content="Done"),
            CompletionEvent(messages=[]),
        ]
        agent = _make_mock_agent(stream_events=events)
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        collected = []
        async for event in intake.process_message_stream(
            "do something", user_id="u1", session_id="s1"
        ):
            collected.append(event)

        assert collected[0].type == "status"
        assert collected[0].message == "Calling tool..."

    async def test_yields_error_event(self) -> None:
        hass = MockHass()
        events = [
            TextEvent(content="partial"),
            ErrorEvent(message="Provider timeout"),
        ]
        agent = _make_mock_agent(stream_events=events)
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        collected = []
        async for event in intake.process_message_stream(
            "hello", user_id="u1", session_id="s1"
        ):
            collected.append(event)

        assert collected[-1].type == "error"
        assert collected[-1].message == "Provider timeout"

    async def test_raises_when_no_agent(self) -> None:
        hass = MockHass()
        hass.data[DOMAIN] = {"agents": {}}

        intake = MessageIntake(hass)
        with pytest.raises(HomeAssistantError, match="No AI agent configured"):
            async for _ in intake.process_message_stream(
                "hello", user_id="u1", session_id="s1"
            ):
                pass

    async def test_passes_channel_source(self) -> None:
        """Verify channel_source is forwarded to agent.stream_query."""
        hass = MockHass()
        captured_kwargs: dict[str, Any] = {}

        async def _capturing_stream(*args: Any, **kwargs: Any):
            captured_kwargs.update(kwargs)
            yield CompletionEvent(messages=[])

        agent = _make_mock_agent()
        agent.stream_query = _capturing_stream
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        async for _ in intake.process_message_stream(
            "hello",
            user_id="u1",
            session_id="s1",
            channel_source="telegram",
        ):
            pass

        assert captured_kwargs["channel_source"] == "telegram"

    async def test_passes_attachments(self) -> None:
        """Verify attachments are forwarded to agent.stream_query."""
        hass = MockHass()
        captured_kwargs: dict[str, Any] = {}

        async def _capturing_stream(*args: Any, **kwargs: Any):
            captured_kwargs.update(kwargs)
            yield CompletionEvent(messages=[])

        agent = _make_mock_agent()
        agent.stream_query = _capturing_stream
        _setup_hass_with_agent(hass, agent)

        fake_attachments = [MagicMock(filename="photo.jpg")]
        intake = MessageIntake(hass)
        async for _ in intake.process_message_stream(
            "look at this",
            user_id="u1",
            session_id="s1",
            attachments=fake_attachments,
        ):
            pass

        assert captured_kwargs["attachments"] == fake_attachments

    async def test_empty_stream(self) -> None:
        """Handle agents that yield zero events."""
        hass = MockHass()
        agent = _make_mock_agent(stream_events=[])
        _setup_hass_with_agent(hass, agent)

        intake = MessageIntake(hass)
        collected = []
        async for event in intake.process_message_stream(
            "hello", user_id="u1", session_id="s1"
        ):
            collected.append(event)

        assert collected == []
