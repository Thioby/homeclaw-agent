"""Conversation Manager for AI agent interactions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class Message:
    """Represents a message in a conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class ConversationManager:
    """Manages conversation history for AI interactions."""

    def __init__(self, max_messages: int = 100) -> None:
        """Initialize the conversation manager.

        Args:
            max_messages: Maximum number of messages to keep in history.
        """
        self._messages: list[Message] = []
        self._max_messages = max_messages

    def add_message(self, role: str, content: str) -> None:
        """Add a message to history.

        Args:
            role: The role of the message sender (system, user, or assistant).
            content: The content of the message.
        """
        msg = Message(role=role, content=content)  # type: ignore[arg-type]
        if role == "system":
            # System messages go at the beginning
            self._messages.insert(0, msg)
        else:
            self._messages.append(msg)
        self._enforce_limit()

    def add_user_message(self, content: str) -> None:
        """Add a user message to history.

        Args:
            content: The content of the user message.
        """
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to history.

        Args:
            content: The content of the assistant message.
        """
        self.add_message("assistant", content)

    def get_messages(self) -> list[dict[str, str]]:
        """Get messages as list of dicts.

        Returns:
            A copy of the messages as a list of dictionaries.
        """
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()

    def trim_to_limit(self, limit: int) -> None:
        """Keep only last N messages, preserving system messages.

        Args:
            limit: The maximum number of messages to keep.
        """
        if len(self._messages) <= limit:
            return

        # Separate system messages from others
        system_messages = [m for m in self._messages if m.role == "system"]
        non_system_messages = [m for m in self._messages if m.role != "system"]

        # Calculate how many non-system messages we can keep
        non_system_limit = limit - len(system_messages)
        if non_system_limit < 0:
            non_system_limit = 0

        # Keep only the last non_system_limit non-system messages
        kept_non_system = non_system_messages[-non_system_limit:] if non_system_limit > 0 else []

        # Rebuild messages: system first, then non-system
        self._messages = system_messages + kept_non_system

    def get_last_n_messages(self, n: int) -> list[dict[str, str]]:
        """Get last N messages.

        Args:
            n: Number of messages to retrieve.

        Returns:
            The last N messages as a list of dictionaries.
        """
        messages = self.get_messages()
        if n >= len(messages):
            return messages
        return messages[-n:]

    @property
    def message_count(self) -> int:
        """Get the number of messages in history.

        Returns:
            The count of messages.
        """
        return len(self._messages)

    def _enforce_limit(self) -> None:
        """Enforce max_messages limit by trimming old messages."""
        if len(self._messages) > self._max_messages:
            self.trim_to_limit(self._max_messages)
