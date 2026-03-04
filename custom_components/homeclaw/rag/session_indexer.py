"""Session indexer for RAG system.

Indexes conversation history as an additional RAG source.
Uses round-level granularity (User + Assistant) with Key Expansion
(Original text + Extracted User Facts) for better retrieval.

Delta-based reindex and SHA-256 hash-based change detection is maintained
from the previous chunk-based approach.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .embeddings import EmbeddingProvider
    from .sqlite_store import SqliteStore

_LOGGER = logging.getLogger(__name__)

# Delta thresholds — reindex session only after enough new rounds
DELTA_MIN_ROUNDS = 2  # Minimum new rounds before reindex

# Hard cap on characters per round sent to embedding API.
# Prevents oversized messages from causing embedding failures.
MAX_ROUND_CHARS = 2000


def _hash_text(text: str) -> str:
    """Compute SHA-256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class SessionIndexer:
    """Indexes conversation sessions into the RAG SQLite store.

    Tracks per-session round counts to enable delta-based reindexing.
    Only re-embeds sessions that have enough new rounds since the last index.

    Attributes:
        store: The SQLite vector store for persistence.
        embedding_provider: Provider for generating text embeddings.
        _delta_tracker: Maps session_id -> last indexed round count.
    """

    store: SqliteStore
    embedding_provider: EmbeddingProvider
    _delta_tracker: dict[str, int] = field(default_factory=dict, repr=False)

    async def index_session(
        self,
        session_id: str,
        rounds: list[dict[str, Any]],
        *,
        force: bool = False,
    ) -> int:
        """Index or re-index a single conversation session.

        Expects a list of sanitized rounds (with facts and timestamps).

        Args:
            session_id: Unique session identifier.
            rounds: List of dicts with 'user_message', 'assistant_message', 'user_facts', 'timestamp'.
            force: If True, skip delta check and always reindex.

        Returns:
            Number of rounds indexed (0 if skipped).
        """
        # Ensure we have valid rounds
        valid_rounds = [
            r
            for r in rounds
            if isinstance(r, dict) and "user_message" in r and "assistant_message" in r
        ]

        if not valid_rounds:
            _LOGGER.debug(
                "Session %s has no valid rounds, skipping indexing", session_id
            )
            return 0

        # Delta check: skip if not enough new rounds
        last_count = self._delta_tracker.get(session_id, 0)
        new_rounds_count = len(valid_rounds) - last_count

        if not force and new_rounds_count < DELTA_MIN_ROUNDS:
            _LOGGER.debug(
                "Session %s: only %d new rounds (need %d), skipping",
                session_id,
                new_rounds_count,
                DELTA_MIN_ROUNDS,
            )
            return 0

        # Check content hash to avoid re-embedding identical content
        # We hash the concatenated user and assistant messages + facts
        full_text = "\n".join(
            f"User: {r['user_message']}\nAssistant: {r['assistant_message']}\nFacts: {r.get('user_facts', '')}"
            for r in valid_rounds
        )
        content_hash = _hash_text(full_text)
        stored_hash = await self.store.get_session_hash(session_id)

        if not force and stored_hash == content_hash:
            _LOGGER.debug(
                "Session %s content unchanged (hash match), skipping", session_id
            )
            self._delta_tracker[session_id] = len(valid_rounds)
            return 0

        _LOGGER.info(
            "Indexing session %s: %d rounds",
            session_id,
            len(valid_rounds),
        )

        # Generate embeddings for all rounds.
        # KEY EXPANSION: The embedding key is a combination of the conversation text AND the extracted facts.
        # Truncate to MAX_ROUND_CHARS to prevent embedding API failures on oversized messages.
        keys_for_embedding = []
        for r in valid_rounds:
            key = f"User: {r['user_message']}\nAssistant: {r['assistant_message']}"
            facts = r.get("user_facts", "").strip()
            if facts:
                key += f"\nUser Facts: {facts}"
            if len(key) > MAX_ROUND_CHARS:
                key = key[:MAX_ROUND_CHARS]
            keys_for_embedding.append(key)

        try:
            embeddings = await self.embedding_provider.get_embeddings(
                keys_for_embedding
            )
        except Exception as e:
            _LOGGER.error("Failed to embed session %s rounds: %s", session_id, e)
            return 0

        # Build chunk IDs and metadata
        chunk_ids: list[str] = []
        chunk_texts: list[str] = []
        chunk_metadatas: list[dict[str, Any]] = []

        for i, (r, key_text) in enumerate(zip(valid_rounds, keys_for_embedding)):
            # Deterministic ID for the round
            round_id = _hash_text(
                f"session:{session_id}:round:{i}:{_hash_text(key_text)}"
            )

            chunk_ids.append(round_id)
            # What we retrieve as VALUE is the original text (without facts polluting it)
            # so we store the same combined text with a timestamp
            value_text = f"[{r.get('timestamp', '')}] User: {r['user_message']}\nAssistant: {r['assistant_message']}"
            chunk_texts.append(value_text)

            chunk_metadatas.append(
                {
                    "session_id": session_id,
                    "round_index": i,
                    "start_msg": i * 2,
                    "end_msg": i * 2 + 1,
                    "timestamp": r.get("timestamp", ""),
                    "source": "session_round",
                }
            )

        # Delete old chunks for this session, then insert new ones
        await self.store.delete_session_chunks(session_id)
        await self.store.add_session_chunks(
            ids=chunk_ids,
            texts=chunk_texts,
            embeddings=embeddings,
            metadatas=chunk_metadatas,
            session_id=session_id,
            content_hash=content_hash,
        )

        # Update delta tracker
        self._delta_tracker[session_id] = len(valid_rounds)

        _LOGGER.info(
            "Indexed session %s: %d rounds stored", session_id, len(valid_rounds)
        )
        return len(valid_rounds)

    async def remove_session(self, session_id: str) -> None:
        """Remove all indexed chunks for a session."""
        await self.store.delete_session_chunks(session_id)
        self._delta_tracker.pop(session_id, None)
        _LOGGER.debug("Removed session %s from index", session_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get session indexing statistics."""
        stats = await self.store.get_session_chunk_stats()
        stats["tracked_sessions"] = len(self._delta_tracker)
        return stats
