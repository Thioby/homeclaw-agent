"""Tests for the session archiver (auto-compression of old session chunks)."""

from __future__ import annotations

import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.homeclaw.rag.session_archiver import (
    archive_old_sessions,
    _find_old_sessions,
    _collect_chunks,
    _summarize_chunks,
    ARCHIVE_SESSION_ID,
    ARCHIVE_SUMMARY_PROMPT,
    MAX_INDEXED_SESSIONS,
    ARCHIVE_AGE_DAYS,
    MAX_ARCHIVE_INPUT_CHARS,
)


# --- Helpers ---


def _make_store(sessions: dict[str, list[dict]] | None = None):
    """Create a mock SqliteStore with session chunks data.

    Args:
        sessions: Dict mapping session_id -> list of chunk dicts.
            Each chunk dict has 'text', 'updated_at' keys.
    """
    sessions = sessions or {}
    store = AsyncMock()

    # Build chunk rows for the DB simulation
    all_rows = []
    for sid, chunks in sessions.items():
        for i, chunk in enumerate(chunks):
            all_rows.append(
                {
                    "session_id": sid,
                    "text": chunk.get("text", f"chunk {i}"),
                    "updated_at": chunk.get("updated_at", time.time()),
                    "start_msg": i * 2,
                    "end_msg": i * 2 + 1,
                }
            )

    # get_session_chunk_stats
    indexed = len(sessions)
    total_chunks = sum(len(c) for c in sessions.values())
    store.get_session_chunk_stats = AsyncMock(
        return_value={
            "total_chunks": total_chunks,
            "indexed_sessions": indexed,
            "total_bytes": total_chunks * 1000,
            "total_mb": round(total_chunks * 1000 / (1024 * 1024), 2),
        }
    )

    # Simulate _conn for direct SQL queries
    mock_conn = MagicMock()
    store._conn = mock_conn

    # Cursor that responds to different queries
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    def execute_side_effect(sql, params=None):
        """Route SQL queries to appropriate mock data."""
        if "GROUP BY session_id" in sql:
            # _find_old_sessions query
            cutoff = params[1] if params and len(params) > 1 else 0
            archive_id = params[0] if params else ARCHIVE_SESSION_ID
            results = []
            for sid, chunks in sessions.items():
                if sid == archive_id:
                    continue
                newest = max(c.get("updated_at", 0) for c in chunks)
                if newest < cutoff:
                    results.append(
                        {"session_id": sid, "cnt": len(chunks), "newest": newest}
                    )
            mock_cursor.fetchall.return_value = results
        elif "WHERE session_id = ?" in sql and "ORDER BY" in sql:
            # _collect_chunks query
            sid = params[0] if params else ""
            chunk_rows = [{"text": c.get("text", "")} for c in sessions.get(sid, [])]
            mock_cursor.fetchall.return_value = chunk_rows

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    # delete_session_chunks and add_session_chunks
    store.delete_session_chunks = AsyncMock()
    store.add_session_chunks = AsyncMock()

    return store


def _make_provider(response: str = "Summary of archived conversations."):
    """Create a mock AI provider."""
    provider = AsyncMock()
    provider.get_response = AsyncMock(return_value=response)
    return provider


def _make_embedding_provider(dim: int = 768):
    """Create a mock embedding provider."""
    ep = AsyncMock()
    ep.get_embeddings = AsyncMock(return_value=[[0.1] * dim])
    return ep


# --- archive_old_sessions tests ---


