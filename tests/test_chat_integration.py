"""Integration tests for the new chat session functionality.

These tests verify the complete chat flow using simple mocks that don't conflict
with pytest-homeassistant-custom-component.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from custom_components.homeclaw.storage import (
    Message,
    Session,
    SessionStorage,
)


# ============================================================================
# Test Fixtures
# ============================================================================


class MockStore:
    """Mock for homeassistant.helpers.storage.Store with shared class-level storage.

    This allows testing persistence across multiple SessionStorage instances.
    """

    # Class-level storage for persistence testing across instances
    _stores: dict[str, "MockStore"] = {}

    def __init__(self, hass: Any, version: int, key: str) -> None:
        self.hass = hass
        self.version = version
        self.key = key
        # Check if we have existing data for this key (for persistence tests)
        if key in MockStore._stores:
            self._data = MockStore._stores[key]._data
        else:
            self._data: dict[str, Any] | None = None
        MockStore._stores[key] = self

    async def async_load(self) -> dict[str, Any] | None:
        return self._data

    async def async_save(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def reset_stores(cls) -> None:
        """Reset all stored data between tests."""
        cls._stores.clear()


@pytest.fixture(autouse=True)
def reset_mock_stores():
    """Reset mock stores before and after each test."""
    MockStore.reset_stores()
    yield
    MockStore.reset_stores()


@pytest.fixture
def mock_store_patch():
    """Patch Store globally for all storage operations."""
    with patch(
        "custom_components.homeclaw.storage.Store",
        MockStore,
    ):
        yield


# ============================================================================
# Integration Tests
# ============================================================================


class TestChatFlowIntegration:
    """Test the complete chat flow: create session -> send message -> verify persistence."""

    @pytest.mark.asyncio
    async def test_full_chat_flow(self, hass, mock_store_patch):
        """Test complete flow: create session, send messages, reload, verify."""
        storage = SessionStorage(hass, "test_user")

        session = await storage.create_session(provider="anthropic")
        assert session.session_id is not None
        assert session.title == "New Conversation"

        user_msg = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="user",
            content="Turn on the kitchen lights",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session.session_id, user_msg)

        assistant_msg = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="assistant",
            content="Done! I've turned on the kitchen lights.",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session.session_id, assistant_msg)

        storage2 = SessionStorage(hass, "test_user")
        messages = await storage2.get_session_messages(session.session_id)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Turn on the kitchen lights"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Done! I've turned on the kitchen lights."

    @pytest.mark.asyncio
    async def test_session_title_auto_update(self, hass, mock_store_patch):
        """Test that session title updates from first user message."""
        storage = SessionStorage(hass, "test_user")

        session = await storage.create_session(provider="openai")
        assert session.title == "New Conversation"

        user_msg = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="user",
            content="How do I create an automation for motion-activated lights?",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session.session_id, user_msg)

        sessions = await storage.list_sessions()
        assert len(sessions) == 1
        # Title is truncated to 40 chars + "..."
        assert sessions[0].title == "How do I create an automation for motion..."

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self, hass, mock_store_patch):
        """Test that messages are isolated between sessions."""
        storage = SessionStorage(hass, "test_user")

        session1 = await storage.create_session(provider="anthropic")
        session2 = await storage.create_session(provider="openai")

        msg1 = Message(
            message_id=str(uuid.uuid4()),
            session_id=session1.session_id,
            role="user",
            content="Message for session 1",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session1.session_id, msg1)

        msg2 = Message(
            message_id=str(uuid.uuid4()),
            session_id=session2.session_id,
            role="user",
            content="Message for session 2",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session2.session_id, msg2)

        messages1 = await storage.get_session_messages(session1.session_id)
        messages2 = await storage.get_session_messages(session2.session_id)

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0].content == "Message for session 1"
        assert messages2[0].content == "Message for session 2"

    @pytest.mark.asyncio
    async def test_session_delete_cascade(self, hass, mock_store_patch):
        """Test that deleting session removes all its messages."""
        storage = SessionStorage(hass, "test_user")

        session = await storage.create_session(provider="anthropic")

        for i in range(5):
            msg = Message(
                message_id=str(uuid.uuid4()),
                session_id=session.session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.utcnow().isoformat(),
            )
            await storage.add_message(session.session_id, msg)

        messages_before = await storage.get_session_messages(session.session_id)
        assert len(messages_before) == 5

        await storage.delete_session(session.session_id)

        sessions = await storage.list_sessions()
        assert len(sessions) == 0

        with pytest.raises(ValueError):
            await storage.get_session_messages(session.session_id)

    @pytest.mark.asyncio
    async def test_conversation_context_building(self, hass, mock_store_patch):
        """Test building conversation history for AI context."""
        storage = SessionStorage(hass, "test_user")

        session = await storage.create_session(provider="anthropic")

        conversation = [
            ("user", "Turn on kitchen lights"),
            ("assistant", "Done! Kitchen lights are on."),
            ("user", "Now turn them off"),
            ("assistant", "Kitchen lights are now off."),
            ("user", "What did I just ask you to do?"),
        ]

        for role, content in conversation:
            msg = Message(
                message_id=str(uuid.uuid4()),
                session_id=session.session_id,
                role=role,
                content=content,
                timestamp=datetime.utcnow().isoformat(),
            )
            await storage.add_message(session.session_id, msg)

        messages = await storage.get_session_messages(session.session_id)

        history = [{"role": m.role, "content": m.content} for m in messages]

        assert len(history) == 5
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Turn on kitchen lights"
        assert history[-1]["role"] == "user"
        assert history[-1]["content"] == "What did I just ask you to do?"

    @pytest.mark.asyncio
    async def test_session_preview_updates(self, hass, mock_store_patch):
        """Test that session preview updates with last user message."""
        storage = SessionStorage(hass, "test_user")

        session = await storage.create_session(provider="anthropic")

        msg1 = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="user",
            content="First message about lights",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session.session_id, msg1)

        sessions = await storage.list_sessions()
        assert sessions[0].preview == "First message about lights"

        msg2 = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            role="user",
            content="Second message about temperature",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage.add_message(session.session_id, msg2)

        sessions = await storage.list_sessions()
        assert sessions[0].preview == "Second message about temperature"

    @pytest.mark.asyncio
    async def test_session_message_count(self, hass, mock_store_patch):
        """Test that session message count is tracked correctly."""
        storage = SessionStorage(hass, "test_user")

        session = await storage.create_session(provider="anthropic")

        for i in range(10):
            msg = Message(
                message_id=str(uuid.uuid4()),
                session_id=session.session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.utcnow().isoformat(),
            )
            await storage.add_message(session.session_id, msg)

        sessions = await storage.list_sessions()
        assert sessions[0].message_count == 10

    @pytest.mark.asyncio
    async def test_user_isolation(self, hass, mock_store_patch):
        """Test that different users have isolated sessions."""
        storage_user_a = SessionStorage(hass, "user_a")
        storage_user_b = SessionStorage(hass, "user_b")

        session_a = await storage_user_a.create_session(provider="anthropic")
        session_b = await storage_user_b.create_session(provider="openai")

        msg_a = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_a.session_id,
            role="user",
            content="User A's private message",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage_user_a.add_message(session_a.session_id, msg_a)

        msg_b = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_b.session_id,
            role="user",
            content="User B's private message",
            timestamp=datetime.utcnow().isoformat(),
        )
        await storage_user_b.add_message(session_b.session_id, msg_b)

        # User A can only see their own sessions
        sessions_a = await storage_user_a.list_sessions()
        assert len(sessions_a) == 1
        assert sessions_a[0].session_id == session_a.session_id

        # User B can only see their own sessions
        sessions_b = await storage_user_b.list_sessions()
        assert len(sessions_b) == 1
        assert sessions_b[0].session_id == session_b.session_id

        # User A cannot access User B's session
        with pytest.raises(ValueError):
            await storage_user_a.get_session_messages(session_b.session_id)
