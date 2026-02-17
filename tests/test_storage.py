"""Tests for the session storage module.

These tests use simple mocks for HA dependencies, avoiding conflicts with
pytest-homeassistant-custom-component while still testing the storage logic.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.storage import (
    DATA_VERSION,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS,
    SESSION_RETENTION_DAYS,
    STORAGE_VERSION,
    Message,
    Session,
    SessionStorage,
)


# ============================================================================
# Test Fixtures
# ============================================================================


class MockStore:
    """Simple mock for homeassistant.helpers.storage.Store."""

    def __init__(self, hass: Any, version: int, key: str) -> None:
        self.hass = hass
        self.version = version
        self.key = key
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, Any] | None:
        return self._data

    async def async_save(self, data: dict[str, Any]) -> None:
        self._data = data


@pytest.fixture
def mock_store_patch():
    """Patch Store globally for all storage operations."""
    with patch(
        "custom_components.homeclaw.storage.Store",
        MockStore,
    ):
        yield


@pytest.fixture
def storage(hass, mock_store_patch) -> SessionStorage:
    """Create a SessionStorage instance for testing with mocked Store."""
    return SessionStorage(hass, "test_user")


@pytest.fixture
def storage_factory(hass, mock_store_patch):
    """Factory to create SessionStorage instances for different users."""

    def create(user_id: str) -> SessionStorage:
        return SessionStorage(hass, user_id)

    return create


# ============================================================================
# Test Cases
# ============================================================================


class TestMessage:
    """Tests for the Message dataclass."""

    def test_message_creation(self) -> None:
        """Test basic message creation."""
        msg = Message(
            message_id="msg-123",
            session_id="session-456",
            role="user",
            content="Hello, world!",
            timestamp="2026-01-23T10:00:00+00:00",
        )
        assert msg.message_id == "msg-123"
        assert msg.role == "user"
        assert msg.status == "completed"
        assert msg.error_message == ""
        assert msg.metadata == {}

    def test_message_with_all_fields(self) -> None:
        """Test message creation with all optional fields."""
        msg = Message(
            message_id="msg-123",
            session_id="session-456",
            role="assistant",
            content="Response text",
            timestamp="2026-01-23T10:00:00+00:00",
            status="completed",
            error_message="",
            metadata={"token_usage": 150},
        )
        assert msg.metadata["token_usage"] == 150

    def test_message_invalid_role(self) -> None:
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            Message(
                message_id="msg-123",
                session_id="session-456",
                role="invalid",
                content="Hello",
                timestamp="2026-01-23T10:00:00+00:00",
            )

    def test_message_invalid_status(self) -> None:
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            Message(
                message_id="msg-123",
                session_id="session-456",
                role="user",
                content="Hello",
                timestamp="2026-01-23T10:00:00+00:00",
                status="invalid",
            )

    def test_message_content_truncation(self) -> None:
        """Test that long content is truncated."""
        long_content = "x" * 60000
        msg = Message(
            message_id="msg-123",
            session_id="session-456",
            role="user",
            content=long_content,
            timestamp="2026-01-23T10:00:00+00:00",
        )
        assert len(msg.content) == 50000


class TestSession:
    """Tests for the Session dataclass."""

    def test_session_creation(self) -> None:
        """Test basic session creation."""
        session = Session(
            session_id="session-123",
            title="Test Session",
            created_at="2026-01-23T10:00:00+00:00",
            updated_at="2026-01-23T10:00:00+00:00",
            provider="anthropic",
        )
        assert session.session_id == "session-123"
        assert session.message_count == 0
        assert session.preview == ""


class TestSessionStorageBasics:
    """Basic tests for SessionStorage."""

    @pytest.mark.asyncio
    async def test_create_session(self, storage: SessionStorage) -> None:
        """Test creating a new session."""
        session = await storage.create_session(provider="anthropic")

        assert session.session_id is not None
        assert len(session.session_id) == 36  # UUID length
        assert session.provider == "anthropic"
        assert session.title == "New Conversation"
        assert session.message_count == 0

    @pytest.mark.asyncio
    async def test_create_session_with_title(self, storage: SessionStorage) -> None:
        """Test creating a session with custom title."""
        session = await storage.create_session(
            provider="openai", title="My Custom Chat"
        )

        assert session.title == "My Custom Chat"

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, storage: SessionStorage) -> None:
        """Test listing sessions when none exist."""
        sessions = await storage.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions_sorted(self, storage: SessionStorage) -> None:
        """Test that sessions are sorted by updated_at descending."""
        session1 = await storage.create_session(provider="anthropic", title="First")
        session2 = await storage.create_session(provider="anthropic", title="Second")
        session3 = await storage.create_session(provider="anthropic", title="Third")

        sessions = await storage.list_sessions()

        assert len(sessions) == 3
        # Most recently created should be first
        assert sessions[0].title == "Third"
        assert sessions[1].title == "Second"
        assert sessions[2].title == "First"

    @pytest.mark.asyncio
    async def test_get_session(self, storage: SessionStorage) -> None:
        """Test getting a session by ID."""
        created = await storage.create_session(provider="anthropic", title="Test")

        session = await storage.get_session(created.session_id)

        assert session is not None
        assert session.session_id == created.session_id
        assert session.title == "Test"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, storage: SessionStorage) -> None:
        """Test getting a non-existent session."""
        session = await storage.get_session("non-existent-id")
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session(self, storage: SessionStorage) -> None:
        """Test deleting a session."""
        session = await storage.create_session(provider="anthropic")

        result = await storage.delete_session(session.session_id)

        assert result is True
        sessions = await storage.list_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, storage: SessionStorage) -> None:
        """Test deleting a non-existent session (should succeed silently)."""
        result = await storage.delete_session("non-existent-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_rename_session(self, storage: SessionStorage) -> None:
        """Test renaming a session."""
        session = await storage.create_session(provider="anthropic")

        result = await storage.rename_session(session.session_id, "New Title")

        assert result is True
        renamed = await storage.get_session(session.session_id)
        assert renamed is not None
        assert renamed.title == "New Title"

    @pytest.mark.asyncio
    async def test_rename_session_not_found(self, storage: SessionStorage) -> None:
        """Test renaming a non-existent session."""
        result = await storage.rename_session("non-existent-id", "New Title")
        assert result is False


class TestToolMessageFields:
    """Tests for tool message fields (content_blocks, tool_call_id)."""

    def test_tool_use_role_accepted(self) -> None:
        """Test that tool_use role is valid."""
        msg = Message(
            message_id="msg-tool-1",
            session_id="session-1",
            role="tool_use",
            content="get_state({})",
            timestamp="2026-02-17T10:00:00+00:00",
            content_blocks=[
                {
                    "type": "tool_call",
                    "id": "call_abc",
                    "name": "get_state",
                    "arguments": {"entity_id": "sensor.temp"},
                }
            ],
        )
        assert msg.role == "tool_use"
        assert len(msg.content_blocks) == 1
        assert msg.content_blocks[0]["name"] == "get_state"
        assert msg.tool_call_id == ""

    def test_tool_result_role_accepted(self) -> None:
        """Test that tool_result role is valid."""
        msg = Message(
            message_id="msg-tool-2",
            session_id="session-1",
            role="tool_result",
            content='{"state": "22.5"}',
            timestamp="2026-02-17T10:00:01+00:00",
            content_blocks=[
                {
                    "type": "tool_result",
                    "tool_call_id": "call_abc",
                    "name": "get_state",
                    "content": '{"state": "22.5", "unit": "°C"}',
                }
            ],
            tool_call_id="call_abc",
        )
        assert msg.role == "tool_result"
        assert msg.tool_call_id == "call_abc"
        assert len(msg.content_blocks) == 1

    def test_default_content_blocks_empty(self) -> None:
        """Test that content_blocks defaults to empty list."""
        msg = Message(
            message_id="msg-1",
            session_id="session-1",
            role="user",
            content="Hello",
            timestamp="2026-02-17T10:00:00+00:00",
        )
        assert msg.content_blocks == []
        assert msg.tool_call_id == ""

    def test_tool_use_empty_content_allowed(self) -> None:
        """Test that tool_use messages can have empty content."""
        msg = Message(
            message_id="msg-1",
            session_id="session-1",
            role="tool_use",
            content="",
            timestamp="2026-02-17T10:00:00+00:00",
            content_blocks=[
                {
                    "type": "tool_call",
                    "id": "call_1",
                    "name": "turn_on",
                    "arguments": {"entity_id": "light.kitchen"},
                }
            ],
        )
        assert msg.content == ""
        assert len(msg.content_blocks) == 1


class TestToolMessagePersistence:
    """Tests for tool message storage and retrieval."""

    @pytest.mark.asyncio
    async def test_add_and_retrieve_tool_messages(
        self, storage: SessionStorage
    ) -> None:
        """Test that tool messages are persisted and retrieved correctly."""
        session = await storage.create_session(provider="anthropic")

        # User message
        user_msg = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content="What is the temperature?",
            timestamp="2026-02-17T10:00:00+00:00",
        )
        await storage.add_message(session.session_id, user_msg)

        # Tool use message
        tool_use_msg = Message(
            message_id="msg-2",
            session_id=session.session_id,
            role="tool_use",
            content='get_state({"entity_id": "sensor.temp"})',
            timestamp="2026-02-17T10:00:01+00:00",
            content_blocks=[
                {
                    "type": "tool_call",
                    "id": "call_abc",
                    "name": "get_state",
                    "arguments": {"entity_id": "sensor.temp"},
                }
            ],
        )
        await storage.add_message(session.session_id, tool_use_msg)

        # Tool result message
        tool_result_msg = Message(
            message_id="msg-3",
            session_id=session.session_id,
            role="tool_result",
            content='{"state": "22.5"}',
            timestamp="2026-02-17T10:00:02+00:00",
            content_blocks=[
                {
                    "type": "tool_result",
                    "tool_call_id": "call_abc",
                    "name": "get_state",
                    "content": '{"state": "22.5", "unit": "°C"}',
                }
            ],
            tool_call_id="call_abc",
        )
        await storage.add_message(session.session_id, tool_result_msg)

        # Assistant message
        assistant_msg = Message(
            message_id="msg-4",
            session_id=session.session_id,
            role="assistant",
            content="The temperature is 22.5°C.",
            timestamp="2026-02-17T10:00:03+00:00",
        )
        await storage.add_message(session.session_id, assistant_msg)

        # Retrieve and verify
        messages = await storage.get_session_messages(session.session_id)
        assert len(messages) == 4
        assert messages[0].role == "user"
        assert messages[1].role == "tool_use"
        assert messages[1].content_blocks[0]["name"] == "get_state"
        assert messages[2].role == "tool_result"
        assert messages[2].tool_call_id == "call_abc"
        assert messages[3].role == "assistant"

    @pytest.mark.asyncio
    async def test_tool_messages_dont_update_preview(
        self, storage: SessionStorage
    ) -> None:
        """Test that tool messages don't affect session preview or title."""
        session = await storage.create_session(provider="anthropic")

        user_msg = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content="Check temperature",
            timestamp="2026-02-17T10:00:00+00:00",
        )
        await storage.add_message(session.session_id, user_msg)

        tool_msg = Message(
            message_id="msg-2",
            session_id=session.session_id,
            role="tool_use",
            content="get_state({})",
            timestamp="2026-02-17T10:00:01+00:00",
            content_blocks=[
                {"type": "tool_call", "id": "c1", "name": "get_state", "arguments": {}}
            ],
        )
        await storage.add_message(session.session_id, tool_msg)

        updated = await storage.get_session(session.session_id)
        assert updated is not None
        # Preview should still be from user message, not tool message
        assert updated.preview == "Check temperature"
        assert updated.title == "Check temperature"