@pytest.mark.asyncio
class TestArchiveOldSessions:
    """Tests for the main archive_old_sessions function."""

    async def test_no_archival_under_limit(self):
        """No archival when session count is below MAX_INDEXED_SESSIONS."""
        store = _make_store({"s1": [{"text": "hello"}]})
        provider = _make_provider()
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        assert result == {}
        provider.get_response.assert_not_called()

    async def test_archival_triggered_over_limit(self):
        """Archival triggers when session count exceeds limit."""
        old_time = time.time() - (ARCHIVE_AGE_DAYS + 1) * 86400

        # Create MAX_INDEXED_SESSIONS + 5 sessions, some old
        sessions = {}
        for i in range(MAX_INDEXED_SESSIONS + 5):
            if i < 10:
                # 10 old sessions
                sessions[f"old_{i}"] = [
                    {
                        "text": f"Old conversation {i} about lights",
                        "updated_at": old_time,
                    }
                ]
            else:
                # Recent sessions
                sessions[f"new_{i}"] = [
                    {"text": f"Recent conversation {i}", "updated_at": time.time()}
                ]

        store = _make_store(sessions)
        provider = _make_provider("Archived knowledge: user prefers warm lights")
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        assert result.get("sessions_archived") == 10
        assert result.get("chunks_removed") == 10
        assert result.get("archive_created") is True
        assert result.get("summary_length") > 0

        # Verify old sessions were deleted
        assert store.delete_session_chunks.call_count == 10

        # Verify archive chunk was stored
        store.add_session_chunks.assert_called_once()
        call_kwargs = store.add_session_chunks.call_args
        assert call_kwargs[1]["session_id"] == ARCHIVE_SESSION_ID

    async def test_no_old_sessions_above_cutoff(self):
        """No archival if all sessions are recent despite exceeding count."""
        sessions = {}
        for i in range(MAX_INDEXED_SESSIONS + 5):
            sessions[f"s_{i}"] = [
                {"text": f"Recent chat {i}", "updated_at": time.time()}
            ]

        store = _make_store(sessions)
        provider = _make_provider()
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        assert result == {}
        provider.get_response.assert_not_called()

    async def test_empty_llm_response_skips(self):
        """Empty LLM response skips archival."""
        old_time = time.time() - (ARCHIVE_AGE_DAYS + 1) * 86400
        sessions = {}
        for i in range(MAX_INDEXED_SESSIONS + 5):
            sessions[f"s_{i}"] = [{"text": f"Chat {i}", "updated_at": old_time}]

        store = _make_store(sessions)
        provider = _make_provider("")  # Empty response
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        assert result == {}
        store.delete_session_chunks.assert_not_called()

    async def test_embedding_failure_skips(self):
        """Embedding failure prevents archival."""
        old_time = time.time() - (ARCHIVE_AGE_DAYS + 1) * 86400
        sessions = {}
        for i in range(MAX_INDEXED_SESSIONS + 5):
            sessions[f"s_{i}"] = [{"text": f"Chat {i}", "updated_at": old_time}]

        store = _make_store(sessions)
        provider = _make_provider("Good summary")
        ep = _make_embedding_provider()
        ep.get_embeddings = AsyncMock(return_value=[])  # Empty embeddings

        result = await archive_old_sessions(store, ep, provider)

        assert result == {}
        store.delete_session_chunks.assert_not_called()

    async def test_exception_returns_empty(self):
        """Exception during archival returns empty dict gracefully."""
        store = AsyncMock()
        store.get_session_chunk_stats = AsyncMock(side_effect=RuntimeError("DB error"))
        provider = _make_provider()
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        assert result == {}

    async def test_archive_excludes_existing_archive_session(self):
        """The archive session ID itself is not re-archived."""
        old_time = time.time() - (ARCHIVE_AGE_DAYS + 1) * 86400
        sessions = {
            ARCHIVE_SESSION_ID: [
                {"text": "Previous archive summary", "updated_at": old_time}
            ],
        }
        # Add enough sessions to trigger
        for i in range(MAX_INDEXED_SESSIONS + 5):
            sessions[f"s_{i}"] = [{"text": f"Chat {i}", "updated_at": old_time}]

        store = _make_store(sessions)
        provider = _make_provider("New archive")
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        # Archive session should not be in the deleted set
        deleted_ids = [
            call.args[0] for call in store.delete_session_chunks.call_args_list
        ]
        assert ARCHIVE_SESSION_ID not in deleted_ids

    async def test_multiple_chunks_per_session(self):
        """Sessions with multiple chunks are all collected and deleted."""
        old_time = time.time() - (ARCHIVE_AGE_DAYS + 1) * 86400
        sessions = {}
        for i in range(MAX_INDEXED_SESSIONS + 3):
            sessions[f"s_{i}"] = [
                {"text": f"Chunk A of session {i}", "updated_at": old_time},
                {"text": f"Chunk B of session {i}", "updated_at": old_time},
                {"text": f"Chunk C of session {i}", "updated_at": old_time},
            ]

        store = _make_store(sessions)
        provider = _make_provider("Comprehensive archive summary")
        ep = _make_embedding_provider()

        result = await archive_old_sessions(store, ep, provider)

        total_sessions = MAX_INDEXED_SESSIONS + 3
        assert result.get("sessions_archived") == total_sessions
        assert result.get("chunks_removed") == total_sessions * 3


