"""Unit tests for Homeclaw Conversation Entity (conversation.py).

Tests the HomeclawConversationEntity bridge between HA's Conversation Entity
interface and Homeclaw's agent infrastructure.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import MATCH_ALL
from homeassistant.core import Context

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.conversation import (
    HomeclawConversationEntity,
    async_setup_entry,
)
from custom_components.homeclaw.core.events import (
    CompletionEvent,
    ErrorEvent,
    StatusEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
)


# ---------------------------------------------------------------------------
# Lightweight fakes for HA conversation types
# ---------------------------------------------------------------------------


@dataclass
class FakeSystemContent:
    content: str


@dataclass
class FakeUserContent:
    content: str


@dataclass
class FakeAssistantContent:
    agent_id: str = ""
    content: str = ""


class FakeChatLog:
    """Minimal ChatLog stand-in for unit tests."""

    def __init__(self, content: list | None = None, conversation_id: str = "test-conv"):
        self.content = content or []
        self.conversation_id = conversation_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(
    provider: str = "openai",
    entry_id: str = "test_entry",
) -> HomeclawConversationEntity:
    """Create a HomeclawConversationEntity with mocked dependencies."""
    config_entry = MagicMock()
    config_entry.entry_id = entry_id
    config_entry.data = {"ai_provider": provider}

    agent = MagicMock()
    agent.hass = MagicMock()
    agent._rag_manager = None
    agent._get_system_prompt = AsyncMock(return_value="You are Homeclaw.")
    agent._get_tools_for_provider = MagicMock(return_value=None)

    entity = HomeclawConversationEntity(config_entry, provider, agent)
    entity.hass = agent.hass
    return entity


async def _collect_stream(async_gen):
    """Collect all items from an async generator into a list."""
    items = []
    async for item in async_gen:
        items.append(item)
    return items


async def _fake_provider_stream(chunks: list[dict]):
    """Create a fake async generator from a list of dicts."""
    for chunk in chunks:
        yield chunk


# ---------------------------------------------------------------------------
# Tests: async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for the platform setup entry function."""

    @pytest.mark.asyncio
    async def test_setup_with_valid_agent(self):
        """Agent exists -> entity is added."""
        hass = MagicMock()
        mock_agent = MagicMock()
        hass.data = {DOMAIN: {"agents": {"openai": mock_agent}}}

        config_entry = MagicMock()
        config_entry.data = {"ai_provider": "openai"}

        async_add_entities = MagicMock()
        await async_setup_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], HomeclawConversationEntity)

    @pytest.mark.asyncio
    async def test_setup_without_agent_skips(self):
        """No agent for provider -> no entity added, no crash."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"agents": {}}}

        config_entry = MagicMock()
        config_entry.data = {"ai_provider": "nonexistent"}

        async_add_entities = MagicMock()
        await async_setup_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_with_empty_hass_data(self):
        """hass.data has no DOMAIN key -> no crash."""
        hass = MagicMock()
        hass.data = {}

        config_entry = MagicMock()
        config_entry.data = {"ai_provider": "openai"}

        async_add_entities = MagicMock()
        await async_setup_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Entity properties
# ---------------------------------------------------------------------------


class TestEntityProperties:
    """Tests for entity attribute correctness."""

    def test_name(self):
        entity = _make_entity("openai")
        assert entity._attr_name == "Conversation"

    def test_unique_id(self):
        entity = _make_entity("openai", entry_id="abc123")
        assert entity._attr_unique_id == "abc123-conversation"

    def test_has_entity_name(self):
        entity = _make_entity()
        assert entity._attr_has_entity_name is True

    def test_supports_streaming(self):
        entity = _make_entity()
        assert entity._attr_supports_streaming is True

    def test_supported_languages_match_all(self):
        entity = _make_entity()
        assert entity.supported_languages == MATCH_ALL

    def test_device_info(self):
        entity = _make_entity("gemini_oauth", entry_id="entry1")
        info = entity._attr_device_info
        assert (DOMAIN, "entry1") in info["identifiers"]
        assert info["name"] == "Homeclaw Gemini Oauth"
        assert info["manufacturer"] == "Homeclaw"
        assert info["model"] == "gemini_oauth"

    def test_voice_sessions_initialized_empty(self):
        entity = _make_entity()
        assert entity._voice_sessions == {}


# ---------------------------------------------------------------------------
# Tests: _convert_chat_log_to_messages
# ---------------------------------------------------------------------------


class TestConvertChatLogToMessages:
    """Tests for ChatLog -> provider message conversion."""

    def _patch_content_types(self):
        """Patch conversation module content types to our fakes."""
        return patch.multiple(
            "custom_components.homeclaw.conversation.conversation",
            SystemContent=FakeSystemContent,
            UserContent=FakeUserContent,
            AssistantContent=FakeAssistantContent,
        )

    def test_basic_conversion(self):
        entity = _make_entity()
        chat_log = FakeChatLog(
            content=[
                FakeSystemContent(content="System prompt"),
                FakeUserContent(content="Hello"),
                FakeAssistantContent(content="Hi there"),
            ]
        )

        with self._patch_content_types():
            messages = entity._convert_chat_log_to_messages(chat_log)

        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi there"}

    def test_excludes_system_content(self):
        entity = _make_entity()
        chat_log = FakeChatLog(
            content=[
                FakeSystemContent(content="System"),
            ]
        )

        with self._patch_content_types():
            messages = entity._convert_chat_log_to_messages(chat_log)

        assert messages == []

    def test_exclude_last_user(self):
        entity = _make_entity()
        chat_log = FakeChatLog(
            content=[
                FakeSystemContent(content="System"),
                FakeUserContent(content="First question"),
                FakeAssistantContent(content="First answer"),
                FakeUserContent(content="Second question"),
            ]
        )

        with self._patch_content_types():
            messages = entity._convert_chat_log_to_messages(
                chat_log, exclude_last_user=True
            )

        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "First question"}
        assert messages[1] == {"role": "assistant", "content": "First answer"}

    def test_exclude_last_user_only_removes_last(self):
        """With multiple user messages, only the last one is removed."""
        entity = _make_entity()
        chat_log = FakeChatLog(
            content=[
                FakeUserContent(content="First"),
                FakeUserContent(content="Second"),
                FakeUserContent(content="Third"),
            ]
        )

        with self._patch_content_types():
            messages = entity._convert_chat_log_to_messages(
                chat_log, exclude_last_user=True
            )

        assert len(messages) == 2
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"

    def test_empty_chat_log(self):
        entity = _make_entity()
        chat_log = FakeChatLog(content=[])

        with self._patch_content_types():
            messages = entity._convert_chat_log_to_messages(chat_log)

        assert messages == []

    def test_skips_empty_assistant_content(self):
        """AssistantContent with empty content string is skipped."""
        entity = _make_entity()
        chat_log = FakeChatLog(
            content=[
                FakeAssistantContent(content=""),
                FakeAssistantContent(content="Real response"),
            ]
        )

        with self._patch_content_types():
            messages = entity._convert_chat_log_to_messages(chat_log)

        assert len(messages) == 1
        assert messages[0]["content"] == "Real response"


# ---------------------------------------------------------------------------
# Tests: _transform_provider_stream
# ---------------------------------------------------------------------------


class TestTransformProviderStream:
    """Tests for Homeclaw chunk -> ChatLog delta conversion."""

    @pytest.mark.asyncio
    async def test_text_chunks(self):
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield TextEvent(content="Hello ")
            yield TextEvent(content="world")
            yield CompletionEvent(messages=[])

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        assert deltas[0] == {"content": "Hello "}
        assert deltas[1] == {"content": "world"}
        assert len(deltas) == 2  # no fallback needed

    @pytest.mark.asyncio
    async def test_empty_text_chunks_skipped(self):
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield TextEvent(content="")
            yield TextEvent(content="Real text")
            yield CompletionEvent(messages=[])

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        assert deltas[0] == {"content": "Real text"}
        assert len(deltas) == 1

    @pytest.mark.asyncio
    async def test_status_chunks_skipped(self):
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield TextEvent(content="Hi")
            yield StatusEvent(message="Calling tool...")
            yield TextEvent(content=" there")
            yield CompletionEvent(messages=[])

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        # status should not appear in output
        assert {"content": "Hi"} in deltas
        assert {"content": " there"} in deltas
        assert len(deltas) == 2

    @pytest.mark.asyncio
    async def test_error_chunk(self):
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield ErrorEvent(message="API rate limit")

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        # Error details should NOT be exposed to user (sanitized)
        assert len(deltas) == 1
        assert "error" in deltas[0]["content"].lower()
        assert "API rate limit" not in deltas[0]["content"]

    @pytest.mark.asyncio
    async def test_empty_stream_fallback(self):
        """Empty stream should still yield a minimal assistant delta."""
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield CompletionEvent(messages=[])

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        assert len(deltas) == 1
        assert deltas[0] == {"content": " "}

    @pytest.mark.asyncio
    async def test_tools_only_stream_fallback(self):
        """Stream with only tool events should yield fallback assistant delta."""
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield ToolCallEvent(
                tool_name="get_state", tool_args={}, tool_call_id="call_1"
            )
            yield ToolResultEvent(
                tool_name="get_state", tool_result="on", tool_call_id="call_1"
            )
            yield CompletionEvent(messages=[])

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        assert deltas[0] == {"content": " "}
        assert len(deltas) == 1

    @pytest.mark.asyncio
    async def test_error_after_text_no_duplicate_role(self):
        """Error after text chunks should not emit duplicate content."""
        entity = _make_entity()
        chat_log = MagicMock()

        async def stream():
            yield TextEvent(content="Starting...")
            yield ErrorEvent(message="Oops")

        deltas = await _collect_stream(
            entity._transform_provider_stream(stream(), chat_log)
        )

        # Both text and error deltas should be present, no role deltas at all
        assert deltas[0] == {"content": "Starting..."}
        assert "error" in deltas[1]["content"].lower()
        assert len(deltas) == 2


# ---------------------------------------------------------------------------
# Tests: _build_stream_kwargs
# ---------------------------------------------------------------------------


class TestBuildStreamKwargs:
    """Tests for stream kwargs assembly."""

    def test_basic_kwargs(self):
        entity = _make_entity()

        with patch(
            "custom_components.homeclaw.models.get_context_window",
            return_value=128000,
        ):
            kwargs = entity._build_stream_kwargs(
                user_id="user1",
                system_prompt="System prompt",
                conversation_history=[],
                session_id="sess-123",
            )

        assert kwargs["hass"] is entity._agent.hass
        assert kwargs["user_id"] == "user1"
        assert kwargs["system_prompt_override"] == "System prompt"
        assert kwargs["session_id"] == "sess-123"
        assert kwargs["conversation_history"] == []
        assert kwargs["context_window"] == 128000

    def test_conversation_history_none_not_included(self):
        """When conversation_history is None, it should not be in kwargs."""
        entity = _make_entity()

        with patch(
            "custom_components.homeclaw.models.get_context_window",
            return_value=128000,
        ):
            kwargs = entity._build_stream_kwargs(
                user_id="user1",
                system_prompt="Prompt",
                conversation_history=None,
            )

        assert "conversation_history" not in kwargs

    def test_conversation_history_empty_list_included(self):
        """Empty list [] should be passed (not treated as falsy)."""
        entity = _make_entity()

        with patch(
            "custom_components.homeclaw.models.get_context_window",
            return_value=128000,
        ):
            kwargs = entity._build_stream_kwargs(
                user_id="user1",
                system_prompt="Prompt",
                conversation_history=[],
            )

        assert kwargs["conversation_history"] == []

    def test_tools_included_when_available(self):
        entity = _make_entity()
        entity._agent._get_tools_for_provider.return_value = [
            {"name": "get_state", "description": "Get entity state"}
        ]

        with patch(
            "custom_components.homeclaw.models.get_context_window",
            return_value=128000,
        ):
            kwargs = entity._build_stream_kwargs(
                user_id="user1",
                system_prompt="Prompt",
                conversation_history=[],
            )

        assert "tools" in kwargs
        assert kwargs["tools"][0]["name"] == "get_state"

    def test_rag_context_included(self):
        entity = _make_entity()

        with patch(
            "custom_components.homeclaw.models.get_context_window",
            return_value=128000,
        ):
            kwargs = entity._build_stream_kwargs(
                user_id="user1",
                system_prompt="Prompt",
                conversation_history=[],
                rag_context="light.living_room is a smart bulb",
            )

        assert kwargs["rag_context"] == "light.living_room is a smart bulb"

    def test_memory_flush_fn_included_when_rag_initialized(self):
        entity = _make_entity()
        # Set up RAG manager with memory manager
        entity._agent._rag_manager = MagicMock()
        entity._agent._rag_manager.is_initialized = True
        mock_mem_mgr = MagicMock()
        entity._agent._rag_manager._memory_manager = mock_mem_mgr

        with patch(
            "custom_components.homeclaw.models.get_context_window",
            return_value=128000,
        ):
            kwargs = entity._build_stream_kwargs(
                user_id="user1",
                system_prompt="Prompt",
                conversation_history=[],
            )

        assert kwargs["memory_flush_fn"] is mock_mem_mgr.flush_from_messages


# ---------------------------------------------------------------------------
# Tests: Voice session persistence
# ---------------------------------------------------------------------------


class TestVoiceSessionPersistence:
    """Tests for voice session create/save functionality."""

    @pytest.mark.asyncio
    async def test_get_or_create_voice_session_creates_new(self):
        entity = _make_entity()
        mock_storage = AsyncMock()
        mock_session = MagicMock()
        mock_session.session_id = "hc-session-1"
        mock_storage.create_session = AsyncMock(return_value=mock_session)

        with patch.object(entity, "_get_storage", return_value=mock_storage):
            result = await entity._get_or_create_voice_session(
                user_id="user1",
                conversation_id="conv-abc",
                first_message="Turn on the lights",
            )

        assert result == "hc-session-1"
        mock_storage.create_session.assert_called_once_with(
            provider="openai",
            title="Voice: Turn on the lights",
        )
        # Mapping should be cached with (user_id, conversation_id) key
        assert entity._voice_sessions[("user1", "conv-abc")] == "hc-session-1"

    @pytest.mark.asyncio
    async def test_get_or_create_voice_session_reuses_cached(self):
        entity = _make_entity()
        entity._voice_sessions[("user1", "conv-existing")] = "hc-session-cached"
        mock_storage = AsyncMock()

        with patch.object(entity, "_get_storage", return_value=mock_storage):
            result = await entity._get_or_create_voice_session(
                user_id="user1",
                conversation_id="conv-existing",
                first_message="Any message",
            )

        assert result == "hc-session-cached"
        mock_storage.create_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_voice_session_none_conversation_id(self):
        entity = _make_entity()
        result = await entity._get_or_create_voice_session(
            user_id="user1",
            conversation_id=None,
            first_message="Hello",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_voice_session_handles_error(self):
        entity = _make_entity()
        mock_storage = AsyncMock()
        mock_storage.create_session = AsyncMock(side_effect=RuntimeError("disk full"))

        with patch.object(entity, "_get_storage", return_value=mock_storage):
            result = await entity._get_or_create_voice_session(
                user_id="user1",
                conversation_id="conv-xyz",
                first_message="Hello",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_save_voice_message(self):
        entity = _make_entity()
        mock_storage = AsyncMock()

        with patch.object(entity, "_get_storage", return_value=mock_storage):
            await entity._save_voice_message(
                user_id="user1",
                session_id="sess-1",
                role="user",
                content="Turn off the fan",
            )

        mock_storage.add_message.assert_called_once()
        call_args = mock_storage.add_message.call_args
        assert call_args[0][0] == "sess-1"
        message = call_args[0][1]
        assert message.role == "user"
        assert message.content == "Turn off the fan"
        assert message.session_id == "sess-1"
        assert message.status == "completed"
        assert message.metadata == {"source": "voice"}

    @pytest.mark.asyncio
    async def test_save_voice_message_handles_error(self):
        """Storage failure should not raise, just log."""
        entity = _make_entity()
        mock_storage = AsyncMock()
        mock_storage.add_message = AsyncMock(side_effect=ValueError("no session"))

        with patch.object(entity, "_get_storage", return_value=mock_storage):
            # Should not raise
            await entity._save_voice_message(
                user_id="user1",
                session_id="bad-sess",
                role="user",
                content="Hello",
            )

    def test_extract_last_assistant_text(self):
        entity = _make_entity()

        with patch(
            "custom_components.homeclaw.conversation.conversation.AssistantContent",
            FakeAssistantContent,
        ):
            chat_log = FakeChatLog(
                content=[
                    FakeAssistantContent(content="First response"),
                    FakeAssistantContent(content="Second response"),
                ]
            )
            result = entity._extract_last_assistant_text(chat_log)

        assert result == "Second response"

    def test_extract_last_assistant_text_empty(self):
        entity = _make_entity()

        with patch(
            "custom_components.homeclaw.conversation.conversation.AssistantContent",
            FakeAssistantContent,
        ):
            chat_log = FakeChatLog(content=[])
            result = entity._extract_last_assistant_text(chat_log)

        assert result == ""

    def test_title_truncates_long_message(self):
        """Voice session title should use first 50 chars of the message."""
        entity = _make_entity()
        long_message = "A" * 100
        # Directly test the title construction logic
        preview = long_message[:50].strip()
        title = f"Voice: {preview}"
        assert len(preview) == 50
        assert title.startswith("Voice: ")


# ---------------------------------------------------------------------------
# Tests: _get_storage
# ---------------------------------------------------------------------------


class TestGetStorage:
    """Tests for the SessionStorage factory method."""

    def test_creates_new_storage_instance(self):
        entity = _make_entity()
        entity.hass.data = {}

        with patch(
            "custom_components.homeclaw.conversation.SessionStorage"
        ) as MockStorage:
            mock_instance = MagicMock()
            MockStorage.return_value = mock_instance

            storage = entity._get_storage("user1")

            MockStorage.assert_called_once_with(entity.hass, "user1")
            assert storage is mock_instance

    def test_reuses_cached_storage(self):
        entity = _make_entity()
        cached = MagicMock()
        entity.hass.data = {"homeclaw_storage_user1": cached}

        with patch(
            "custom_components.homeclaw.conversation.SessionStorage"
        ) as MockStorage:
            storage = entity._get_storage("user1")

            MockStorage.assert_not_called()
            assert storage is cached
