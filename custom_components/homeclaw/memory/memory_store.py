"""SQLite-based Long-Term Memory storage.

Stores user memories (preferences, facts, decisions) alongside entity embeddings
in the existing RAG SQLite database. Uses binary blob embeddings, FTS5 keyword
search, and cosine similarity for vector search — same stack as the RAG system.

Tables created:
- memories: Main storage (id, user_id, text, embedding, category, importance, metadata, timestamps)
- memories_fts: FTS5 virtual table for keyword search on memory text
"""

from __future__ import annotations

import json
import logging
import math
import struct
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Memory categories
CATEGORY_PREFERENCE = "preference"
CATEGORY_FACT = "fact"
CATEGORY_DECISION = "decision"
CATEGORY_ENTITY = "entity"  # Contact info, entity references
CATEGORY_OBSERVATION = (
    "observation"  # Ephemeral notes (sleep times, mood, daily routines)
)
CATEGORY_OTHER = "other"

VALID_CATEGORIES = {
    CATEGORY_PREFERENCE,
    CATEGORY_FACT,
    CATEGORY_DECISION,
    CATEGORY_ENTITY,
    CATEGORY_OBSERVATION,
    CATEGORY_OTHER,
}

# Default TTL (in days) per category — None means permanent
DEFAULT_TTL_DAYS: dict[str, int | None] = {
    CATEGORY_PREFERENCE: None,
    CATEGORY_FACT: None,
    CATEGORY_DECISION: None,
    CATEGORY_ENTITY: None,
    CATEGORY_OBSERVATION: 7,
    CATEGORY_OTHER: None,
}

# Deduplication threshold (cosine similarity) — 95% = very similar
DEDUP_SIMILARITY_THRESHOLD = 0.95

# Default importance for auto-captured memories
DEFAULT_IMPORTANCE = 0.7

# Maximum memories per user (LRU eviction of least important + oldest)
MAX_MEMORIES_PER_USER = 500

# Minimum similarity for recall results
RECALL_MIN_SIMILARITY = 0.3

# Maximum memories to return in a single recall
RECALL_MAX_RESULTS = 5


@dataclass
class Memory:
    """A single memory entry."""

    id: str
    user_id: str
    text: str
    category: str
    importance: float
    created_at: float
    updated_at: float
    source: str = "auto"  # "auto", "user", "agent"
    session_id: str = ""
    score: float = 0.0  # Search relevance score (filled during search)
    expires_at: float | None = (
        None  # Unix timestamp when memory expires (None = permanent)
    )