# --- _find_old_sessions tests ---


@pytest.mark.asyncio
class TestFindOldSessions:
    """Tests for finding sessions eligible for archival."""

    async def test_finds_old_sessions(self):
        """Returns sessions whose newest chunk is before cutoff."""
        old_time = time.time() - 30 * 86400  # 30 days old
        sessions = {
            "old1": [{"text": "x", "updated_at": old_time}],
            "recent1": [{"text": "y", "updated_at": time.time()}],
        }
        store = _make_store(sessions)
        cutoff = time.time() - 7 * 86400

        result = await _find_old_sessions(store, cutoff)

        assert "old1" in result
        assert "recent1" not in result

    async def test_empty_when_no_old(self):
        """Returns empty dict when all sessions are recent."""
        sessions = {
            "s1": [{"text": "x", "updated_at": time.time()}],
        }
        store = _make_store(sessions)
        cutoff = time.time() - 7 * 86400

        result = await _find_old_sessions(store, cutoff)
        assert result == {}

    async def test_excludes_archive_session(self):
        """The archive session ID is never returned as old."""
        old_time = time.time() - 30 * 86400
        sessions = {
            ARCHIVE_SESSION_ID: [{"text": "x", "updated_at": old_time}],
            "real_session": [{"text": "y", "updated_at": old_time}],
        }
        store = _make_store(sessions)
        cutoff = time.time() - 7 * 86400

        result = await _find_old_sessions(store, cutoff)

        assert ARCHIVE_SESSION_ID not in result
        assert "real_session" in result

    async def test_handles_db_error(self):
        """Returns empty dict on database error."""
        store = MagicMock()
        store._conn = None

        result = await _find_old_sessions(store, time.time())
        assert result == {}


# --- _collect_chunks tests ---


@pytest.mark.asyncio
class TestCollectChunks:
    """Tests for collecting chunk texts from sessions."""

    async def test_collects_all_texts(self):
        """Returns all chunk texts ordered by session."""
        sessions = {
            "s1": [
                {"text": "First chunk", "updated_at": 100},
                {"text": "Second chunk", "updated_at": 100},
            ],
            "s2": [
                {"text": "Third chunk", "updated_at": 100},
            ],
        }
        store = _make_store(sessions)

        result = await _collect_chunks(store, {"s1": 2, "s2": 1})

        assert len(result) == 3
        assert "First chunk" in result
        assert "Third chunk" in result

    async def test_empty_for_no_sessions(self):
        """Returns empty list when no sessions provided."""
        store = _make_store({})
        result = await _collect_chunks(store, {})
        assert result == []

    async def test_handles_db_error(self):
        """Returns empty list on database error."""
        store = MagicMock()
        store._conn = None

        result = await _collect_chunks(store, {"s1": 2})
        assert result == []


# --- _summarize_chunks tests ---


