"""SQLite-based Agent Identity storage.

Stores agent identity (name, personality, emoji) and user profile (name, preferences)
per user in the existing RAG SQLite database. Used for onboarding and personalization.

Tables created:
- agent_identity: Per-user identity storage (user_id, agent_name, agent_personality, etc.)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class AgentIdentity:
    """Agent identity and user profile data."""

    user_id: str
    agent_name: str | None = None
    agent_personality: str | None = None
    agent_emoji: str | None = None
    user_name: str | None = None
    user_info: str | None = None
    language: str = "auto"
    onboarding_completed: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class IdentityStore:
    """SQLite-based storage for agent identity.

    Uses the same SQLite database as the RAG system (SqliteStore) but manages
    its own table. One identity per user_id.

    Args:
        store: The existing SqliteStore instance from the RAG system.
    """

    store: Any  # SqliteStore — avoid circular import
    _table_created: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        """Create agent_identity table in the existing SQLite database."""
        if self._table_created:
            return

        conn = self.store._conn
        if conn is None:
            raise RuntimeError("SqliteStore connection not available")

        cursor = conn.cursor()

        # Agent identity table (one row per user)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_identity (
                user_id TEXT PRIMARY KEY,
                agent_name TEXT,
                agent_personality TEXT,
                agent_emoji TEXT,
                user_name TEXT,
                user_info TEXT,
                language TEXT DEFAULT 'auto',
                onboarding_completed INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        conn.commit()
        self._table_created = True
        _LOGGER.info("Agent identity table initialized")

    async def get_identity(self, user_id: str) -> AgentIdentity | None:
        """Get identity for a user.

        Args:
            user_id: User to fetch identity for.

        Returns:
            AgentIdentity if found, None if user hasn't been onboarded.
        """
        conn = self.store._conn
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_identity WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return AgentIdentity(
            user_id=row["user_id"],
            agent_name=row["agent_name"],
            agent_personality=row["agent_personality"],
            agent_emoji=row["agent_emoji"],
            user_name=row["user_name"],
            user_info=row["user_info"],
            language=row["language"] or "auto",
            onboarding_completed=bool(row["onboarding_completed"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def save_identity(self, identity: AgentIdentity) -> None:
        """Save or update identity (upsert).

        Args:
            identity: The identity to save.
        """
        conn = self.store._conn
        if conn is None:
            return

        now = time.time()

        # Update timestamps
        if identity.created_at == 0.0:
            identity.created_at = now
        identity.updated_at = now

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO agent_identity
            (user_id, agent_name, agent_personality, agent_emoji, user_name, user_info,
             language, onboarding_completed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identity.user_id,
                identity.agent_name,
                identity.agent_personality,
                identity.agent_emoji,
                identity.user_name,
                identity.user_info,
                identity.language,
                1 if identity.onboarding_completed else 0,
                identity.created_at,
                identity.updated_at,
            ),
        )
        conn.commit()

        _LOGGER.debug(
            "Saved identity for user %s (name=%s, onboarded=%s)",
            identity.user_id[:8],
            identity.agent_name,
            identity.onboarding_completed,
        )

    async def is_onboarded(self, user_id: str) -> bool:
        """Check if user has completed onboarding.

        Args:
            user_id: User to check.

        Returns:
            True if onboarded, False otherwise.
        """
        identity = await self.get_identity(user_id)
        return identity is not None and identity.onboarding_completed