class TestMigrationV2ToV3:
    """Tests for v2 to v3 migration."""

    @pytest.mark.asyncio
    async def test_migrate_v2_data_adds_fields(self, hass) -> None:
        """Test that v2 messages get content_blocks and tool_call_id added."""
        mock_store = MockStore(hass, STORAGE_VERSION, "test")
        mock_store._data = {
            "version": 2,
            "sessions": [
                {
                    "session_id": "s1",
                    "title": "Test",
                    "created_at": "2026-02-17T10:00:00+00:00",
                    "updated_at": "2026-02-17T10:00:00+00:00",
                    "provider": "anthropic",
                    "message_count": 2,
                    "preview": "Hello",
                    "emoji": "",
                    "metadata": {},
                }
            ],
            "messages": {
                "s1": [
                    {
                        "message_id": "m1",
                        "session_id": "s1",
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2026-02-17T10:00:00+00:00",
                        "status": "completed",
                        "error_message": "",
                        "metadata": {},
                        "attachments": [],
                    },
                    {
                        "message_id": "m2",
                        "session_id": "s1",
                        "role": "assistant",
                        "content": "Hi there!",
                        "timestamp": "2026-02-17T10:00:01+00:00",
                        "status": "completed",
                        "error_message": "",
                        "metadata": {},
                        "attachments": [],
                    },
                ]
            },
        }

        with patch(
            "custom_components.homeclaw.storage.Store",
            return_value=mock_store,
        ):
            storage = SessionStorage(hass, "migrate_test")
            messages = await storage.get_session_messages("s1")

        assert len(messages) == 2
        # Both messages should have the new fields
        for msg in messages:
            assert msg.content_blocks == []
            assert msg.tool_call_id == ""

        # Version should be bumped
        assert mock_store._data["version"] == DATA_VERSION

    @pytest.mark.asyncio
    async def test_v3_data_not_re_migrated(self, hass) -> None:
        """Test that v3 data is not migrated again."""
        mock_store = MockStore(hass, STORAGE_VERSION, "test")
        mock_store._data = {
            "version": 3,
            "sessions": [
                {
                    "session_id": "s1",
                    "title": "Test",
                    "created_at": "2026-02-17T10:00:00+00:00",
                    "updated_at": "2026-02-17T10:00:00+00:00",
                    "provider": "anthropic",
                    "message_count": 1,
                    "preview": "",
                    "emoji": "",
                    "metadata": {},
                }
            ],
            "messages": {
                "s1": [
                    {
                        "message_id": "m1",
                        "session_id": "s1",
                        "role": "tool_use",
                        "content": "get_state({})",
                        "timestamp": "2026-02-17T10:00:00+00:00",
                        "status": "completed",
                        "error_message": "",
                        "metadata": {},
                        "attachments": [],
                        "content_blocks": [
                            {
                                "type": "tool_call",
                                "id": "c1",
                                "name": "get_state",
                                "arguments": {},
                            }
                        ],
                        "tool_call_id": "",
                    }
                ]
            },
        }

        with patch(
            "custom_components.homeclaw.storage.Store",
            return_value=mock_store,
        ):
            storage = SessionStorage(hass, "no_remigrate")
            messages = await storage.get_session_messages("s1")

        assert len(messages) == 1
        assert messages[0].role == "tool_use"
        assert len(messages[0].content_blocks) == 1

    @pytest.mark.asyncio
    async def test_v1_data_migrates_through_v2_and_v3(self, hass) -> None:
        """Test that v1 data migrates through both v1→v2 and v2→v3."""
        mock_store = MockStore(hass, STORAGE_VERSION, "test")
        mock_store._data = {
            "version": 1,
            "sessions": [
                {
                    "session_id": "s1",
                    "title": "Old",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "provider": "anthropic",
                    "message_count": 1,
                    "preview": "",
                }
            ],
            "messages": {
                "s1": [
                    {
                        "message_id": "m1",
                        "session_id": "s1",
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2026-02-17T10:00:00+00:00",
                        "status": "completed",
                        "error_message": "",
                        "attachments": [],
                    }
                ]
            },
        }

        with patch(
            "custom_components.homeclaw.storage.Store",
            return_value=mock_store,
        ):
            storage = SessionStorage(hass, "v1_user")
            messages = await storage.get_session_messages("s1")

        # Should have migrated through both steps
        assert len(messages) == 1
        assert messages[0].content_blocks == []
        assert messages[0].tool_call_id == ""
        assert mock_store._data["version"] == DATA_VERSION
        # Session should have metadata from v1→v2
        assert "metadata" in mock_store._data["sessions"][0]