@pytest.mark.asyncio
class TestSummarizeChunks:
    """Tests for LLM summarization of chunks."""

    async def test_basic_summarization(self):
        """Sends chunks to LLM and returns response."""
        provider = _make_provider("User prefers warm lights in bedroom.")
        chunks = ["User: I like warm light", "Assistant: Noted, warm light preference."]

        result = await _summarize_chunks(chunks, provider, None)

        assert result == "User prefers warm lights in bedroom."
        provider.get_response.assert_called_once()

        # Verify the prompt structure
        call_args = provider.get_response.call_args[0][0]
        assert call_args[0]["role"] == "system"
        assert call_args[0]["content"] == ARCHIVE_SUMMARY_PROMPT
        assert call_args[1]["role"] == "user"

    async def test_model_override(self):
        """Model parameter is forwarded to provider."""
        provider = _make_provider("Summary")
        chunks = ["chunk1"]

        await _summarize_chunks(chunks, provider, "gemini-2.0-flash")

        call_kwargs = provider.get_response.call_args[1]
        assert call_kwargs["model"] == "gemini-2.0-flash"

    async def test_no_model_no_kwarg(self):
        """No model kwarg when model is None."""
        provider = _make_provider("Summary")
        chunks = ["chunk1"]

        await _summarize_chunks(chunks, provider, None)

        call_kwargs = provider.get_response.call_args[1]
        assert "model" not in call_kwargs

    async def test_empty_response_returns_none(self):
        """Empty LLM response returns None."""
        provider = _make_provider("")
        result = await _summarize_chunks(["chunk"], provider, None)
        assert result is None

    async def test_whitespace_response_returns_none(self):
        """Whitespace-only LLM response returns None."""
        provider = _make_provider("   \n  ")
        result = await _summarize_chunks(["chunk"], provider, None)
        assert result is None

    async def test_exception_returns_none(self):
        """LLM exception returns None."""
        provider = AsyncMock()
        provider.get_response = AsyncMock(side_effect=RuntimeError("API error"))

        result = await _summarize_chunks(["chunk"], provider, None)
        assert result is None

    async def test_truncation_long_input(self):
        """Long input is truncated to MAX_ARCHIVE_INPUT_CHARS."""
        provider = _make_provider("Summary")
        # Create chunks that exceed the limit
        chunks = [f"Long chunk number {i} " * 200 for i in range(100)]

        await _summarize_chunks(chunks, provider, None)

        # Verify the input was truncated
        call_args = provider.get_response.call_args[0][0]
        user_content = call_args[1]["content"]
        # The combined text should be within limits (prompt + truncated content)
        assert (
            len(user_content) < MAX_ARCHIVE_INPUT_CHARS + 500
        )  # Some overhead for prompt text


# --- Prompt content tests ---


class TestPromptContent:
    """Tests for the archive summary prompt."""

    def test_prompt_mentions_language_preservation(self):
        """Prompt requires preserving original language."""
        assert "SAME LANGUAGE" in ARCHIVE_SUMMARY_PROMPT

    def test_prompt_mentions_removing_states(self):
        """Prompt instructs to remove sensor readings and states."""
        assert "sensor readings" in ARCHIVE_SUMMARY_PROMPT
        assert "on/off" in ARCHIVE_SUMMARY_PROMPT

    def test_prompt_mentions_keeping_preferences(self):
        """Prompt instructs to keep user preferences."""
        assert "preferences" in ARCHIVE_SUMMARY_PROMPT.lower()

    def test_prompt_mentions_keeping_decisions(self):
        """Prompt instructs to keep decisions."""
        assert "Decisions" in ARCHIVE_SUMMARY_PROMPT

    def test_prompt_mentions_interesting_facts(self):
        """Prompt instructs to keep interesting facts."""
        assert "facts" in ARCHIVE_SUMMARY_PROMPT.lower()


# --- Constants tests ---


class TestConstants:
    """Tests for archiver configuration constants."""

    def test_max_sessions_reasonable(self):
        """MAX_INDEXED_SESSIONS is a reasonable limit."""
        assert 20 <= MAX_INDEXED_SESSIONS <= 200

    def test_archive_age_positive(self):
        """ARCHIVE_AGE_DAYS is positive."""
        assert ARCHIVE_AGE_DAYS > 0

    def test_archive_session_id_distinct(self):
        """Archive session ID is clearly distinct from regular UUIDs."""
        assert ARCHIVE_SESSION_ID.startswith("__")

    def test_max_input_chars_reasonable(self):
        """MAX_ARCHIVE_INPUT_CHARS allows enough context."""
        assert MAX_ARCHIVE_INPUT_CHARS >= 10_000
