"""Session indexer for RAG system.

Indexes conversation history as an additional RAG source.
Uses sliding window chunking with overlap, delta-based reindex,
and SHA-256 hash-based change detection.

Modeled after OpenClaw's session indexing approach, adapted for
Home Assistant's SessionStorage dataclass model.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .embeddings import EmbeddingProvider
    from .sqlite_store import SqliteStore

_LOGGER = logging.getLogger(__name__)

# Chunking configuration (matches OpenClaw defaults)
CHUNK_MAX_CHARS = 1600  # ~400 tokens * 4 chars/token
CHUNK_OVERLAP_CHARS = 320  # ~80 tokens * 4 chars/token

# Delta thresholds — reindex session only after enough new content
DELTA_MIN_MESSAGES = 4  # Minimum new messages before reindex

# Session indexing limits
MAX_SESSIONS_TO_INDEX = 50  # Don't index more than this many sessions
MIN_SESSION_MESSAGES = 2  # Skip sessions with fewer messages


@dataclass
class SessionChunk:
    """A chunk of conversation text with position metadata."""

    text: str
    start_msg: int  # Index of first message in chunk
    end_msg: int  # Index of last message in chunk
    hash: str  # SHA-256 of chunk text


def _hash_text(text: str) -> str:
    """Compute SHA-256 hash of text content.

    Args:
        text: Text to hash.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_conversation(
    messages: list[dict[str, str]],
    max_chars: int = CHUNK_MAX_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[SessionChunk]:
    """Split conversation messages into overlapping chunks using a sliding window.

    Each message is formatted as "User: ..." or "Assistant: ..." and joined
    with newlines. The window slides forward, carrying overlap from the
    previous chunk to maintain context continuity.

    Args:
        messages: List of dicts with 'role' and 'content' keys.
        max_chars: Maximum characters per chunk (~400 tokens).
        overlap_chars: Characters to carry over between chunks (~80 tokens).

    Returns:
        List of SessionChunk objects with text, message range, and hash.
    """
    if not messages:
        return []

    # Format messages as labeled lines
    lines: list[tuple[int, str]] = []  # (msg_index, formatted_line)
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "").strip()
        if not content:
            continue
        label = (
            "User"
            if role == "user"
            else "Assistant"
            if role == "assistant"
            else role.capitalize()
        )
        lines.append((i, f"{label}: {content}"))

    if not lines:
        return []

    chunks: list[SessionChunk] = []
    current: list[tuple[int, str]] = []  # (msg_index, line_text)
    current_chars = 0

    def flush() -> None:
        """Emit the current buffer as a chunk."""
        if not current:
            return
        text = "\n".join(line for _, line in current)
        chunks.append(
            SessionChunk(
                text=text,
                start_msg=current[0][0],
                end_msg=current[-1][0],
                hash=_hash_text(text),
            )
        )

    def carry_overlap() -> tuple[list[tuple[int, str]], int]:
        """Keep trailing lines up to overlap_chars for the next chunk."""
        if overlap_chars <= 0 or not current:
            return [], 0
        kept: list[tuple[int, str]] = []
        acc = 0
        for item in reversed(current):
            acc += len(item[1]) + 1  # +1 for newline
            kept.insert(0, item)
            if acc >= overlap_chars:
                break
        new_chars = sum(len(item[1]) + 1 for item in kept)
        return kept, new_chars

    for msg_idx, line_text in lines:
        line_len = len(line_text) + 1  # +1 for newline separator

        # If adding this line would exceed max_chars, flush and carry overlap
        if current_chars + line_len > max_chars and current:
            flush()
            current, current_chars = carry_overlap()

        current.append((msg_idx, line_text))
        current_chars += line_len

    # Flush remaining
    flush()

    return chunks