class TestSessionStorageMessages:
    """Tests for message operations in SessionStorage."""

    @pytest.mark.asyncio
    async def test_add_message(self, storage: SessionStorage) -> None:
        """Test adding a message to a session."""
        session = await storage.create_session(provider="anthropic")
        message = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content="Hello, AI!",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        await storage.add_message(session.session_id, message)

        messages = await storage.get_session_messages(session.session_id)
        assert len(messages) == 1
        assert messages[0].content == "Hello, AI!"

    @pytest.mark.asyncio
    async def test_add_message_updates_session_metadata(
        self, storage: SessionStorage
    ) -> None:
        """Test that adding a user message updates session preview and title."""
        session = await storage.create_session(provider="anthropic")
        message = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content="How do I turn on the kitchen lights?",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        await storage.add_message(session.session_id, message)

        updated_session = await storage.get_session(session.session_id)
        assert updated_session is not None
        assert updated_session.message_count == 1
        assert updated_session.preview == "How do I turn on the kitchen lights?"
        assert updated_session.title == "How do I turn on the kitchen lights?"

    @pytest.mark.asyncio
    async def test_add_message_auto_title_truncation(
        self, storage: SessionStorage
    ) -> None:
        """Test that auto-generated titles are truncated properly."""
        session = await storage.create_session(provider="anthropic")
        long_content = (
            "This is a very long message that should be truncated for the title"
        )
        message = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content=long_content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        await storage.add_message(session.session_id, message)

        updated_session = await storage.get_session(session.session_id)
        assert updated_session is not None
        assert len(updated_session.title) <= 43  # 40 chars + "..."
        assert updated_session.title.endswith("...")

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_session(
        self, storage: SessionStorage
    ) -> None:
        """Test that adding a message to a non-existent session raises error."""
        message = Message(
            message_id="msg-1",
            session_id="non-existent",
            role="user",
            content="Hello",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        with pytest.raises(ValueError, match="Session non-existent not found"):
            await storage.add_message("non-existent", message)

    @pytest.mark.asyncio
    async def test_get_session_messages_not_found(
        self, storage: SessionStorage
    ) -> None:
        """Test getting messages from a non-existent session raises error."""
        with pytest.raises(ValueError, match="not found"):
            await storage.get_session_messages("non-existent")

    @pytest.mark.asyncio
    async def test_update_message(self, storage: SessionStorage) -> None:
        """Test updating an existing message."""
        session = await storage.create_session(provider="anthropic")
        message = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="assistant",
            content="",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="pending",
        )
        await storage.add_message(session.session_id, message)

        result = await storage.update_message(
            session.session_id,
            "msg-1",
            content="Updated response",
            status="completed",
        )

        assert result is True
        messages = await storage.get_session_messages(session.session_id)
        assert messages[0].content == "Updated response"
        assert messages[0].status == "completed"

    @pytest.mark.asyncio
    async def test_update_message_not_found(self, storage: SessionStorage) -> None:
        """Test updating a non-existent message returns False."""
        session = await storage.create_session(provider="anthropic")

        result = await storage.update_message(
            session.session_id, "non-existent", content="test"
        )

        assert result is False


