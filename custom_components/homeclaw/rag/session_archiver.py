"""Session archiver — compresses old session chunks into a single knowledge summary.

When the number of indexed sessions exceeds MAX_INDEXED_SESSIONS, the archiver
collects all chunks from sessions older than ARCHIVE_AGE_DAYS, sends them to
an LLM for summarization, and replaces them with a single dense "archive" chunk.

This keeps the session RAG index bounded while preserving long-term knowledge
(preferences, decisions, interesting facts) from older conversations.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .embeddings import EmbeddingProvider
    from .sqlite_store import SqliteStore

_LOGGER = logging.getLogger(__name__)

# --- Configuration ---

# Trigger archival when indexed sessions exceed this count
MAX_INDEXED_SESSIONS = 50

# Only archive sessions whose chunks are older than this (days)
ARCHIVE_AGE_DAYS = 7

# Maximum text to send per LLM summarization call
MAX_ARCHIVE_INPUT_CHARS = 15_000

# Session ID used for the archive summary chunk
ARCHIVE_SESSION_ID = "__archive__"


# --- Prompt ---

ARCHIVE_SUMMARY_PROMPT = """\
You are a knowledge distiller for a Home Assistant AI assistant's long-term memory.

You will receive conversation chunks from multiple old sessions. Your task is to
produce ONE dense knowledge summary that captures everything worth remembering.

CRITICAL RULE — LANGUAGE PRESERVATION:
Write in the SAME LANGUAGE as the input. If Polish, output Polish. If English,
output English. If mixed, preserve each part's language. NEVER translate.

KEEP (valuable long-term knowledge):
- User preferences: lighting, temperature, routines, naming conventions
- Decisions made: which automations were created, how things were configured
- Device/entity relationships: which rooms, which devices, naming patterns
- Interesting facts about the user or household
- Corrections and feedback about the assistant's behavior
- Anything the user explicitly asked to remember

REMOVE (worthless for long-term):
- All sensor readings and entity states (temperatures, on/off, humidity, etc.)
- Greetings, small talk, confirmations ("ok", "thanks", "sure")
- Troubleshooting steps that were already resolved
- Repetitive information already covered
- Status reports and device listings

OUTPUT FORMAT:
- Write a single continuous summary, organized by topic
- Use bullet points or short paragraphs
- Be dense: aim for maximum information per character
- Target 500-1500 characters depending on how much valuable content exists
- If there is almost no valuable content, output a very short summary
- Output ONLY the summary, no headers or commentary"""


async def archive_old_sessions(
    store: SqliteStore,
    embedding_provider: EmbeddingProvider,
    provider: Any,
    model: str | None = None,
) -> dict[str, Any]:
    """Check if archival is needed and compress old session chunks.

    Counts indexed sessions. If count exceeds MAX_INDEXED_SESSIONS, collects
    chunks older than ARCHIVE_AGE_DAYS, summarizes them via LLM, and replaces
    them with a single archive chunk.

    Args:
        store: SQLite store for chunk operations.
        embedding_provider: For embedding the archive summary.
        provider: AI provider instance with get_response().
        model: Optional model override for the LLM call.

    Returns:
        Dict with archival stats: sessions_archived, chunks_removed,
        archive_created (bool), or empty dict if no archival needed.
    """
    try:
        stats = await store.get_session_chunk_stats()
        indexed_sessions = stats.get("indexed_sessions", 0)

        if indexed_sessions <= MAX_INDEXED_SESSIONS:
            _LOGGER.debug(
                "Session count %d <= %d limit, no archival needed",
                indexed_sessions,
                MAX_INDEXED_SESSIONS,
            )
            return {}

        _LOGGER.info(
            "Session count %d exceeds limit %d, starting archival",
            indexed_sessions,
            MAX_INDEXED_SESSIONS,
        )

        # Find sessions with chunks older than ARCHIVE_AGE_DAYS
        cutoff_time = time.time() - (ARCHIVE_AGE_DAYS * 86400)
        old_sessions = await _find_old_sessions(store, cutoff_time)

        if not old_sessions:
            _LOGGER.debug("No sessions older than %d days to archive", ARCHIVE_AGE_DAYS)
            return {}

        # Collect all chunks from old sessions
        all_old_chunks = await _collect_chunks(store, old_sessions)

        if not all_old_chunks:
            _LOGGER.debug("No chunks found in old sessions")
            return {}

        # Summarize via LLM
        summary_text = await _summarize_chunks(all_old_chunks, provider, model)

        if not summary_text:
            _LOGGER.warning("LLM summarization returned empty, skipping archival")
            return {}

        # Embed the summary
        embeddings = await embedding_provider.get_embeddings([summary_text])
        if not embeddings:
            _LOGGER.warning("Failed to embed archive summary")
            return {}

        # Delete old session chunks and their hashes
        chunks_removed = 0
        for session_id in old_sessions:
            await store.delete_session_chunks(session_id)
            chunks_removed += old_sessions[session_id]

        # Store the archive summary as a single chunk
        now = time.time()
        archive_id = hashlib.sha256(
            f"archive:{now}:{summary_text[:100]}".encode()
        ).hexdigest()[:24]

        await store.add_session_chunks(
            ids=[f"archive_{archive_id}"],
            texts=[summary_text],
            embeddings=embeddings,
            metadatas=[
                {
                    "session_id": ARCHIVE_SESSION_ID,
                    "start_msg": 0,
                    "end_msg": 0,
                    "source": "archive",
                    "archived_sessions": len(old_sessions),
                    "archived_chunks": chunks_removed,
                    "archived_at": now,
                }
            ],
            session_id=ARCHIVE_SESSION_ID,
            content_hash=hashlib.sha256(summary_text.encode()).hexdigest(),
        )

        result = {
            "sessions_archived": len(old_sessions),
            "chunks_removed": chunks_removed,
            "archive_created": True,
            "summary_length": len(summary_text),
        }

        _LOGGER.info(
            "Archived %d sessions (%d chunks) into 1 summary chunk (%d chars)",
            len(old_sessions),
            chunks_removed,
            len(summary_text),
        )

        return result

    except Exception as e:
        _LOGGER.warning("Session archival failed: %s", e)
        return {}


async def _find_old_sessions(
    store: SqliteStore,
    cutoff_time: float,
) -> dict[str, int]:
    """Find sessions whose most recent chunk is older than cutoff_time.

    Args:
        store: SQLite store.
        cutoff_time: Unix timestamp — sessions with all chunks before this are old.

    Returns:
        Dict mapping session_id -> chunk_count for old sessions.
        Excludes the archive session itself.
    """
    try:
        conn = store._conn
        if not conn:
            return {}
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, COUNT(*) as cnt, MAX(updated_at) as newest
            FROM session_chunks
            WHERE session_id != ?
            GROUP BY session_id
            HAVING newest < ?
            """,
            (ARCHIVE_SESSION_ID, cutoff_time),
        )
        return {row["session_id"]: row["cnt"] for row in cursor.fetchall()}
    except Exception as e:
        _LOGGER.error("Failed to find old sessions: %s", e)
        return {}


