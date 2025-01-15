"""Session storage for Homeclaw chat conversations.

This module provides persistent storage for chat sessions and messages
using Home Assistant's Store helpers. Each user has isolated storage.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Storage configuration
STORAGE_VERSION = 1
STORAGE_KEY = "homeclaw_user_data"

# Limits
MAX_SESSIONS = 100
MAX_MESSAGES_PER_SESSION = 500
MAX_MESSAGE_LENGTH = 50000
SESSION_RETENTION_DAYS = 90


@dataclass
class Message:
    """Represents a chat message."""

    message_id: str
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str
    status: str = "completed"  # "pending" | "completed" | "error"
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and sanitize message data."""
        # Truncate content if too long
        if len(self.content) > MAX_MESSAGE_LENGTH:
            self.content = self.content[:MAX_MESSAGE_LENGTH]
            _LOGGER.warning(
                "Message content truncated to %d characters", MAX_MESSAGE_LENGTH
            )

        # Validate role
        if self.role not in ("user", "assistant", "system"):
            raise ValueError(f"Invalid role: {self.role}")

        # Validate status
        if self.status not in ("pending", "streaming", "completed", "error"):
            raise ValueError(f"Invalid status: {self.status}")


@dataclass
class Session:
    """Represents a chat session."""

    session_id: str
    title: str
    created_at: str
    updated_at: str
    provider: str
    message_count: int = 0
    preview: str = ""


