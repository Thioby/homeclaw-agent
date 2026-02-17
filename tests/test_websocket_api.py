"""Tests for the WebSocket API module."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api

from custom_components.homeclaw.const import DOMAIN, VALID_PROVIDERS
from custom_components.homeclaw.storage import Message, SessionStorage
from custom_components.homeclaw.websocket_api import (
    ERR_SESSION_NOT_FOUND,
    ERR_STORAGE_ERROR,
    ws_create_session,
    ws_delete_session,
    ws_get_session,
    ws_list_sessions,
    ws_rename_session,
    ws_send_message,
    ws_get_available_models,
    _get_user_id,
    _validate_session_id,
    _validate_title,
    _validate_message,
    MAX_TITLE_LENGTH,
)
from custom_components.homeclaw.storage import MAX_MESSAGE_LENGTH


# Unwrap decorated functions for testing
if hasattr(ws_list_sessions, "__wrapped__"):
    ws_list_sessions = ws_list_sessions.__wrapped__
if hasattr(ws_get_session, "__wrapped__"):
    ws_get_session = ws_get_session.__wrapped__
if hasattr(ws_create_session, "__wrapped__"):
    ws_create_session = ws_create_session.__wrapped__
if hasattr(ws_delete_session, "__wrapped__"):
    ws_delete_session = ws_delete_session.__wrapped__
if hasattr(ws_rename_session, "__wrapped__"):
    ws_rename_session = ws_rename_session.__wrapped__
if hasattr(ws_send_message, "__wrapped__"):
    ws_send_message = ws_send_message.__wrapped__
if hasattr(ws_get_available_models, "__wrapped__"):
    ws_get_available_models = ws_get_available_models.__wrapped__


class MockUser:
    """Mock Home Assistant User."""

    def __init__(self, user_id: str = "test_user_123") -> None:
        self.id = user_id


class MockConnection:
    """Mock WebSocket ActiveConnection."""

    def __init__(self, user: MockUser | None = None) -> None:
        self.user = user or MockUser()
        self.results: list[tuple[int, Any]] = []
        self.errors: list[tuple[int, str, str]] = []

    def send_result(self, msg_id: int, result: Any) -> None:
        self.results.append((msg_id, result))

    def send_error(self, msg_id: int, code: str, message: str) -> None:
        self.errors.append((msg_id, code, message))


@pytest.fixture
def mock_connection() -> MockConnection:
    """Create a mock WebSocket connection."""
    return MockConnection(MockUser("test_user_123"))


@pytest.fixture
def mock_connection_no_user() -> MockConnection:
    """Create a mock WebSocket connection without user."""
    conn = MockConnection()
    conn.user = None
    return conn


class TestGetUserId:
    """Tests for _get_user_id helper."""

    def test_get_user_id_with_user(self, mock_connection: MockConnection) -> None:
        """Test extracting user ID from connection."""
        user_id = _get_user_id(mock_connection)
        assert user_id == "test_user_123"

    def test_get_user_id_no_user(self, mock_connection_no_user: MockConnection) -> None:
        """Test fallback when no user present."""
        user_id = _get_user_id(mock_connection_no_user)
        assert user_id == "default"

    def test_get_user_id_user_no_id(self) -> None:
        """Test fallback when user has no ID."""
        conn = MockConnection()
        conn.user = MagicMock()
        conn.user.id = None
        user_id = _get_user_id(conn)
        assert user_id == "default"


class TestValidateSessionId:
    """Tests for _validate_session_id helper."""

    def test_valid_uuid(self) -> None:
        """Test valid UUID format."""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = _validate_session_id(valid_uuid)
        assert result == valid_uuid

    def test_valid_uuid_uppercase(self) -> None:
        """Test valid UUID with uppercase letters."""
        valid_uuid = "123E4567-E89B-12D3-A456-426614174000"
        result = _validate_session_id(valid_uuid)
        assert result == valid_uuid

    def test_invalid_uuid_format(self) -> None:
        """Test invalid UUID format raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_session_id("not-a-uuid")
        assert "valid UUID" in str(exc_info.value)

    def test_not_a_string(self) -> None:
        """Test non-string value raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_session_id(12345)
        assert "must be a string" in str(exc_info.value)

    def test_empty_string(self) -> None:
        """Test empty string raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_session_id("")
        assert "valid UUID" in str(exc_info.value)


