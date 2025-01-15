"""SQLite-based vector store for RAG system.

This module provides a simple SQLite-based storage for entity embeddings
with cosine similarity search. No external vector database dependencies required.

The ``SqliteStore`` class composes functionality from domain-specific mixins:
- ``FtsIndexMixin``:        FTS5 keyword search for entities and sessions
- ``EmbeddingCacheMixin``:  Content-addressable embedding cache
- ``SessionChunkMixin``:    Session conversation chunk storage and search

Pure utility functions (cosine math, blob serialization, etc.) live in
``_store_utils`` and are re-exported here for backward compatibility.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from ._store_cache import EmbeddingCacheMixin
from ._store_fts import FtsIndexMixin
from ._store_sessions import SessionChunkMixin
from ._store_utils import (
    SearchResult,
    blob_to_embedding,
    bm25_rank_to_score,
    cosine_distance,
    cosine_similarity,
    embedding_to_blob,
    filter_metadata,
    read_embedding,
)

_LOGGER = logging.getLogger(__name__)

# Default table name for entity embeddings
DEFAULT_TABLE_NAME = "ha_entities"

# FTS5 virtual table name (derived from main table)
FTS_TABLE_SUFFIX = "_fts"


# ---------------------------------------------------------------------------
# Backward-compatible private aliases used by legacy callers / tests
# ---------------------------------------------------------------------------
_cosine_similarity = cosine_similarity
_bm25_rank_to_score = bm25_rank_to_score
_cosine_distance = cosine_distance


@dataclass
class SqliteStore(SessionChunkMixin, EmbeddingCacheMixin, FtsIndexMixin):
    """SQLite-based vector store for entity embeddings.

    Provides async-compatible methods for storing and searching embeddings.
    Uses SQLite with binary blob storage for embeddings and pure Python for
    cosine similarity computation.

    Composed from mixins:
    - ``FtsIndexMixin``:        FTS5 keyword search
    - ``EmbeddingCacheMixin``:  Embedding cache
    - ``SessionChunkMixin``:    Session chunk storage
    """

    persist_directory: str
    table_name: str = DEFAULT_TABLE_NAME
    _db_path: str = field(default="", repr=False)
    _conn: sqlite3.Connection | None = field(default=None, repr=False)
    _initialized: bool = field(default=False, repr=False)
    _fts_available: bool = field(default=False, repr=False)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Initialize SQLite database and create tables.

        Creates the persist directory if it doesn't exist and initializes
        the SQLite database with required tables.
        """
        if self._initialized:
            _LOGGER.debug("SqliteStore already initialized")
            return

        try:
            # Ensure persist directory exists
            os.makedirs(self.persist_directory, exist_ok=True)
            _LOGGER.debug("SQLite persist directory: %s", self.persist_directory)

            # Set up database path
            self._db_path = os.path.join(self.persist_directory, "vectors.db")

            # Initialize SQLite connection
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row

            # Create tables
            self._create_tables()

            # Migrate legacy JSON embeddings to binary blob
            self._migrate_embeddings_to_blob()

            self._initialized = True
            count = await self.get_document_count()
            _LOGGER.info("SQLite vector store initialized with %d documents", count)

        except Exception as e:
            _LOGGER.error("Failed to initialize SQLite store: %s", e)
            raise

    def _create_tables(self) -> None:
        """Create the required database tables."""
        if self._conn is None:
            return

        cursor = self._conn.cursor()

        # Main documents table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Index for faster lookups
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_id
            ON {self.table_name}(id)
        """)

        # Metadata table for tracking configuration (embedding provider, versions, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Embedding cache table (content-addressable by SHA-256 hash)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                hash TEXT NOT NULL,
                embedding BLOB NOT NULL,
                dims INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (provider, model, hash)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_embedding_cache_updated_at
            ON embedding_cache(updated_at)
        """)

        # Session chunks table for conversation indexing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_chunks (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                start_msg INTEGER NOT NULL,
                end_msg INTEGER NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_chunks_session_id
            ON session_chunks(session_id)
        """)

        # Session content hashes for delta change detection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_hashes (
                session_id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            )
        """)

        # FTS5 virtual table for keyword search (graceful fallback if unavailable)
        fts_table = self.table_name + FTS_TABLE_SUFFIX
        try:
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table} USING fts5(
                    text,
                    entity_id UNINDEXED,
                    domain UNINDEXED,
                    area_name UNINDEXED
                )
            """)
            self._fts_available = True
            _LOGGER.debug("FTS5 virtual table '%s' created/verified", fts_table)
        except Exception as fts_err:
            self._fts_available = False
            _LOGGER.warning("FTS5 not available (keyword search disabled): %s", fts_err)

        # FTS5 for session chunks (separate from entity FTS5)
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS session_chunks_fts USING fts5(
                    text,
                    chunk_id UNINDEXED,
                    session_id UNINDEXED
                )
            """)
            _LOGGER.debug("Session chunks FTS5 table created/verified")
        except Exception as fts_err:
            _LOGGER.debug("Session chunks FTS5 not available: %s", fts_err)

        self._conn.commit()
        _LOGGER.debug("Database tables created/verified (fts5=%s)", self._fts_available)

    def _migrate_embeddings_to_blob(self) -> None:
        """Migrate existing JSON string embeddings to binary blob format.

        Scans the main entity table for rows where the embedding column
        contains JSON text (str) and converts them to float32 binary blobs.
        This is idempotent -- rows already in blob format are skipped.

        Runs once at initialization if legacy JSON embeddings are detected.
        """
        if self._conn is None:
            return

        cursor = self._conn.cursor()

        # Check if any rows have JSON (text) embeddings
        cursor.execute(
            f"SELECT COUNT(*) FROM {self.table_name} WHERE typeof(embedding) = 'text'"
        )
        json_count = cursor.fetchone()[0]

        if json_count == 0:
            _LOGGER.debug("No JSON embeddings to migrate -- all rows use binary blob")
            return

        _LOGGER.info(
            "Migrating %d embeddings from JSON to binary blob format...", json_count
        )

        # Migrate in batches to avoid holding a huge transaction
        batch_size = 200
        migrated = 0
        failed = 0

        while True:
            cursor.execute(
                f"""
                SELECT id, embedding FROM {self.table_name}
                WHERE typeof(embedding) = 'text'
                LIMIT ?
                """,
                (batch_size,),
            )
            rows = cursor.fetchall()
            if not rows:
                break

            for row in rows:
                try:
                    embedding = json.loads(row["embedding"])
                    blob = embedding_to_blob(embedding)
                    cursor.execute(
                        f"UPDATE {self.table_name} SET embedding = ? WHERE id = ?",
                        (blob, row["id"]),
                    )
                    migrated += 1
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to migrate embedding for %s: %s", row["id"], e
                    )
                    failed += 1

            self._conn.commit()

        _LOGGER.info(
            "Embedding migration complete: %d migrated, %d failed", migrated, failed
        )

    # ------------------------------------------------------------------
    # Properties / guards
    # ------------------------------------------------------------------

    @property
    def fts_available(self) -> bool:
        """Whether FTS5 keyword search is available."""
        return self._fts_available

    def _ensure_initialized(self) -> None:
        """Ensure the store is initialized before operations."""
        if not self._initialized or self._conn is None:
            raise RuntimeError(
                "SqliteStore not initialized. Call async_initialize() first."
            )

    # ------------------------------------------------------------------
    # Entity document CRUD
    # ------------------------------------------------------------------

    async def add_documents(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add documents with their embeddings to the store.

        Args:
            ids: Unique identifiers for each document.
            texts: Text content of each document.
            embeddings: Pre-computed embeddings for each document.
            metadatas: Optional metadata dictionaries for each document.
        """
        self._ensure_initialized()

        if not ids:
            _LOGGER.debug("No documents to add")
            return

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            for i, doc_id in enumerate(ids):
                text = texts[i] if i < len(texts) else ""
                embedding = embeddings[i] if i < len(embeddings) else []
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                filtered_meta = filter_metadata(metadata)

                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name} (id, text, embedding, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        text,
                        embedding_to_blob(embedding),
                        json.dumps(filtered_meta),
                    ),
                )

                # Sync to FTS5 index
                self._fts_sync_insert(cursor, doc_id, text, filtered_meta)

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug("Added %d documents to SQLite store", len(ids))

        except sqlite3.IntegrityError:
            # Document already exists, use upsert instead
            _LOGGER.debug("Some documents already exist, using upsert")
            await self.upsert_documents(ids, texts, embeddings, metadatas)
        except Exception as e:
            _LOGGER.error("Failed to add documents: %s", e)
            raise

    async def upsert_documents(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Upsert documents (add or update) in the store.

        Args:
            ids: Unique identifiers for each document.
            texts: Text content of each document.
            embeddings: Pre-computed embeddings for each document.
            metadatas: Optional metadata dictionaries for each document.
        """
        self._ensure_initialized()

        if not ids:
            _LOGGER.debug("No documents to upsert")
            return

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            # Delete old FTS5 entries for all upserted IDs (then re-insert below)
            self._fts_sync_delete(cursor, ids)

            for i, doc_id in enumerate(ids):
                text = texts[i] if i < len(texts) else ""
                embedding = embeddings[i] if i < len(embeddings) else []
                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                filtered_meta = filter_metadata(metadata)

                cursor.execute(
                    f"""
                    INSERT OR REPLACE INTO {self.table_name} (id, text, embedding, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        text,
                        embedding_to_blob(embedding),
                        json.dumps(filtered_meta),
                    ),
                )

                # Sync to FTS5 index
                self._fts_sync_insert(cursor, doc_id, text, filtered_meta)

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug("Upserted %d documents to SQLite store", len(ids))

        except Exception as e:
            _LOGGER.error("Failed to upsert documents: %s", e)
            raise

    async def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        min_similarity: float | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents using query embedding.

        Args:
            query_embedding: The embedding vector to search with.
            n_results: Maximum number of results to return.
            where: Optional filter conditions for metadata (simple equality only).
            min_similarity: Minimum cosine similarity (0-1) for results.

        Returns:
            List of SearchResult objects sorted by similarity (lowest distance first).
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]

            # Fetch all documents (for small datasets this is fine)
            cursor.execute(
                f"SELECT id, text, embedding, metadata FROM {self.table_name}"
            )
            rows = cursor.fetchall()

            # Compute similarities
            results_with_distance = []
            for row in rows:
                doc_id = row["id"]
                text = row["text"]
                embedding = read_embedding(row["embedding"])
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}

                # Apply where filter if provided
                if where:
                    match = True
                    for key, value in where.items():
                        if metadata.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue

                # Compute cosine distance
                distance = cosine_distance(query_embedding, embedding)
                results_with_distance.append(
                    SearchResult(
                        id=doc_id,
                        text=text,
                        metadata=metadata,
                        distance=distance,
                    )
                )

            # Apply similarity threshold filter if specified
            filtered_results = []
            if min_similarity is not None:
                for result in results_with_distance:
                    similarity = 1.0 - result.distance
                    if similarity >= min_similarity:
                        filtered_results.append(result)

                _LOGGER.debug(
                    "RAG similarity filter: %d/%d results above threshold %.2f",
                    len(filtered_results),
                    len(results_with_distance),
                    min_similarity,
                )
            else:
                filtered_results = results_with_distance

            # Sort by distance (ascending) and limit results
            filtered_results.sort(key=lambda x: x.distance)
            search_results = filtered_results[:n_results]

            _LOGGER.debug("Search returned %d results", len(search_results))
            return search_results

        except Exception as e:
            _LOGGER.error("Failed to search: %s", e)
            raise

    async def delete_documents(self, ids: list[str]) -> None:
        """Delete documents from the store by their IDs.

        Args:
            ids: List of document IDs to delete.
        """
        self._ensure_initialized()

        if not ids:
            _LOGGER.debug("No documents to delete")
            return

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            placeholders = ",".join("?" * len(ids))
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})",
                ids,
            )

            # Sync FTS5
            self._fts_sync_delete(cursor, ids)

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug("Deleted %d documents from SQLite store", cursor.rowcount)

        except Exception as e:
            _LOGGER.error("Failed to delete documents: %s", e)
            raise

    async def get_document_count(self) -> int:
        """Get the total number of documents in the store.

        Returns:
            Number of documents in the store.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            _LOGGER.error("Failed to get document count: %s", e)
            raise

    async def get_document(self, doc_id: str) -> SearchResult | None:
        """Get a specific document by its ID.

        Args:
            doc_id: The document ID to retrieve.

        Returns:
            SearchResult if found, None otherwise.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute(
                f"SELECT id, text, metadata FROM {self.table_name} WHERE id = ?",
                (doc_id,),
            )
            row = cursor.fetchone()

            if row:
                return SearchResult(
                    id=row["id"],
                    text=row["text"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    distance=0.0,
                )
            return None

        except Exception as e:
            _LOGGER.error("Failed to get document %s: %s", doc_id, e)
            raise

    async def clear_collection(self) -> None:
        """Clear all documents from the store."""
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute(f"DELETE FROM {self.table_name}")

            # Sync FTS5
            self._fts_sync_clear(cursor)

            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.info("Cleared all documents from SQLite store")

        except Exception as e:
            _LOGGER.error("Failed to clear collection: %s", e)
            raise

    # ------------------------------------------------------------------
    # RAG metadata key-value store
    # ------------------------------------------------------------------

    async def get_metadata(self, key: str) -> str | None:
        """Get metadata value by key.

        Args:
            key: The metadata key to retrieve.

        Returns:
            The metadata value if found, None otherwise.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute("SELECT value FROM rag_metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
        except Exception as e:
            _LOGGER.error("Failed to get metadata for key %s: %s", key, e)
            return None

    async def set_metadata(self, key: str, value: str) -> None:
        """Set metadata value.

        Args:
            key: The metadata key.
            value: The metadata value to store.
        """
        self._ensure_initialized()

        try:
            cursor = self._conn.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                INSERT OR REPLACE INTO rag_metadata (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, value, time.time()),
            )
            self._conn.commit()  # type: ignore[union-attr]
            _LOGGER.debug("Set metadata: %s = %s", key, value)
        except Exception as e:
            _LOGGER.error("Failed to set metadata %s: %s", key, e)
            raise

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def async_shutdown(self) -> None:
        """Shutdown the SQLite connection gracefully."""
        if self._conn:
            _LOGGER.debug("Shutting down SQLite store")
            self._conn.close()
            self._conn = None
            self._initialized = False

    # ------------------------------------------------------------------
    # Backward-compatible static method aliases
    # ------------------------------------------------------------------
    # These delegate to module-level functions in _store_utils so that
    # existing callers (memory_store, tests) using SqliteStore._embedding_to_blob()
    # continue to work unchanged.

    _embedding_to_blob = staticmethod(embedding_to_blob)  # type: ignore[assignment]
    _blob_to_embedding = staticmethod(blob_to_embedding)  # type: ignore[assignment]
    _read_embedding = staticmethod(read_embedding)  # type: ignore[assignment]
    _filter_metadata = staticmethod(filter_metadata)  # type: ignore[assignment]


# Alias for backwards compatibility
ChromaStore = SqliteStore