@dataclass
class SessionIndexer:
    """Indexes conversation sessions into the RAG SQLite store.

    Tracks per-session message counts to enable delta-based reindexing.
    Only re-chunks and re-embeds sessions that have enough new messages
    since the last index.

    Attributes:
        store: The SQLite vector store for persistence.
        embedding_provider: Provider for generating text embeddings.
        _delta_tracker: Maps session_id -> last indexed message count.
    """

    store: SqliteStore
    embedding_provider: EmbeddingProvider
    _delta_tracker: dict[str, int] = field(default_factory=dict, repr=False)

    async def index_session(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        *,
        force: bool = False,
    ) -> int:
        """Index or re-index a single conversation session.

        Checks delta threshold before reindexing. If the session hasn't
        accumulated enough new messages since last index, it's skipped
        (unless force=True).

        Args:
            session_id: Unique session identifier.
            messages: List of message dicts with 'role' and 'content' keys.
            force: If True, skip delta check and always reindex.

        Returns:
            Number of chunks indexed (0 if skipped).
        """
        # Filter to user/assistant messages only
        relevant = [
            m
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
        ]

        if len(relevant) < MIN_SESSION_MESSAGES:
            _LOGGER.debug(
                "Session %s has only %d messages, skipping indexing",
                session_id,
                len(relevant),
            )
            return 0

        # Delta check: skip if not enough new messages
        last_count = self._delta_tracker.get(session_id, 0)
        new_messages = len(relevant) - last_count

        if not force and new_messages < DELTA_MIN_MESSAGES:
            _LOGGER.debug(
                "Session %s: only %d new messages (need %d), skipping",
                session_id,
                new_messages,
                DELTA_MIN_MESSAGES,
            )
            return 0

        # Check content hash to avoid re-embedding identical content
        full_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'].strip()}"
            for m in relevant
        )
        content_hash = _hash_text(full_text)
        stored_hash = await self.store.get_session_hash(session_id)

        if not force and stored_hash == content_hash:
            _LOGGER.debug(
                "Session %s content unchanged (hash match), skipping", session_id
            )
            self._delta_tracker[session_id] = len(relevant)
            return 0

        # Chunk the conversation
        chunks = chunk_conversation(relevant)

        if not chunks:
            _LOGGER.debug("Session %s produced no chunks", session_id)
            return 0

        _LOGGER.info(
            "Indexing session %s: %d messages -> %d chunks",
            session_id,
            len(relevant),
            len(chunks),
        )

        # Generate embeddings for all chunk texts
        texts = [c.text for c in chunks]
        try:
            embeddings = await self.embedding_provider.get_embeddings(texts)
        except Exception as e:
            _LOGGER.error("Failed to embed session %s chunks: %s", session_id, e)
            return 0

        # Build chunk IDs and metadata
        chunk_ids: list[str] = []
        chunk_texts: list[str] = []
        chunk_metadatas: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            # Deterministic chunk ID: hash of session_id + chunk position + content hash
            chunk_id = _hash_text(
                f"session:{session_id}:{chunk.start_msg}:{chunk.end_msg}:{chunk.hash}"
            )
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk.text)
            chunk_metadatas.append(
                {
                    "session_id": session_id,
                    "start_msg": chunk.start_msg,
                    "end_msg": chunk.end_msg,
                    "chunk_index": i,
                    "source": "session",
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
        self._delta_tracker[session_id] = len(relevant)

        _LOGGER.info(
            "Indexed session %s: %d chunks stored",
            session_id,
            len(chunks),
        )
        return len(chunks)

    async def remove_session(self, session_id: str) -> None:
        """Remove all indexed chunks for a session.

        Args:
            session_id: Session to remove from the index.
        """
        await self.store.delete_session_chunks(session_id)
        self._delta_tracker.pop(session_id, None)
        _LOGGER.debug("Removed session %s from index", session_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get session indexing statistics.

        Returns:
            Dict with indexed session count, total chunks, etc.
        """
        stats = await self.store.get_session_chunk_stats()
        stats["tracked_sessions"] = len(self._delta_tracker)
        return stats