class SessionStorage:
    """Manages conversation sessions with Home Assistant Store.

    Each user has their own isolated storage file. Sessions are automatically
    cleaned up after the retention period expires.
    """

    def __init__(self, hass: HomeAssistant, user_id: str) -> None:
        """Initialize the session storage.

        Args:
            hass: Home Assistant instance
            user_id: User identifier for storage isolation
        """
        self.hass = hass
        self.user_id = user_id
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{user_id}"
        )
        self._data: dict[str, Any] | None = None

    async def _load(self) -> dict[str, Any]:
        """Load data from store, with migration support.

        Returns:
            Dictionary containing sessions and messages data
        """
        if self._data is None:
            loaded = await self._store.async_load()
            self._data = loaded or {
                "version": STORAGE_VERSION,
                "sessions": [],
                "messages": {},
            }
            await self._migrate_legacy_data()
            await self._cleanup_old_sessions()
        return self._data

    async def _save(self) -> None:
        """Save data to store."""
        if self._data:
            await self._store.async_save(self._data)

    async def _migrate_legacy_data(self) -> None:
        """Migrate from legacy prompt history if exists.

        Converts old homeclaw_history_{user_id} format to new session format.
        Original data is preserved with a _migrated flag.
        """
        if self._data is None:
            return

        legacy_store: Store[dict[str, Any]] = Store(
            self.hass, 1, f"homeclaw_history_{self.user_id}"
        )
        legacy_data = await legacy_store.async_load()

        if (
            legacy_data
            and legacy_data.get("prompts")
            and not legacy_data.get("_migrated")
        ):
            _LOGGER.info(
                "Migrating legacy prompt history for user %s (%d prompts)",
                self.user_id,
                len(legacy_data["prompts"]),
            )

            # Create migration session
            now = datetime.now(timezone.utc).isoformat()
            session = Session(
                session_id=str(uuid.uuid4()),
                title="Imported History",
                created_at=now,
                updated_at=now,
                provider="unknown",
            )
            self._data["sessions"].append(asdict(session))
            self._data["messages"][session.session_id] = []

            # Convert prompts to messages
            for prompt in legacy_data["prompts"]:
                message = Message(
                    message_id=str(uuid.uuid4()),
                    session_id=session.session_id,
                    role="user",
                    content=prompt,
                    timestamp=now,
                )
                self._data["messages"][session.session_id].append(asdict(message))

            # Update session message count
            for s in self._data["sessions"]:
                if s["session_id"] == session.session_id:
                    s["message_count"] = len(legacy_data["prompts"])
                    if legacy_data["prompts"]:
                        s["preview"] = legacy_data["prompts"][-1][:100]
                    break

            # Mark as migrated (preserve original data)
            legacy_data["_migrated"] = True
            await legacy_store.async_save(legacy_data)
            await self._save()

            _LOGGER.info(
                "Migrated %d prompts to session %s",
                len(legacy_data["prompts"]),
                session.session_id,
            )

    async def _cleanup_old_sessions(self) -> None:
        """Remove sessions older than retention period."""
        if not self._data:
            return

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=SESSION_RETENTION_DAYS)
        ).isoformat()
        sessions_to_remove = [
            s["session_id"] for s in self._data["sessions"] if s["updated_at"] < cutoff
        ]

        if sessions_to_remove:
            _LOGGER.info(
                "Cleaning up %d old sessions for user %s",
                len(sessions_to_remove),
                self.user_id,
            )

            for session_id in sessions_to_remove:
                self._data["sessions"] = [
                    s for s in self._data["sessions"] if s["session_id"] != session_id
                ]
                self._data["messages"].pop(session_id, None)

            await self._save()

    async def list_sessions(self) -> list[Session]:
        """Get all sessions for user, sorted by updated_at desc.

        Returns:
            List of Session objects sorted by most recently updated first
        """
        data = await self._load()
        sessions = [Session(**s) for s in data.get("sessions", [])]
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    async def create_session(self, provider: str, title: str | None = None) -> Session:
        """Create a new session.

        Args:
            provider: AI provider to use for this session
            title: Optional session title (defaults to "New Conversation")

        Returns:
            The newly created Session object
        """
        data = await self._load()

        # Enforce session limit - remove oldest if at max
        if len(data["sessions"]) >= MAX_SESSIONS:
            oldest = min(data["sessions"], key=lambda s: s["updated_at"])
            _LOGGER.info(
                "Session limit reached, removing oldest session: %s",
                oldest["session_id"],
            )
            await self.delete_session(oldest["session_id"])
            # Reload data after deletion
            data = await self._load()

        now = datetime.now(timezone.utc).isoformat()
        session = Session(
            session_id=str(uuid.uuid4()),
            title=title or "New Conversation",
            created_at=now,
            updated_at=now,
            provider=provider,
        )

        data["sessions"].append(asdict(session))
        data["messages"][session.session_id] = []

        _LOGGER.info(
            "💾 Saving session %s to storage (user: %s)",
            session.session_id,
            self.user_id,
        )
        _LOGGER.info("Total sessions before save: %d", len(data["sessions"]))

        await self._save()

        _LOGGER.info("✅ Session %s saved successfully", session.session_id)

        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session ID to look up

        Returns:
            Session object if found, None otherwise
        """
        _LOGGER.info("=" * 80)
        _LOGGER.info(
            "GET_SESSION called for session_id: %s, user_id: %s",
            session_id,
            self.user_id,
        )

        data = await self._load()
        sessions = data.get("sessions", [])

        _LOGGER.info("Loaded %d sessions from storage", len(sessions))
        _LOGGER.info("self._data cache status: %s", "EXISTS" if self._data else "NONE")

        for s in sessions:
            if s["session_id"] == session_id:
                _LOGGER.info("✅ SESSION FOUND: %s", session_id)
                return Session(**s)

        # Log available session IDs for debugging
        if sessions:
            session_ids = [s["session_id"] for s in sessions[:5]]  # First 5
            _LOGGER.warning("❌ SESSION NOT FOUND! Looking for: %s", session_id)
            _LOGGER.warning("Available sessions (first 5): %s", session_ids)
        else:
            _LOGGER.warning("❌ NO SESSIONS in storage for user %s", self.user_id)

        return None

    async def get_session_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session.

        Args:
            session_id: The session ID

        Returns:
            List of Message objects in chronological order

        Raises:
            ValueError: If session not found
        """
        data = await self._load()

        # Verify session exists
        session_exists = any(
            s["session_id"] == session_id for s in data.get("sessions", [])
        )
        if not session_exists:
            raise ValueError(f"Session {session_id} not found")

        messages = data.get("messages", {}).get(session_id, [])

        # Deduplicate by message_id (keep last occurrence)
        seen: dict[str, dict[str, Any]] = {}
        for m in messages:
            seen[m["message_id"]] = m
        unique = list(seen.values())

        # Sort by timestamp to guarantee chronological order
        unique.sort(key=lambda m: m.get("timestamp", ""))

        return [Message(**m) for m in unique]

    async def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to a session.

        Args:
            session_id: The session ID
            message: The Message object to add

        Raises:
            ValueError: If session not found
        """
        data = await self._load()

        if session_id not in data["messages"]:
            raise ValueError(f"Session {session_id} not found")

        # Deduplicate: skip if message_id already exists
        existing_ids = {m["message_id"] for m in data["messages"][session_id]}
        if message.message_id in existing_ids:
            _LOGGER.debug(
                "Duplicate message_id %s in session %s, skipping",
                message.message_id,
                session_id,
            )
            return

        # Enforce message limit - remove oldest if at max
        if len(data["messages"][session_id]) >= MAX_MESSAGES_PER_SESSION:
            removed_count = (
                len(data["messages"][session_id]) - MAX_MESSAGES_PER_SESSION + 1
            )
            data["messages"][session_id] = data["messages"][session_id][removed_count:]
            _LOGGER.debug(
                "Message limit reached for session %s, removed %d oldest messages",
                session_id,
                removed_count,
            )

        data["messages"][session_id].append(asdict(message))

        # Update session metadata
        for session in data["sessions"]:
            if session["session_id"] == session_id:
                session["updated_at"] = datetime.now(timezone.utc).isoformat()
                session["message_count"] = len(data["messages"][session_id])

                # Update preview and auto-title from user messages
                if message.role == "user":
                    session["preview"] = message.content[:100]
                    if session["title"] == "New Conversation":
                        title_text = message.content[:40]
                        if len(message.content) > 40:
                            title_text += "..."
                        session["title"] = title_text
                break

        await self._save()

    async def update_message(
        self,
        session_id: str,
        message_id: str,
        content: str | None = None,
        status: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update an existing message.

        Args:
            session_id: The session ID
            message_id: The message ID to update
            content: Optional new content
            status: Optional new status
            error_message: Optional error message
            metadata: Optional metadata to merge

        Returns:
            True if message was found and updated, False otherwise
        """
        data = await self._load()

        if session_id not in data["messages"]:
            return False

        for msg in data["messages"][session_id]:
            if msg["message_id"] == message_id:
                if content is not None:
                    msg["content"] = content[:MAX_MESSAGE_LENGTH]
                if status is not None:
                    if status not in ("pending", "completed", "error"):
                        raise ValueError(f"Invalid status: {status}")
                    msg["status"] = status
                if error_message is not None:
                    msg["error_message"] = error_message
                if metadata is not None:
                    msg["metadata"] = {**msg.get("metadata", {}), **metadata}

                await self._save()
                return True

        return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages.

        Args:
            session_id: The session ID to delete

        Returns:
            True (always succeeds, even if session didn't exist)
        """
        data = await self._load()
        original_count = len(data["sessions"])
        data["sessions"] = [
            s for s in data["sessions"] if s["session_id"] != session_id
        ]
        data["messages"].pop(session_id, None)

        if len(data["sessions"]) < original_count:
            await self._save()
            _LOGGER.debug("Deleted session %s", session_id)

        return True

    async def rename_session(self, session_id: str, title: str) -> bool:
        """Rename a session.

        Args:
            session_id: The session ID
            title: The new title

        Returns:
            True if session was found and renamed, False otherwise
        """
        data = await self._load()
        for session in data["sessions"]:
            if session["session_id"] == session_id:
                session["title"] = title
                await self._save()
                return True
        return False

    async def get_preferences(self) -> dict[str, Any]:
        """Get user preferences (default provider, model, etc.).

        Returns:
            Dictionary with preference keys, e.g.
            {"default_provider": "gemini_oauth", "default_model": "gemini-2.5-pro"}.
        """
        data = await self._load()
        return dict(data.get("preferences", {}))

    async def set_preferences(self, prefs: dict[str, Any]) -> dict[str, Any]:
        """Update user preferences (merge with existing).

        Args:
            prefs: Dictionary of preferences to set/update.
                   Keys with None values are removed.

        Returns:
            The full updated preferences dictionary.
        """
        data = await self._load()
        current = data.get("preferences", {})

        for key, value in prefs.items():
            if value is None:
                current.pop(key, None)
            else:
                current[key] = value

        data["preferences"] = current
        await self._save()
        _LOGGER.info(
            "Updated preferences for user %s: %s", self.user_id, list(prefs.keys())
        )
        return dict(current)

    async def clear_all_sessions(self) -> None:
        """Delete all sessions for this user.

        Use with caution - this permanently removes all data.
        """
        self._data = {
            "version": STORAGE_VERSION,
            "sessions": [],
            "messages": {},
        }
        await self._save()
        _LOGGER.info("Cleared all sessions for user %s", self.user_id)