async def _collect_chunks(
    store: SqliteStore,
    sessions: dict[str, int],
) -> list[str]:
    """Collect chunk texts from the given sessions.

    Args:
        store: SQLite store.
        sessions: Dict of session_id -> chunk_count.

    Returns:
        List of chunk text strings, ordered by session and position.
    """
    try:
        conn = store._conn
        if not conn:
            return []

        all_texts: list[str] = []
        cursor = conn.cursor()

        for session_id in sessions:
            cursor.execute(
                """
                SELECT text FROM session_chunks
                WHERE session_id = ?
                ORDER BY start_msg ASC
                """,
                (session_id,),
            )
            for row in cursor.fetchall():
                if row["text"]:
                    all_texts.append(row["text"])

        return all_texts
    except Exception as e:
        _LOGGER.error("Failed to collect chunks for archival: %s", e)
        return []


async def _summarize_chunks(
    chunks: list[str],
    provider: Any,
    model: str | None,
) -> str | None:
    """Send chunks to LLM for summarization into a single knowledge block.

    Truncates input to MAX_ARCHIVE_INPUT_CHARS. If chunks exceed this,
    only the most recent ones (end of list) are included.

    Args:
        chunks: List of chunk text strings.
        provider: AI provider with get_response().
        model: Optional model override.

    Returns:
        Summary text or None on failure.
    """
    combined = "\n---\n".join(chunks)

    # Truncate from the beginning (keep most recent chunks at the end)
    if len(combined) > MAX_ARCHIVE_INPUT_CHARS:
        combined = combined[-MAX_ARCHIVE_INPUT_CHARS:]
        # Clean up partial chunk at the start
        first_sep = combined.find("\n---\n")
        if first_sep > 0:
            combined = combined[first_sep + 5 :]

    messages = [
        {"role": "system", "content": ARCHIVE_SUMMARY_PROMPT},
        {
            "role": "user",
            "content": (
                f"Summarize these conversation chunks from {len(chunks)} old sessions "
                f"into one dense knowledge block:\n\n{combined}"
            ),
        },
    ]

    kwargs: dict[str, Any] = {}
    if model:
        kwargs["model"] = model

    try:
        response = await provider.get_response(messages, **kwargs)
        if response and response.strip():
            return response.strip()
        return None
    except Exception as e:
        _LOGGER.warning("Archive summarization LLM call failed: %s", e)
        return None
