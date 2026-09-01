"""L3 persona storage — one LLM-distilled user profile per user.

The persona is a Markdown summary of everything the memory system knows
about a user, regenerated periodically (see MemoryManager) and injected
into the system prompt on every conversation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class Persona:
    """A distilled user profile (L3 layer)."""

    user_id: str
    content: str
    memory_count_at_generation: int
    created_at: float
    updated_at: float


@dataclass
class PersonaStore:
    """SQLite storage for user personas. Shares the RAG database connection."""

    store: Any  # SqliteStore — avoid circular import
    _table_created: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        if self._table_created:
            return

        conn = self.store._conn
        if conn is None:
            raise RuntimeError("SqliteStore connection not available")

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_personas (
                user_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_count_at_generation INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.commit()
        self._table_created = True
        _LOGGER.info("Persona store table initialized")

    async def get_persona(self, user_id: str) -> Persona | None:
        conn = self.store._conn
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_personas WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Persona(
            user_id=row["user_id"],
            content=row["content"],
            memory_count_at_generation=row["memory_count_at_generation"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def save_persona(
        self, user_id: str, content: str, *, memory_count: int
    ) -> None:
        conn = self.store._conn
        if conn is None:
            return
        now = time.time()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_personas
                (user_id, content, memory_count_at_generation,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                content = excluded.content,
                memory_count_at_generation = excluded.memory_count_at_generation,
                updated_at = excluded.updated_at
            """,
            (user_id, content, memory_count, now, now),
        )
        conn.commit()

    async def delete_persona(self, user_id: str) -> bool:
        conn = self.store._conn
        if conn is None:
            return False
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_personas WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
