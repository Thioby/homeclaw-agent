"""Embedding cache mixin for the SQLite vector store.

Provides content-addressable caching of computed embeddings
keyed by (provider, model, SHA-256 hash) to avoid redundant API calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ._store_utils import blob_to_embedding, embedding_to_blob

_LOGGER = logging.getLogger(__name__)


class EmbeddingCacheMixin:
    """Mixin providing embedding cache operations on the ``embedding_cache`` table.

    Expects the host class to provide:
    - ``self._conn``: sqlite3.Connection
    - ``self._ensure_initialized()``: guard method
    """

    def cache_lookup(
        self,
        provider: str,
        model: str,
        hashes: list[str],
    ) -> dict[str, list[float]]:
        """Bulk lookup cached embeddings by content hashes.

        Args:
            provider: Embedding provider name (e.g., "openai", "gemini").
            model: Embedding model name (e.g., "text-embedding-3-small").
            hashes: List of SHA-256 content hashes to look up.

        Returns:
            Dict mapping hash -> embedding for cache hits.
        """
        self._ensure_initialized()

        if not hashes:
            return {}

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            result: dict[str, list[float]] = {}

            # Query in batches of 400 to avoid SQL parameter limits
            batch_size = 400
            for start in range(0, len(hashes), batch_size):
                batch = hashes[start : start + batch_size]
                placeholders = ",".join("?" * len(batch))
                cursor.execute(
                    f"""
                    SELECT hash, embedding FROM embedding_cache
                    WHERE provider = ? AND model = ? AND hash IN ({placeholders})
                    """,
                    [provider, model, *batch],
                )
                for row in cursor.fetchall():
                    result[row["hash"]] = blob_to_embedding(row["embedding"])

            return result

        except Exception as e:
            _LOGGER.error("Embedding cache lookup failed: %s", e)
            return {}

    def cache_upsert(
        self,
        provider: str,
        model: str,
        entries: list[tuple[str, list[float]]],
    ) -> None:
        """Store newly computed embeddings in the cache.

        Args:
            provider: Embedding provider name.
            model: Embedding model name.
            entries: List of (hash, embedding) tuples to cache.
        """
        self._ensure_initialized()

        if not entries:
            return

        try:
            now = time.time()
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            for content_hash, embedding in entries:
                blob = embedding_to_blob(embedding)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO embedding_cache
                        (provider, model, hash, embedding, dims, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (provider, model, content_hash, blob, len(embedding), now),
                )

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug(
                "Cached %d embeddings for %s/%s", len(entries), provider, model
            )

        except Exception as e:
            _LOGGER.error("Embedding cache upsert failed: %s", e)

    def cache_prune(self, max_entries: int = 10000) -> None:
        """Prune oldest cache entries if cache exceeds max size (LRU).

        Args:
            max_entries: Maximum number of cache entries to keep.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute("SELECT COUNT(*) FROM embedding_cache")
            count = cursor.fetchone()[0]

            if count <= max_entries:
                return

            excess = count - max_entries
            cursor.execute(
                """
                DELETE FROM embedding_cache
                WHERE rowid IN (
                    SELECT rowid FROM embedding_cache
                    ORDER BY updated_at ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )
            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.info(
                "Pruned %d oldest embedding cache entries (kept %d)",
                excess,
                max_entries,
            )

        except Exception as e:
            _LOGGER.error("Embedding cache prune failed: %s", e)

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get embedding cache statistics.

        Returns:
            Dict with cache entry count and approximate size.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute(
                "SELECT COUNT(*), SUM(LENGTH(embedding)) FROM embedding_cache"
            )
            row = cursor.fetchone()
            count = row[0] if row else 0
            total_bytes = row[1] if row and row[1] else 0

            return {
                "entries": count,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / (1024 * 1024), 2),
            }
        except Exception as e:
            _LOGGER.error("Failed to get cache stats: %s", e)
            return {"entries": 0, "total_bytes": 0, "total_mb": 0}