class TestSessionStorageLimits:
    """Tests for storage limits enforcement."""

    @pytest.mark.asyncio
    async def test_session_limit_enforcement(self, storage: SessionStorage) -> None:
        """Test that session limit is enforced by removing oldest."""
        # Create MAX_SESSIONS sessions
        for i in range(MAX_SESSIONS):
            await storage.create_session(provider="anthropic", title=f"Session {i}")

        sessions = await storage.list_sessions()
        assert len(sessions) == MAX_SESSIONS

        # Create one more - should remove oldest
        await storage.create_session(provider="anthropic", title="New Session")

        sessions = await storage.list_sessions()
        assert len(sessions) == MAX_SESSIONS
        assert "Session 0" not in [s.title for s in sessions]
        assert "New Session" in [s.title for s in sessions]

    @pytest.mark.asyncio
    async def test_message_limit_enforcement(self, storage: SessionStorage) -> None:
        """Test that message limit is enforced by removing oldest."""
        session = await storage.create_session(provider="anthropic")

        # Add MAX_MESSAGES_PER_SESSION messages
        for i in range(MAX_MESSAGES_PER_SESSION):
            message = Message(
                message_id=f"msg-{i}",
                session_id=session.session_id,
                role="user",
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            await storage.add_message(session.session_id, message)

        messages = await storage.get_session_messages(session.session_id)
        assert len(messages) == MAX_MESSAGES_PER_SESSION
        assert messages[0].content == "Message 0"

        # Add one more - should remove oldest
        new_message = Message(
            message_id="msg-new",
            session_id=session.session_id,
            role="user",
            content="New message",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        await storage.add_message(session.session_id, new_message)

        messages = await storage.get_session_messages(session.session_id)
        assert len(messages) == MAX_MESSAGES_PER_SESSION
        assert messages[0].content == "Message 1"  # Message 0 was removed
        assert messages[-1].content == "New message"


class TestSessionStorageUserIsolation:
    """Tests for user isolation in SessionStorage."""

    @pytest.mark.asyncio
    async def test_user_isolation(self, storage_factory) -> None:
        """Test that users have isolated storage."""
        storage_a = storage_factory("user_a")
        storage_b = storage_factory("user_b")

        await storage_a.create_session(provider="anthropic", title="A's session")
        await storage_b.create_session(provider="anthropic", title="B's session")

        a_sessions = await storage_a.list_sessions()
        b_sessions = await storage_b.list_sessions()

        assert len(a_sessions) == 1
        assert len(b_sessions) == 1
        assert a_sessions[0].title == "A's session"
        assert b_sessions[0].title == "B's session"


class TestSessionStorageCleanup:
    """Tests for session cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, hass) -> None:
        """Test that old sessions are cleaned up."""
        old_date = (
            datetime.now(timezone.utc) - timedelta(days=SESSION_RETENTION_DAYS + 1)
        ).isoformat()
        recent_date = datetime.now(timezone.utc).isoformat()

        # Create a mock store with pre-populated data
        mock_store = MockStore(hass, STORAGE_VERSION, "test")
        mock_store._data = {
            "version": STORAGE_VERSION,
            "sessions": [
                {
                    "session_id": "old-session",
                    "title": "Old Session",
                    "created_at": old_date,
                    "updated_at": old_date,
                    "provider": "anthropic",
                    "message_count": 0,
                    "preview": "",
                },
                {
                    "session_id": "recent-session",
                    "title": "Recent Session",
                    "created_at": recent_date,
                    "updated_at": recent_date,
                    "provider": "anthropic",
                    "message_count": 0,
                    "preview": "",
                },
            ],
            "messages": {
                "old-session": [],
                "recent-session": [],
            },
        }

        with patch(
            "custom_components.homeclaw.storage.Store",
            return_value=mock_store,
        ):
            storage = SessionStorage(hass, "cleanup_test_user")
            sessions = await storage.list_sessions()

        assert len(sessions) == 1
        assert sessions[0].session_id == "recent-session"


class TestSessionStorageMigration:
    """Tests for legacy data migration."""

    @pytest.mark.asyncio
    async def test_migrate_legacy_data(self, hass) -> None:
        """Test migration of legacy prompt history."""
        # Track stores created
        stores: dict[str, MockStore] = {}

        def create_store(hass, version, key):
            store = MockStore(hass, version, key)
            stores[key] = store
            # Set up legacy data if this is the legacy store
            if "homeclaw_history_" in key:
                store._data = {
                    "prompts": ["Hello", "How are you?", "Turn on lights"],
                }
            return store

        with patch(
            "custom_components.homeclaw.storage.Store",
            side_effect=create_store,
        ):
            storage = SessionStorage(hass, "migration_user")
            sessions = await storage.list_sessions()

        # Should have created one session with migrated messages
        assert len(sessions) == 1
        assert sessions[0].title == "Imported History"
        assert sessions[0].message_count == 3

    @pytest.mark.asyncio
    async def test_migrate_legacy_data_already_migrated(self, hass) -> None:
        """Test that already migrated data is not migrated again."""
        stores: dict[str, MockStore] = {}

        def create_store(hass, version, key):
            store = MockStore(hass, version, key)
            stores[key] = store
            if "homeclaw_history_" in key:
                store._data = {
                    "prompts": ["Hello"],
                    "_migrated": True,
                }
            return store

        with patch(
            "custom_components.homeclaw.storage.Store",
            side_effect=create_store,
        ):
            storage = SessionStorage(hass, "already_migrated_user")
            sessions = await storage.list_sessions()

        # No sessions should be created
        assert len(sessions) == 0


class TestSessionStoragePersistence:
    """Tests for data persistence."""

    @pytest.mark.asyncio
    async def test_data_persists_across_instances(self, hass) -> None:
        """Test that data persists when creating new storage instances."""
        # Shared store to simulate persistence
        shared_store = MockStore(hass, STORAGE_VERSION, "shared")

        with patch(
            "custom_components.homeclaw.storage.Store",
            return_value=shared_store,
        ):
            # Create session with first instance
            storage1 = SessionStorage(hass, "persist_user")
            session = await storage1.create_session(
                provider="anthropic", title="Persistent"
            )
            message = Message(
                message_id="msg-1",
                session_id=session.session_id,
                role="user",
                content="Test persistence",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            await storage1.add_message(session.session_id, message)

            # Create new instance (simulates restart)
            storage2 = SessionStorage(hass, "persist_user")
            storage2._data = None  # Force reload

            sessions = await storage2.list_sessions()
            messages = await storage2.get_session_messages(session.session_id)

        assert len(sessions) == 1
        assert sessions[0].title == "Persistent"
        assert len(messages) == 1
        assert messages[0].content == "Test persistence"


class TestSessionStorageClearAll:
    """Tests for clear all functionality."""

    @pytest.mark.asyncio
    async def test_clear_all_sessions(self, storage: SessionStorage) -> None:
        """Test clearing all sessions for a user."""
        # Create some sessions
        await storage.create_session(provider="anthropic", title="Session 1")
        await storage.create_session(provider="anthropic", title="Session 2")

        sessions = await storage.list_sessions()
        assert len(sessions) == 2

        # Clear all
        await storage.clear_all_sessions()

        sessions = await storage.list_sessions()
        assert len(sessions) == 0
