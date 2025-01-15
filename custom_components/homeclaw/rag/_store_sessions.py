"""Session chunk storage mixin for the SQLite vector store.

Provides conversation indexing: storing, searching, listing, and managing
session conversation chunks with embeddings for RAG retrieval.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from ._store_utils import (
    SearchResult,
    cosine_distance,
    embedding_to_blob,
    read_embedding,
)

_LOGGER = logging.getLogger(__name__)


class SessionChunkMixin:
    """Mixin providing session chunk operations on ``session_chunks`` and related tables.

    Expects the host class to provide:
    - ``self._conn``: sqlite3.Connection
    - ``self._ensure_initialized()``: guard method
    """

    async def add_session_chunks(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        session_id: str = "",
        content_hash: str = "",
    ) -> None:
        """Store session conversation chunks with embeddings.

        Args:
            ids: Unique chunk IDs (SHA-256 based).
            texts: Chunk text contents.
            embeddings: Pre-computed embeddings for each chunk.
            metadatas: Optional metadata dicts for each chunk.
            session_id: Session these chunks belong to.
            content_hash: SHA-256 hash of full session content for change detection.
        """
        self._ensure_initialized()

        if not ids:
            return

        try:
            now = time.time()
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            for i, chunk_id in enumerate(ids):
                text = texts[i] if i < len(texts) else ""
                embedding = embeddings[i] if i < len(embeddings) else []
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO session_chunks
                        (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        session_id,
                        text,
                        embedding_to_blob(embedding),
                        json.dumps(metadata),
                        metadata.get("start_msg", 0),
                        metadata.get("end_msg", 0),
                        now,
                    ),
                )

                # Sync to session FTS5 (if available)
                try:
                    cursor.execute(
                        """
                        INSERT INTO session_chunks_fts (text, chunk_id, session_id)
                        VALUES (?, ?, ?)
                        """,
                        (text, chunk_id, session_id),
                    )
                except Exception:
                    pass  # FTS5 not available -- silently skip

            # Store session content hash for delta detection
            if session_id and content_hash:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO session_hashes
                        (session_id, content_hash, chunk_count, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, content_hash, len(ids), now),
                )

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug(
                "Stored %d session chunks for session %s", len(ids), session_id
            )

        except Exception as e:
            _LOGGER.error("Failed to store session chunks: %s", e)
            raise

    async def delete_session_chunks(self, session_id: str) -> None:
        """Delete all chunks for a given session.

        Args:
            session_id: Session whose chunks should be removed.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            # Delete from FTS5 first (if available)
            try:
                cursor.execute(
                    "DELETE FROM session_chunks_fts WHERE session_id = ?",
                    (session_id,),
                )
            except Exception:
                pass  # FTS5 not available

            # Delete from main table
            cursor.execute(
                "DELETE FROM session_chunks WHERE session_id = ?",
                (session_id,),
            )

            # Delete hash record
            cursor.execute(
                "DELETE FROM session_hashes WHERE session_id = ?",
                (session_id,),
            )

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug("Deleted session chunks for session %s", session_id)

        except Exception as e:
            _LOGGER.error("Failed to delete session chunks for %s: %s", session_id, e)

    async def get_session_hash(self, session_id: str) -> str | None:
        """Get the stored content hash for a session.

        Args:
            session_id: Session to look up.

        Returns:
            Content hash string if found, None otherwise.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute(
                "SELECT content_hash FROM session_hashes WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            return row["content_hash"] if row else None

        except Exception as e:
            _LOGGER.error("Failed to get session hash for %s: %s", session_id, e)
            return None

    async def search_session_chunks(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        min_similarity: float | None = None,
        session_id: str | None = None,
    ) -> list[SearchResult]:
        """Search session chunks using cosine similarity.

        Args:
            query_embedding: The embedding vector to search with.
            n_results: Maximum number of results to return.
            min_similarity: Minimum cosine similarity (0-1) for results.
            session_id: If provided, limit search to this session only.

        Returns:
            List of SearchResult objects sorted by similarity (lowest distance first).
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            if session_id:
                cursor.execute(
                    "SELECT id, session_id, text, embedding, metadata FROM session_chunks WHERE session_id = ?",
                    (session_id,),
                )
            else:
                cursor.execute(
                    "SELECT id, session_id, text, embedding, metadata FROM session_chunks"
                )
            rows = cursor.fetchall()

            if not rows:
                return []

            results = []
            for row in rows:
                embedding = read_embedding(row["embedding"])
                distance = cosine_distance(query_embedding, embedding)
                similarity = 1.0 - distance

                if min_similarity is not None and similarity < min_similarity:
                    continue

                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                metadata["session_id"] = row["session_id"]

                results.append(
                    SearchResult(
                        id=row["id"],
                        text=row["text"],
                        metadata=metadata,
                        distance=distance,
                    )
                )

            results.sort(key=lambda x: x.distance)
            return results[:n_results]

        except Exception as e:
            _LOGGER.error("Session chunk search failed: %s", e)
            return []

    async def list_session_chunks(
        self,
        *,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List session chunks (for RAG viewer UI).

        Args:
            session_id: Optional filter by session.
            limit: Max results per page.
            offset: Pagination offset.

        Returns:
            List of dicts with id, session_id, text (first 500 chars), start_msg, end_msg.
        """
        self._ensure_initialized()
        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            if session_id:
                cursor.execute(
                    """SELECT id, session_id, text, metadata, start_msg, end_msg
                       FROM session_chunks WHERE session_id = ?
                       ORDER BY start_msg ASC LIMIT ? OFFSET ?""",
                    (session_id, limit, offset),
                )
            else:
                cursor.execute(
                    """SELECT id, session_id, text, metadata, start_msg, end_msg
                       FROM session_chunks
                       ORDER BY session_id, start_msg ASC LIMIT ? OFFSET ?""",
                    (limit, offset),
                )
            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "text": row["text"][:500],
                        "text_length": len(row["text"]),
                        "start_msg": row["start_msg"],
                        "end_msg": row["end_msg"],
                    }
                )
            return results
        except Exception as e:
            _LOGGER.error("Failed to list session chunks: %s", e)
            return []

    async def get_session_chunk_stats(self) -> dict[str, Any]:
        """Get session chunk statistics.

        Returns:
            Dict with chunk count, session count, and storage size.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            cursor.execute("SELECT COUNT(*) FROM session_chunks")
            total_chunks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM session_chunks")
            indexed_sessions = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(LENGTH(embedding)) FROM session_chunks")
            row = cursor.fetchone()
            total_bytes = row[0] if row and row[0] else 0

            return {
                "total_chunks": total_chunks,
                "indexed_sessions": indexed_sessions,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / (1024 * 1024), 2),
            }

        except Exception as e:
            _LOGGER.error("Failed to get session chunk stats: %s", e)
            return {
                "total_chunks": 0,
                "indexed_sessions": 0,
                "total_bytes": 0,
                "total_mb": 0,
            }