class TestValidateTitle:
    """Tests for _validate_title helper."""

    def test_valid_title(self) -> None:
        """Test valid title."""
        result = _validate_title("My Session Title")
        assert result == "My Session Title"

    def test_truncates_long_title(self) -> None:
        """Test that long titles are truncated."""
        long_title = "A" * (MAX_TITLE_LENGTH + 50)
        result = _validate_title(long_title)
        assert len(result) == MAX_TITLE_LENGTH

    def test_not_a_string(self) -> None:
        """Test non-string value raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_title(12345)
        assert "must be a string" in str(exc_info.value)

    def test_empty_string(self) -> None:
        """Test empty string raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_title("")
        assert "cannot be empty" in str(exc_info.value)


class TestValidateMessage:
    """Tests for _validate_message helper."""

    def test_valid_message(self) -> None:
        """Test valid message."""
        result = _validate_message("Hello, this is a test message")
        assert result == "Hello, this is a test message"

    def test_not_a_string(self) -> None:
        """Test non-string value raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_message(12345)
        assert "must be a string" in str(exc_info.value)

    def test_empty_string(self) -> None:
        """Test empty string raises error."""
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_message("")
        assert "cannot be empty" in str(exc_info.value)

    def test_exceeds_max_length(self) -> None:
        """Test message exceeding max length raises error."""
        long_message = "A" * (MAX_MESSAGE_LENGTH + 1)
        with pytest.raises(vol.Invalid) as exc_info:
            _validate_message(long_message)
        assert "exceeds maximum length" in str(exc_info.value)

    def test_at_max_length(self) -> None:
        """Test message at exactly max length is valid."""
        max_message = "A" * MAX_MESSAGE_LENGTH
        result = _validate_message(max_message)
        assert len(result) == MAX_MESSAGE_LENGTH


class TestWsListSessions:
    """Tests for ws_list_sessions command."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test listing sessions when none exist."""
        msg = {"id": 1, "type": "homeclaw/sessions/list"}

        await ws_list_sessions(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        msg_id, result = mock_connection.results[0]
        assert msg_id == 1
        assert result == {"sessions": []}

    @pytest.mark.asyncio
    async def test_list_sessions_storage_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test listing sessions when storage raises an error."""
        from custom_components.homeclaw.websocket_api import (
            _get_storage,
            _STORAGE_CACHE_PREFIX,
        )

        # Create a mock storage that raises an exception
        mock_storage = MagicMock()
        mock_storage.list_sessions = AsyncMock(side_effect=Exception("Storage error"))

        # Cache the mock storage
        cache_key = f"{_STORAGE_CACHE_PREFIX}test_user_123"
        hass.data[cache_key] = mock_storage

        msg = {"id": 1, "type": "homeclaw/sessions/list"}
        await ws_list_sessions(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        msg_id, code, message = mock_connection.errors[0]
        assert msg_id == 1
        assert code == ERR_STORAGE_ERROR

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test listing sessions with existing data."""
        # Create some sessions first
        storage = SessionStorage(hass, "test_user_123")
        await storage.create_session(provider="anthropic", title="Session 1")
        await storage.create_session(provider="openai", title="Session 2")

        msg = {"id": 2, "type": "homeclaw/sessions/list"}
        await ws_list_sessions(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        msg_id, result = mock_connection.results[0]
        assert msg_id == 2
        assert len(result["sessions"]) == 2
        assert result["sessions"][0]["title"] == "Session 2"  # Most recent first


class TestWsGetSession:
    """Tests for ws_get_session command."""

    @pytest.mark.asyncio
    async def test_get_session_success(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test getting a session with messages."""
        storage = SessionStorage(hass, "test_user_123")
        session = await storage.create_session(provider="anthropic", title="Test")
        message = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content="Hello",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        await storage.add_message(session.session_id, message)

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/get",
            "session_id": session.session_id,
        }
        await ws_get_session(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        msg_id, result = mock_connection.results[0]
        assert msg_id == 1
        assert result["session"]["session_id"] == session.session_id
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test getting a non-existent session."""
        msg = {
            "id": 1,
            "type": "homeclaw/sessions/get",
            "session_id": "non-existent",
        }
        await ws_get_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        msg_id, code, message = mock_connection.errors[0]
        assert msg_id == 1
        assert code == ERR_SESSION_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_session_value_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test getting session when ValueError is raised."""
        from custom_components.homeclaw.websocket_api import _STORAGE_CACHE_PREFIX

        mock_storage = MagicMock()
        mock_storage.get_session = AsyncMock(side_effect=ValueError("Invalid session"))

        cache_key = f"{_STORAGE_CACHE_PREFIX}test_user_123"
        hass.data[cache_key] = mock_storage

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/get",
            "session_id": "12345678-1234-1234-1234-123456789012",
        }
        await ws_get_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_SESSION_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_session_storage_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test getting session when storage raises exception."""
        from custom_components.homeclaw.websocket_api import _STORAGE_CACHE_PREFIX

        mock_storage = MagicMock()
        mock_storage.get_session = AsyncMock(side_effect=Exception("Storage error"))

        cache_key = f"{_STORAGE_CACHE_PREFIX}test_user_123"
        hass.data[cache_key] = mock_storage

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/get",
            "session_id": "12345678-1234-1234-1234-123456789012",
        }
        await ws_get_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_STORAGE_ERROR


class TestWsCreateSession:
    """Tests for ws_create_session command."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test creating a new session."""
        msg = {
            "id": 1,
            "type": "homeclaw/sessions/create",
            "provider": "anthropic",
        }
        await ws_create_session(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        msg_id, result = mock_connection.results[0]
        assert msg_id == 1
        assert result["provider"] == "anthropic"
        assert result["title"] == "New Conversation"
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_create_session_with_title(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test creating a session with custom title."""
        msg = {
            "id": 1,
            "type": "homeclaw/sessions/create",
            "provider": "openai",
            "title": "My Custom Chat",
        }
        await ws_create_session(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result["title"] == "My Custom Chat"

    @pytest.mark.asyncio
    async def test_create_session_storage_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test creating session when storage raises exception."""
        from custom_components.homeclaw.websocket_api import _STORAGE_CACHE_PREFIX

        mock_storage = MagicMock()
        mock_storage.create_session = AsyncMock(side_effect=Exception("Storage error"))

        cache_key = f"{_STORAGE_CACHE_PREFIX}test_user_123"
        hass.data[cache_key] = mock_storage

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/create",
            "provider": "openai",
        }
        await ws_create_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_STORAGE_ERROR


class TestWsDeleteSession:
    """Tests for ws_delete_session command."""

    @pytest.mark.asyncio
    async def test_delete_session_success(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test deleting an existing session."""
        storage = SessionStorage(hass, "test_user_123")
        # Ensure websocket handler uses the same storage instance
        hass.data[f"{DOMAIN}_storage_test_user_123"] = storage

        session = await storage.create_session(provider="anthropic")

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/delete",
            "session_id": session.session_id,
        }
        await ws_delete_session(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result == {"success": True}

        # Verify session is deleted
        # Force reload to be sure, though sharing instance should handle it if _save updates _data correctly (which it does)
        sessions = await storage.list_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_delete_session_not_found(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test deleting a non-existent session (should succeed silently)."""
        msg = {
            "id": 1,
            "type": "homeclaw/sessions/delete",
            "session_id": "non-existent",
        }
        await ws_delete_session(hass, mock_connection, msg)

        # Should still return success
        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_delete_session_storage_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test deleting session when storage raises exception."""
        from custom_components.homeclaw.websocket_api import _STORAGE_CACHE_PREFIX

        mock_storage = MagicMock()
        mock_storage.delete_session = AsyncMock(side_effect=Exception("Storage error"))

        cache_key = f"{_STORAGE_CACHE_PREFIX}test_user_123"
        hass.data[cache_key] = mock_storage

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/delete",
            "session_id": "12345678-1234-1234-1234-123456789012",
        }
        await ws_delete_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_STORAGE_ERROR


class TestWsRenameSession:
    """Tests for ws_rename_session command."""

    @pytest.mark.asyncio
    async def test_rename_session_success(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test renaming an existing session."""
        storage = SessionStorage(hass, "test_user_123")
        # Ensure websocket handler uses the same storage instance
        hass.data[f"{DOMAIN}_storage_test_user_123"] = storage

        session = await storage.create_session(provider="anthropic")

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/rename",
            "session_id": session.session_id,
            "title": "Renamed Session",
        }
        await ws_rename_session(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result == {"success": True}

        # Verify rename
        renamed = await storage.get_session(session.session_id)
        assert renamed.title == "Renamed Session"

    @pytest.mark.asyncio
    async def test_rename_session_not_found(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test renaming a non-existent session."""
        msg = {
            "id": 1,
            "type": "homeclaw/sessions/rename",
            "session_id": "non-existent",
            "title": "New Title",
        }
        await ws_rename_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_SESSION_NOT_FOUND

    @pytest.mark.asyncio
    async def test_rename_session_storage_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test renaming session when storage raises exception."""
        from custom_components.homeclaw.websocket_api import _STORAGE_CACHE_PREFIX

        mock_storage = MagicMock()
        mock_storage.rename_session = AsyncMock(side_effect=Exception("Storage error"))

        cache_key = f"{_STORAGE_CACHE_PREFIX}test_user_123"
        hass.data[cache_key] = mock_storage

        msg = {
            "id": 1,
            "type": "homeclaw/sessions/rename",
            "session_id": "12345678-1234-1234-1234-123456789012",
            "title": "New Title",
        }
        await ws_rename_session(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_STORAGE_ERROR


class TestWsSendMessage:
    """Tests for ws_send_message command."""

    @pytest.mark.asyncio
    async def test_send_message_success(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test sending a message with successful AI response."""
        from custom_components.homeclaw.core.events import TextEvent, CompletionEvent

        # Set up session
        storage = SessionStorage(hass, "test_user_123")
        session = await storage.create_session(provider="anthropic")

        # Set up mock AI agent with stream_query as async generator
        async def mock_stream_query(*args, **kwargs):
            yield TextEvent(content="Hello! I can help with that.")
            yield CompletionEvent(messages=[])

        mock_agent = AsyncMock()
        mock_agent.stream_query = mock_stream_query
        hass.data[DOMAIN] = {
            "agents": {"anthropic": mock_agent},
        }

        msg = {
            "id": 1,
            "type": "homeclaw/chat/send",
            "session_id": session.session_id,
            "message": "Hello, AI!",
        }
        await ws_send_message(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result["success"] is True
        assert result["user_message"]["content"] == "Hello, AI!"
        assert result["user_message"]["role"] == "user"
        assert result["assistant_message"]["content"] == "Hello! I can help with that."
        assert result["assistant_message"]["role"] == "assistant"
        assert result["assistant_message"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_send_message_ai_error(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test sending a message when AI returns error."""
        from custom_components.homeclaw.core.events import ErrorEvent

        storage = SessionStorage(hass, "test_user_123")
        session = await storage.create_session(provider="anthropic")

        # Set up mock AI agent that yields an error event
        async def mock_stream_query(*args, **kwargs):
            yield ErrorEvent(message="AI service down")

        mock_agent = AsyncMock()
        mock_agent.stream_query = mock_stream_query
        hass.data[DOMAIN] = {
            "agents": {"anthropic": mock_agent},
        }

        msg = {
            "id": 1,
            "type": "homeclaw/chat/send",
            "session_id": session.session_id,
            "message": "Hello",
        }
        await ws_send_message(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result["success"] is False
        assert result["user_message"]["status"] == "completed"
        assert result["assistant_message"]["status"] == "error"
        assert "AI service down" in result["assistant_message"]["error_message"]

    @pytest.mark.asyncio
    async def test_send_message_provider_not_configured(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test sending message when provider is not configured."""
        storage = SessionStorage(hass, "test_user_123")
        session = await storage.create_session(provider="anthropic")

        # No agents configured
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN]["agents"] = {}

        msg = {
            "id": 1,
            "type": "homeclaw/chat/send",
            "session_id": session.session_id,
            "message": "Hello",
        }
        await ws_send_message(hass, mock_connection, msg)

        assert len(mock_connection.results) == 1
        _, result = mock_connection.results[0]
        assert result["success"] is False
        assert result["assistant_message"]["status"] == "error"
        assert "No AI agent configured" in result["assistant_message"]["error_message"]

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test sending message to non-existent session."""
        msg = {
            "id": 1,
            "type": "homeclaw/chat/send",
            "session_id": "non-existent",
            "message": "Hello",
        }
        await ws_send_message(hass, mock_connection, msg)

        assert len(mock_connection.errors) == 1
        _, code, _ = mock_connection.errors[0]
        assert code == ERR_SESSION_NOT_FOUND

    @pytest.mark.asyncio
    async def test_send_message_with_conversation_history(
        self, hass: HomeAssistant, mock_connection: MockConnection
    ) -> None:
        """Test that conversation history is passed to AI."""
        from custom_components.homeclaw.core.events import TextEvent, CompletionEvent

        storage = SessionStorage(hass, "test_user_123")
        session = await storage.create_session(provider="anthropic")

        # Add existing messages
        msg1 = Message(
            message_id="msg-1",
            session_id=session.session_id,
            role="user",
            content="Turn on lights",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        msg2 = Message(
            message_id="msg-2",
            session_id=session.session_id,
            role="assistant",
            content="Done, lights are on",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        await storage.add_message(session.session_id, msg1)
        await storage.add_message(session.session_id, msg2)

        # Set up mock agent with stream_query - capture kwargs for verification
        captured_kwargs = {}

        async def mock_stream_query(*args, **kwargs):
            captured_kwargs.update(kwargs)
            yield TextEvent(content="Lights turned off")
            yield CompletionEvent(messages=[])

        mock_agent = AsyncMock()
        mock_agent.stream_query = mock_stream_query
        hass.data[DOMAIN] = {"agents": {"anthropic": mock_agent}}

        msg = {
            "id": 1,
            "type": "homeclaw/chat/send",
            "session_id": session.session_id,
            "message": "Now turn them off",
        }
        await ws_send_message(hass, mock_connection, msg)

        # Verify conversation history was passed (excluding the current user message,
        # which _build_messages() in QueryProcessor appends to avoid duplication).
        history = captured_kwargs.get("conversation_history", [])
        assert (
            len(history) == 2
        )  # 2 existing messages (current query added by _build_messages)
        assert history[0]["content"] == "Turn on lights"
        assert history[1]["content"] == "Done, lights are on"


class TestUserIsolation:
    """Tests for user isolation in WebSocket API."""

    @pytest.mark.asyncio
    async def test_users_see_only_their_sessions(self, hass: HomeAssistant) -> None:
        """Test that users can only see their own sessions."""
        # Create sessions for user A
        conn_a = MockConnection(MockUser("user_a"))
        storage_a = SessionStorage(hass, "user_a")
        await storage_a.create_session(provider="anthropic", title="A's session")

        # Create sessions for user B
        conn_b = MockConnection(MockUser("user_b"))
        storage_b = SessionStorage(hass, "user_b")
        await storage_b.create_session(provider="anthropic", title="B's session")

        # User A lists sessions
        await ws_list_sessions(hass, conn_a, {"id": 1, "type": "..."})
        _, result_a = conn_a.results[0]

        # User B lists sessions
        await ws_list_sessions(hass, conn_b, {"id": 1, "type": "..."})
        _, result_b = conn_b.results[0]

        assert len(result_a["sessions"]) == 1
        assert result_a["sessions"][0]["title"] == "A's session"

        assert len(result_b["sessions"]) == 1
        assert result_b["sessions"][0]["title"] == "B's session"


class TestWsGetAvailableModels:
    """Tests for ws_get_available_models handler."""

    @pytest.mark.asyncio
    async def test_get_models_gemini_oauth(self, hass: HomeAssistant) -> None:
        """Test getting available models for gemini_oauth provider."""
        mock_connection = MockConnection(MockUser())

        msg = {
            "id": 1,
            "type": "homeclaw/models/list",
            "provider": "gemini_oauth",
        }
        await ws_get_available_models(hass, mock_connection, msg)

        msg_id, result = mock_connection.results[0]
        assert msg_id == 1
        assert result["provider"] == "gemini_oauth"
        assert result["supports_model_selection"] is True
        assert len(result["models"]) > 0

        # Verify expected models are present
        model_ids = [m["id"] for m in result["models"]]
        assert "gemini-3-pro-preview" in model_ids
        assert "gemini-3-flash" in model_ids
        assert "gemini-2.5-flash" in model_ids

        # Verify default model is marked
        default_models = [m for m in result["models"] if m.get("default")]
        assert len(default_models) == 1
        assert default_models[0]["id"] == "gemini-3-pro-preview"

    @pytest.mark.asyncio
    async def test_get_models_default_provider(self, hass: HomeAssistant) -> None:
        """Test getting models without specifying provider uses gemini_oauth."""
        mock_connection = MockConnection(MockUser())

        msg = {
            "id": 1,
            "type": "homeclaw/models/list",
        }
        await ws_get_available_models(hass, mock_connection, msg)

        msg_id, result = mock_connection.results[0]
        assert result["provider"] == "gemini_oauth"
        assert result["supports_model_selection"] is True

    @pytest.mark.asyncio
    async def test_get_models_anthropic(self, hass: HomeAssistant) -> None:
        """Test getting available models for anthropic provider."""
        mock_connection = MockConnection(MockUser())

        msg = {
            "id": 1,
            "type": "homeclaw/models/list",
            "provider": "anthropic",
        }
        await ws_get_available_models(hass, mock_connection, msg)

        msg_id, result = mock_connection.results[0]
        assert result["provider"] == "anthropic"
        assert result["supports_model_selection"] is True
        assert len(result["models"]) > 0

        # Verify expected models are present
        model_ids = [m["id"] for m in result["models"]]
        assert "claude-sonnet-4-20250514" in model_ids

        # Verify default model is marked
        default_models = [m for m in result["models"] if m.get("default")]
        assert len(default_models) == 1

    @pytest.mark.asyncio
    async def test_get_models_unknown_provider(self, hass: HomeAssistant) -> None:
        """Test that unknown provider returns no models."""
        mock_connection = MockConnection(MockUser())

        msg = {
            "id": 1,
            "type": "homeclaw/models/list",
            "provider": "nonexistent_provider",
        }
        await ws_get_available_models(hass, mock_connection, msg)

        msg_id, result = mock_connection.results[0]
        assert result["provider"] == "nonexistent_provider"
        assert result["supports_model_selection"] is False
        assert result["models"] == []
