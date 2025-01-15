"""Tests for ConversationManager."""
from __future__ import annotations

import pytest

from custom_components.homeclaw.core.conversation import (
    ConversationManager,
    Message,
)


class TestConversationManagerInit:
    """Tests for ConversationManager initialization."""

    def test_init_empty(self) -> None:
        """Test that ConversationManager starts with empty messages."""
        manager = ConversationManager()

        assert manager.message_count == 0
        assert manager.get_messages() == []


class TestAddMessages:
    """Tests for adding messages to the conversation."""

    def test_add_user_message(self) -> None:
        """Test adding a user message."""
        manager = ConversationManager()

        manager.add_user_message("Hello, assistant!")

        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, assistant!"

    def test_add_assistant_message(self) -> None:
        """Test adding an assistant message."""
        manager = ConversationManager()

        manager.add_assistant_message("Hello! How can I help?")

        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Hello! How can I help?"

    def test_add_system_message(self) -> None:
        """Test that system message is added at the beginning."""
        manager = ConversationManager()

        # Add some messages first
        manager.add_user_message("User message")
        manager.add_assistant_message("Assistant message")

        # Add system message - should go at the beginning
        manager.add_message("system", "You are a helpful assistant.")

        messages = manager.get_messages()
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_add_multiple_system_messages(self) -> None:
        """Test that multiple system messages are inserted at beginning."""
        manager = ConversationManager()

        manager.add_user_message("User message")
        manager.add_message("system", "First system")
        manager.add_message("system", "Second system")

        messages = manager.get_messages()
        assert len(messages) == 3
        # Both system messages should be at the beginning
        # Second system message is inserted at position 0, pushing first to position 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Second system"
        assert messages[1]["role"] == "system"
        assert messages[1]["content"] == "First system"


class TestGetMessages:
    """Tests for get_messages method."""

    def test_get_messages_returns_copy(self) -> None:
        """Test that get_messages returns a copy, not the original list."""
        manager = ConversationManager()

        manager.add_user_message("Hello")

        messages1 = manager.get_messages()
        messages2 = manager.get_messages()

        # Should be equal but not the same object
        assert messages1 == messages2
        assert messages1 is not messages2

        # Modifying the returned list should not affect the manager
        messages1.append({"role": "user", "content": "Modified"})
        assert manager.message_count == 1


class TestClear:
    """Tests for clear method."""

    def test_clear(self) -> None:
        """Test that clear removes all messages."""
        manager = ConversationManager()

        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")
        manager.add_user_message("Message 2")

        assert manager.message_count == 3

        manager.clear()

        assert manager.message_count == 0
        assert manager.get_messages() == []


class TestTrimToLimit:
    """Tests for trim_to_limit method."""

    def test_trim_to_limit(self) -> None:
        """Test keeping only last N messages."""
        manager = ConversationManager()

        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")
        manager.add_user_message("Message 2")
        manager.add_assistant_message("Response 2")
        manager.add_user_message("Message 3")

        assert manager.message_count == 5

        manager.trim_to_limit(3)

        messages = manager.get_messages()
        assert len(messages) == 3
        # Should keep the last 3 messages
        assert messages[0]["content"] == "Message 2"
        assert messages[1]["content"] == "Response 2"
        assert messages[2]["content"] == "Message 3"

    def test_trim_to_limit_preserves_system_message(self) -> None:
        """Test that system message is preserved when trimming."""
        manager = ConversationManager()

        manager.add_message("system", "System prompt")
        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")
        manager.add_user_message("Message 2")
        manager.add_assistant_message("Response 2")

        # Trim to 3 messages - should keep system + last 2 non-system
        manager.trim_to_limit(3)

        messages = manager.get_messages()
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System prompt"
        # The last 2 non-system messages
        assert messages[1]["content"] == "Message 2"
        assert messages[2]["content"] == "Response 2"

    def test_trim_to_limit_no_change_if_under_limit(self) -> None:
        """Test that trim does nothing if under the limit."""
        manager = ConversationManager()

        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")

        manager.trim_to_limit(10)

        assert manager.message_count == 2

    def test_trim_to_limit_handles_zero(self) -> None:
        """Test that trim_to_limit(0) clears non-system messages."""
        manager = ConversationManager()

        manager.add_message("system", "System prompt")
        manager.add_user_message("Message 1")

        manager.trim_to_limit(1)

        # Should keep only system message
        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"


class TestGetLastNMessages:
    """Tests for get_last_n_messages method."""

    def test_get_last_n_messages(self) -> None:
        """Test getting last N messages."""
        manager = ConversationManager()

        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")
        manager.add_user_message("Message 2")
        manager.add_assistant_message("Response 2")
        manager.add_user_message("Message 3")

        last_three = manager.get_last_n_messages(3)

        assert len(last_three) == 3
        # Should return the last 3 messages
        assert last_three[0]["content"] == "Message 2"
        assert last_three[1]["content"] == "Response 2"
        assert last_three[2]["content"] == "Message 3"

    def test_get_last_n_messages_more_than_available(self) -> None:
        """Test getting more messages than available returns all."""
        manager = ConversationManager()

        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")

        last_ten = manager.get_last_n_messages(10)

        assert len(last_ten) == 2
        assert last_ten[0]["content"] == "Message 1"
        assert last_ten[1]["content"] == "Response 1"

    def test_get_last_n_messages_empty(self) -> None:
        """Test getting messages from empty manager."""
        manager = ConversationManager()

        result = manager.get_last_n_messages(5)

        assert result == []


class TestMessageCount:
    """Tests for message_count property."""

    def test_message_count(self) -> None:
        """Test that message_count returns correct count."""
        manager = ConversationManager()

        assert manager.message_count == 0

        manager.add_user_message("Message 1")
        assert manager.message_count == 1

        manager.add_assistant_message("Response 1")
        assert manager.message_count == 2

        manager.add_message("system", "System")
        assert manager.message_count == 3


class TestMaxMessages:
    """Tests for max_messages limit enforcement."""

    def test_enforce_limit_on_add(self) -> None:
        """Test that adding messages enforces the max limit."""
        manager = ConversationManager(max_messages=3)

        manager.add_user_message("Message 1")
        manager.add_assistant_message("Response 1")
        manager.add_user_message("Message 2")
        manager.add_assistant_message("Response 2")  # This should trigger enforcement

        # Should have trimmed to max_messages (3)
        assert manager.message_count == 3
        messages = manager.get_messages()
        # Oldest messages should be dropped
        assert messages[0]["content"] == "Response 1"
        assert messages[1]["content"] == "Message 2"
        assert messages[2]["content"] == "Response 2"


class TestMessageDataclass:
    """Tests for the Message dataclass."""

    def test_message_creation(self) -> None:
        """Test creating a Message instance."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_roles(self) -> None:
        """Test that Message accepts valid roles."""
        user_msg = Message(role="user", content="User content")
        assistant_msg = Message(role="assistant", content="Assistant content")
        system_msg = Message(role="system", content="System content")

        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"
        assert system_msg.role == "system"