@dataclass
class MemoryStore:
    """SQLite-based storage for long-term memories.

    Uses the same SQLite database as the RAG system (SqliteStore) but manages
    its own tables. Reuses the embedding format (binary blob) and search
    patterns (cosine similarity + FTS5) from the RAG system.

    Args:
        store: The existing SqliteStore instance from the RAG system.
    """

    store: Any  # SqliteStore — avoid circular import
    _tables_created: bool = field(default=False, repr=False)
    _fts_available: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        """Create memory tables in the existing SQLite database."""
        if self._tables_created:
            return

        conn = self.store._conn
        if conn is None:
            raise RuntimeError("SqliteStore connection not available")

        cursor = conn.cursor()

        # Main memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                category TEXT NOT NULL DEFAULT 'fact',
                importance REAL NOT NULL DEFAULT 0.7,
                source TEXT NOT NULL DEFAULT 'auto',
                session_id TEXT NOT NULL DEFAULT '',
                metadata TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user_id
            ON memories(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_category
            ON memories(user_id, category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_importance
            ON memories(user_id, importance DESC)
        """)

        # Migration: add expires_at column if missing
        try:
            cursor.execute("SELECT expires_at FROM memories LIMIT 1")
        except Exception:
            _LOGGER.info("Migrating memories table: adding expires_at column")
            cursor.execute("ALTER TABLE memories ADD COLUMN expires_at REAL")
            conn.commit()

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_expires
            ON memories(expires_at)
        """)

        # FTS5 for keyword search on memory text
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    text,
                    memory_id UNINDEXED,
                    user_id UNINDEXED,
                    category UNINDEXED
                )
            """)
            self._fts_available = True
            _LOGGER.debug("Memory FTS5 table created/verified")
        except Exception as fts_err:
            self._fts_available = False
            _LOGGER.debug("Memory FTS5 not available: %s", fts_err)

        conn.commit()
        self._tables_created = True
        _LOGGER.info("Memory store tables initialized (fts=%s)", self._fts_available)

    async def store_memory(
        self,
        text: str,
        embedding: list[float],
        user_id: str,
        *,
        category: str = CATEGORY_FACT,
        importance: float = DEFAULT_IMPORTANCE,
        source: str = "auto",
        session_id: str = "",
        metadata: dict[str, Any] | None = None,
        ttl_days: int | None = None,
    ) -> str | None:
        """Store a memory, deduplicating against existing memories.

        Args:
            text: The memory text to store.
            embedding: Pre-computed embedding vector.
            user_id: User who owns this memory.
            category: Memory category (preference, fact, decision, entity, observation, other).
            importance: Importance score 0.0-1.0.
            source: Origin of memory (auto, user, agent).
            session_id: Session where this was captured.
            metadata: Optional additional metadata.
            ttl_days: Time-to-live in days. None uses category default.

        Returns:
            Memory ID if stored, None if duplicate was detected.
        """
        conn = self.store._conn
        if conn is None:
            return None

        # Validate category
        if category not in VALID_CATEGORIES:
            category = CATEGORY_OTHER

        # Deduplication: check for very similar existing memories
        existing = await self.search_memories(
            query_embedding=embedding,
            user_id=user_id,
            limit=1,
            min_similarity=DEDUP_SIMILARITY_THRESHOLD,
        )
        if existing:
            _LOGGER.debug(
                "Duplicate memory detected (score=%.3f), skipping: %s",
                existing[0].score,
                text[:80],
            )
            # Update importance if new one is higher
            if importance > existing[0].importance:
                await self._update_importance(existing[0].id, importance)
            return None

        # Generate ID and timestamps
        memory_id = str(uuid.uuid4())
        now = time.time()

        # Calculate expires_at: explicit ttl_days > category default > None (permanent)
        if ttl_days is not None:
            expires_at = now + ttl_days * 86400
        else:
            default_ttl = DEFAULT_TTL_DAYS.get(category)
            expires_at = (now + default_ttl * 86400) if default_ttl else None

        # Store embedding as binary blob
        embedding_blob = self.store._embedding_to_blob(embedding)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memories (id, user_id, text, embedding, category, importance,
                                  source, session_id, metadata, created_at, updated_at,
                                  expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                user_id,
                text,
                embedding_blob,
                category,
                importance,
                source,
                session_id,
                json.dumps(metadata) if metadata else None,
                now,
                now,
                expires_at,
            ),
        )

        # Sync FTS5
        if self._fts_available:
            try:
                cursor.execute(
                    "INSERT INTO memories_fts (text, memory_id, user_id, category) VALUES (?, ?, ?, ?)",
                    (text, memory_id, user_id, category),
                )
            except Exception as fts_err:
                _LOGGER.debug("Memory FTS5 sync failed: %s", fts_err)

        conn.commit()

        # Enforce per-user limit
        await self._enforce_user_limit(user_id)

        _LOGGER.debug(
            "Stored memory [%s] (%s, importance=%.1f): %s",
            memory_id[:8],
            category,
            importance,
            text[:80],
        )
        return memory_id

    async def search_memories(
        self,
        query_embedding: list[float],
        user_id: str,
        *,
        limit: int = RECALL_MAX_RESULTS,
        min_similarity: float = RECALL_MIN_SIMILARITY,
        category: str | None = None,
    ) -> list[Memory]:
        """Vector search for memories by cosine similarity.

        Automatically filters out expired memories and runs lazy cleanup.

        Args:
            query_embedding: Query embedding vector.
            user_id: User whose memories to search.
            limit: Maximum results to return.
            min_similarity: Minimum cosine similarity threshold (0-1).
            category: Optional category filter.

        Returns:
            List of Memory objects sorted by relevance (highest score first).
        """
        conn = self.store._conn
        if conn is None:
            return []

        # Lazy cleanup: remove expired memories
        await self._cleanup_expired(user_id)

        now = time.time()
        cursor = conn.cursor()

        # Build query with optional category filter + exclude expired
        if category:
            cursor.execute(
                "SELECT * FROM memories WHERE user_id = ? AND category = ? "
                "AND (expires_at IS NULL OR expires_at > ?)",
                (user_id, category, now),
            )
        else:
            cursor.execute(
                "SELECT * FROM memories WHERE user_id = ? "
                "AND (expires_at IS NULL OR expires_at > ?)",
                (user_id, now),
            )

        rows = cursor.fetchall()
        if not rows:
            return []

        # Compute cosine similarity for each row
        results = []
        for row in rows:
            stored_embedding = self.store._read_embedding(row["embedding"])
            similarity = _cosine_similarity(query_embedding, stored_embedding)

            if similarity >= min_similarity:
                results.append(
                    Memory(
                        id=row["id"],
                        user_id=row["user_id"],
                        text=row["text"],
                        category=row["category"],
                        importance=row["importance"],
                        source=row["source"],
                        session_id=row["session_id"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        score=similarity,
                        expires_at=row["expires_at"],
                    )
                )

        # Sort by score descending, then by importance
        results.sort(key=lambda m: (m.score, m.importance), reverse=True)
        return results[:limit]

    async def keyword_search_memories(
        self,
        fts_query: str,
        user_id: str,
        *,
        limit: int = RECALL_MAX_RESULTS,
    ) -> list[Memory]:
        """FTS5 keyword search on memory text.

        Args:
            fts_query: FTS5 query string (from build_fts_query).
            user_id: User whose memories to search.
            limit: Maximum results to return.

        Returns:
            List of Memory objects sorted by BM25 relevance.
        """
        if not self._fts_available or not fts_query:
            return []

        conn = self.store._conn
        if conn is None:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT memories_fts.memory_id, bm25(memories_fts) as rank
                FROM memories_fts
                WHERE memories_fts MATCH ? AND memories_fts.user_id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, user_id, limit),
            )
            fts_rows = cursor.fetchall()

            if not fts_rows:
                return []

            # Fetch full memory data for each FTS result
            results = []
            for fts_row in fts_rows:
                memory_id = fts_row["memory_id"]
                rank = fts_row["rank"]
                bm25_score = _bm25_rank_to_score(rank)

                cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
                row = cursor.fetchone()
                if row:
                    # Skip expired memories
                    if row["expires_at"] and row["expires_at"] <= time.time():
                        continue
                    results.append(
                        Memory(
                            id=row["id"],
                            user_id=row["user_id"],
                            text=row["text"],
                            category=row["category"],
                            importance=row["importance"],
                            source=row["source"],
                            session_id=row["session_id"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                            score=bm25_score,
                            expires_at=row["expires_at"],
                        )
                    )

            return results

        except Exception as e:
            _LOGGER.debug("Memory keyword search failed: %s", e)
            return []

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The memory to delete.

        Returns:
            True if deleted, False if not found.
        """
        conn = self.store._conn
        if conn is None:
            return False

        cursor = conn.cursor()

        # Delete from FTS5 first
        if self._fts_available:
            try:
                cursor.execute(
                    "DELETE FROM memories_fts WHERE memory_id = ?", (memory_id,)
                )
            except Exception:
                pass

        # Delete from main table
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
        conn.commit()

        if deleted:
            _LOGGER.debug("Deleted memory: %s", memory_id[:8])
        return deleted

    async def delete_user_memories(self, user_id: str) -> int:
        """Delete all memories for a user (GDPR compliance).

        Args:
            user_id: User whose memories to delete.

        Returns:
            Number of memories deleted.
        """
        conn = self.store._conn
        if conn is None:
            return 0

        cursor = conn.cursor()

        # Delete from FTS5
        if self._fts_available:
            try:
                cursor.execute("DELETE FROM memories_fts WHERE user_id = ?", (user_id,))
            except Exception:
                pass

        # Delete from main table
        cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        count = cursor.rowcount
        conn.commit()

        _LOGGER.info("Deleted %d memories for user %s", count, user_id[:8])
        return count

    async def get_memory_count(self, user_id: str) -> int:
        """Get total memory count for a user."""
        conn = self.store._conn
        if conn is None:
            return 0

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]

    async def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Get memory statistics.

        Args:
            user_id: If provided, stats for specific user. Otherwise global stats.

        Returns:
            Dict with total count, per-category counts, etc.
        """
        conn = self.store._conn
        if conn is None:
            return {"total": 0}

        cursor = conn.cursor()

        if user_id:
            cursor.execute(
                "SELECT category, COUNT(*) as cnt FROM memories WHERE user_id = ? GROUP BY category",
                (user_id,),
            )
        else:
            cursor.execute(
                "SELECT category, COUNT(*) as cnt FROM memories GROUP BY category"
            )

        categories = {row["category"]: row["cnt"] for row in cursor.fetchall()}
        total = sum(categories.values())

        # Count unique users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM memories")
        unique_users = cursor.fetchone()[0]

        # Per-source breakdown
        if user_id:
            cursor.execute(
                "SELECT source, COUNT(*) as cnt FROM memories WHERE user_id = ? GROUP BY source",
                (user_id,),
            )
        else:
            cursor.execute(
                "SELECT source, COUNT(*) as cnt FROM memories GROUP BY source"
            )
        sources = {row["source"]: row["cnt"] for row in cursor.fetchall()}

        # Expiring soon (within 3 days)
        now = time.time()
        three_days = now + 3 * 86400
        if user_id:
            cursor.execute(
                "SELECT COUNT(*) FROM memories WHERE user_id = ? "
                "AND expires_at IS NOT NULL AND expires_at > ? AND expires_at <= ?",
                (user_id, now, three_days),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM memories "
                "WHERE expires_at IS NOT NULL AND expires_at > ? AND expires_at <= ?",
                (now, three_days),
            )
        expiring_soon = cursor.fetchone()[0]

        # Total with TTL (non-permanent)
        if user_id:
            cursor.execute(
                "SELECT COUNT(*) FROM memories WHERE user_id = ? AND expires_at IS NOT NULL AND expires_at > ?",
                (user_id, now),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL AND expires_at > ?",
                (now,),
            )
        total_with_ttl = cursor.fetchone()[0]

        return {
            "total": total,
            "categories": categories,
            "sources": sources,
            "unique_users": unique_users,
            "fts_available": self._fts_available,
            "expiring_soon": expiring_soon,
            "total_with_ttl": total_with_ttl,
        }

    async def list_memories(
        self,
        user_id: str,
        *,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
        include_expired: bool = False,
    ) -> list[Memory]:
        """List all memories for a user (paginated, no embedding search).

        Args:
            user_id: User whose memories to list.
            category: Optional category filter.
            limit: Max results per page.
            offset: Pagination offset.
            include_expired: If True, include expired memories too.

        Returns:
            List of Memory objects sorted by importance DESC, created_at DESC.
        """
        conn = self.store._conn
        if conn is None:
            return []

        now = time.time()
        cursor = conn.cursor()

        expire_filter = (
            "" if include_expired else "AND (expires_at IS NULL OR expires_at > ?)"
        )

        if category:
            params: list[Any] = [user_id, category]
            if not include_expired:
                params.append(now)
            params.extend([limit, offset])
            cursor.execute(
                f"""SELECT * FROM memories WHERE user_id = ? AND category = ?
                   {expire_filter}
                   ORDER BY importance DESC, created_at DESC LIMIT ? OFFSET ?""",
                params,
            )
        else:
            params = [user_id]
            if not include_expired:
                params.append(now)
            params.extend([limit, offset])
            cursor.execute(
                f"""SELECT * FROM memories WHERE user_id = ?
                   {expire_filter}
                   ORDER BY importance DESC, created_at DESC LIMIT ? OFFSET ?""",
                params,
            )

        return [
            Memory(
                id=row["id"],
                user_id=row["user_id"],
                text=row["text"],
                category=row["category"],
                importance=row["importance"],
                source=row["source"],
                session_id=row["session_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                expires_at=row["expires_at"],
            )
            for row in cursor.fetchall()
        ]

    async def _cleanup_expired(self, user_id: str) -> int:
        """Delete expired memories for a user (lazy cleanup).

        Called automatically during search/recall operations.

        Args:
            user_id: User whose expired memories to clean up.

        Returns:
            Number of expired memories deleted.
        """
        conn = self.store._conn
        if conn is None:
            return 0

        now = time.time()
        cursor = conn.cursor()

        # Find expired memory IDs
        cursor.execute(
            "SELECT id FROM memories WHERE user_id = ? AND expires_at IS NOT NULL AND expires_at <= ?",
            (user_id, now),
        )
        expired_ids = [row["id"] for row in cursor.fetchall()]

        if not expired_ids:
            return 0

        # Delete from FTS5
        if self._fts_available:
            for mid in expired_ids:
                try:
                    cursor.execute(
                        "DELETE FROM memories_fts WHERE memory_id = ?", (mid,)
                    )
                except Exception:
                    pass

        # Delete from main table
        placeholders = ",".join("?" * len(expired_ids))
        cursor.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})", expired_ids
        )
        conn.commit()

        _LOGGER.info(
            "Cleaned up %d expired memories for user %s", len(expired_ids), user_id[:8]
        )
        return len(expired_ids)

    async def _update_importance(self, memory_id: str, importance: float) -> None:
        """Update the importance score of an existing memory."""
        conn = self.store._conn
        if conn is None:
            return

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE memories SET importance = ?, updated_at = ? WHERE id = ?",
            (importance, time.time(), memory_id),
        )
        conn.commit()

    async def _enforce_user_limit(self, user_id: str) -> None:
        """Enforce maximum memories per user by evicting low-importance old entries."""
        conn = self.store._conn
        if conn is None:
            return

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]

        if count <= MAX_MEMORIES_PER_USER:
            return

        # Delete oldest, least important memories over the limit
        excess = count - MAX_MEMORIES_PER_USER
        cursor.execute(
            """
            SELECT id FROM memories
            WHERE user_id = ?
            ORDER BY importance ASC, created_at ASC
            LIMIT ?
            """,
            (user_id, excess),
        )
        ids_to_delete = [row["id"] for row in cursor.fetchall()]

        for mid in ids_to_delete:
            if self._fts_available:
                try:
                    cursor.execute(
                        "DELETE FROM memories_fts WHERE memory_id = ?", (mid,)
                    )
                except Exception:
                    pass
            cursor.execute("DELETE FROM memories WHERE id = ?", (mid,))

        conn.commit()
        _LOGGER.info(
            "Evicted %d memories for user %s (limit %d)",
            len(ids_to_delete),
            user_id[:8],
            MAX_MEMORIES_PER_USER,
        )


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def _bm25_rank_to_score(rank: float) -> float:
    """Convert SQLite FTS5 bm25() rank to a 0-1 score."""
    if not math.isfinite(rank):
        return 0.001
    return 1.0 / (1.0 + abs(rank))
