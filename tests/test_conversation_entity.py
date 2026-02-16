from unittest.mock import MagicMock
import pytest
from custom_components.homeclaw.conversation import HomeclawConversationEntity
from custom_components.homeclaw.core.events import (
    TextEvent,
    StatusEvent,
    ErrorEvent,
    CompletionEvent,
    ToolCallEvent,
    ToolResultEvent,
)

# Mock constants
DOMAIN = "homeclaw"


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.hass = MagicMock()
    return agent


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.data = {"ai_provider": "test_provider"}
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def entity(mock_config_entry, mock_agent):
    return HomeclawConversationEntity(mock_config_entry, "test_provider", mock_agent)


@pytest.mark.asyncio
async def test_transform_stream_text(entity):
    """Test transforming a simple text stream."""

    async def mock_stream():
        yield TextEvent(content="Hello")
        yield TextEvent(content=" World")
        yield CompletionEvent(messages=[])

    chat_log = MagicMock()

    deltas = []
    async for delta in entity._transform_provider_stream(mock_stream(), chat_log):
        deltas.append(delta)

    # Verify deltas — implementation yields content-only dicts (no role prefix)
    assert len(deltas) == 2
    assert deltas[0] == {"content": "Hello"}
    assert deltas[1] == {"content": " World"}


@pytest.mark.asyncio
async def test_transform_stream_tool_flow(entity):
    """Test transforming a stream with tool calls."""

    async def mock_stream():
        yield StatusEvent(message="Thinking...")
        # Tool call
        yield ToolCallEvent(
            tool_name="turn_on_light",
            tool_args={"entity_id": "light.kitchen"},
            tool_call_id="call_123",
        )
        yield StatusEvent(message="Executing...")
        # Tool result
        yield ToolResultEvent(
            tool_name="turn_on_light",
            tool_result={"success": True},
            tool_call_id="call_123",
        )
        # Final text
        yield TextEvent(content="I turned on the light.")
        yield CompletionEvent(messages=[])

    chat_log = MagicMock()
    chat_log.async_add_tool_result_content = MagicMock()

    deltas = []
    async for delta in entity._transform_provider_stream(mock_stream(), chat_log):
        deltas.append(delta)

    # Implementation deliberately skips ToolCallEvent/ToolResultEvent deltas
    # to avoid breaking Assist Pipeline buffering/TTS. Only text content is yielded.
    assert len(deltas) == 1
    assert deltas[0] == {"content": "I turned on the light."}


@pytest.mark.asyncio
async def test_transform_stream_error(entity):
    """Test transforming a stream with an error."""

    async def mock_stream():
        yield ErrorEvent(message="Something went wrong")

    chat_log = MagicMock()

    deltas = []
    async for delta in entity._transform_provider_stream(mock_stream(), chat_log):
        deltas.append(delta)

    # No role prefix delta — implementation yields content-only dicts
    assert len(deltas) == 1
    assert deltas[0] == {
        "content": "Sorry, I encountered an error processing your request."
    }
