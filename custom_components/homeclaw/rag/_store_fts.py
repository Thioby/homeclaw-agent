"""FTS5 full-text search mixin for the SQLite vector store.

Provides entity and session keyword search via SQLite FTS5,
plus sync helpers for keeping FTS indexes in sync with main tables.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from ._store_utils import SearchResult, bm25_rank_to_score

_LOGGER = logging.getLogger(__name__)


class FtsIndexMixin:
    """Mixin providing FTS5 keyword search for entities and session chunks.

    Expects the host class to provide:
    - ``self._conn``: sqlite3.Connection
    - ``self._fts_available``: bool
    - ``self._ensure_initialized()``: guard method
    - ``self.table_name``: str (entity table name)
    """

    # FTS5 virtual table name suffix (appended to self.table_name)
    _FTS_TABLE_SUFFIX = "_fts"

    def _fts_sync_insert(
        self,
        cursor: sqlite3.Cursor,
        doc_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        """Insert a document into the FTS5 index (if available).

        Args:
            cursor: Active database cursor.
            doc_id: Document/entity ID.
            text: Searchable text content.
            metadata: Document metadata (extracts domain, area_name).
        """
        if not self._fts_available:
            return

        fts_table = self.table_name + self._FTS_TABLE_SUFFIX
        cursor.execute(
            f"INSERT INTO {fts_table} (text, entity_id, domain, area_name) VALUES (?, ?, ?, ?)",
            (
                text,
                doc_id,
                metadata.get("domain", ""),
                metadata.get("area_name", ""),
            ),
        )

    def _fts_sync_delete(self, cursor: sqlite3.Cursor, doc_ids: list[str]) -> None:
        """Delete documents from the FTS5 index (if available).

        Args:
            cursor: Active database cursor.
            doc_ids: List of document/entity IDs to remove.
        """
        if not self._fts_available or not doc_ids:
            return

        fts_table = self.table_name + self._FTS_TABLE_SUFFIX
        placeholders = ",".join("?" * len(doc_ids))
        cursor.execute(
            f"DELETE FROM {fts_table} WHERE entity_id IN ({placeholders})",
            doc_ids,
        )

    def _fts_sync_clear(self, cursor: sqlite3.Cursor) -> None:
        """Clear all FTS5 data (if available).

        Args:
            cursor: Active database cursor.
        """
        if not self._fts_available:
            return

        fts_table = self.table_name + self._FTS_TABLE_SUFFIX
        cursor.execute(f"DELETE FROM {fts_table}")

    async def keyword_search(
        self,
        fts_query: str,
        n_results: int = 10,
    ) -> list[SearchResult]:
        """Search for documents using FTS5 full-text search with BM25 ranking.

        The fts_query should be a pre-built FTS5 query string (from build_fts_query).

        Args:
            fts_query: FTS5 MATCH query string (e.g., '"bedroom" AND "light"').
            n_results: Maximum number of results to return.

        Returns:
            List of SearchResult objects with BM25-based scores (lower distance = better).
            Returns empty list if FTS5 is not available or query is empty.
        """
        self._ensure_initialized()

        if not self._fts_available or not fts_query:
            return []

        try:
            fts_table = self.table_name + self._FTS_TABLE_SUFFIX
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            cursor.execute(
                f"""
                SELECT entity_id, text, domain, area_name,
                       bm25({fts_table}) AS rank
                FROM {fts_table}
                WHERE {fts_table} MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_query, n_results),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                entity_id = row["entity_id"]
                bm25_score = bm25_rank_to_score(row["rank"])

                # Fetch full metadata from main table
                cursor.execute(
                    f"SELECT metadata FROM {self.table_name} WHERE id = ?",
                    (entity_id,),
                )
                meta_row = cursor.fetchone()
                metadata = (
                    json.loads(meta_row["metadata"])
                    if meta_row and meta_row["metadata"]
                    else {}
                )

                # Store BM25 score as distance (1 - score so lower = better match)
                results.append(
                    SearchResult(
                        id=entity_id,
                        text=row["text"],
                        metadata=metadata,
                        distance=1.0 - bm25_score,
                    )
                )

            _LOGGER.debug(
                "FTS5 keyword search returned %d results for query: %s",
                len(results),
                fts_query[:80],
            )
            return results

        except Exception as e:
            _LOGGER.warning(
                "FTS5 keyword search failed (falling back to vector-only): %s", e
            )
            return []

    async def keyword_search_sessions(
        self,
        fts_query: str,
        n_results: int = 5,
    ) -> list[SearchResult]:
        """Search session chunks using FTS5 full-text search.

        Args:
            fts_query: FTS5 MATCH query string.
            n_results: Maximum number of results to return.

        Returns:
            List of SearchResult objects with BM25-based scores.
        """
        self._ensure_initialized()

        if not fts_query:
            return []

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            cursor.execute(
                """
                SELECT chunk_id, session_id, text,
                       bm25(session_chunks_fts) AS rank
                FROM session_chunks_fts
                WHERE session_chunks_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_query, n_results),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                bm25_score = bm25_rank_to_score(row["rank"])

                # Fetch full metadata from session_chunks table
                cursor.execute(
                    "SELECT metadata FROM session_chunks WHERE id = ?",
                    (row["chunk_id"],),
                )
                meta_row = cursor.fetchone()
                metadata = (
                    json.loads(meta_row["metadata"])
                    if meta_row and meta_row["metadata"]
                    else {}
                )
                metadata["session_id"] = row["session_id"]

                results.append(
                    SearchResult(
                        id=row["chunk_id"],
                        text=row["text"],
                        metadata=metadata,
                        distance=1.0 - bm25_score,
                    )
                )

            _LOGGER.debug(
                "Session FTS5 search returned %d results for query: %s",
                len(results),
                fts_query[:80],
            )
            return results

        except Exception as e:
            _LOGGER.debug("Session FTS5 search failed: %s", e)
            return []
