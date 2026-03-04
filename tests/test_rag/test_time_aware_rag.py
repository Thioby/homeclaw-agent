"""Tests for time-aware RAG functionality."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from custom_components.homeclaw.rag._store_utils import SearchResult
from custom_components.homeclaw.rag.context_retriever import _has_temporal_hint
from custom_components.homeclaw.rag.sqlite_store import SqliteStore


@pytest_asyncio.fixture
async def store(tmp_path):
    """Create a temporary SQLite store."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()
    return store


@pytest_asyncio.fixture
async def populated_store(store):
    """Create a populated store with session chunks for various dates."""
    # We directly manipulate the database to bypass embedding delays
    cursor = store._conn.cursor()

    # Add a mock session hash to satisfy foreign keys / constraints if any
    cursor.execute(
        "INSERT INTO session_hashes (session_id, content_hash, chunk_count, updated_at) VALUES (?, ?, ?, ?)",
        ("session1", "hash1", 4, 0.0),
    )

    # 1. Start of month
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "chunk1",
            "session1",
            "What happened on the first?",
            json.dumps({"timestamp": "2024-03-01T10:00:00+00:00", "source": "test"}),
            0,
            1,
            0.0,
            "2024-03-01T10:00:00+00:00",
        ),
    )

    # 2. Middle of month
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "chunk2",
            "session1",
            "What happened on the ides?",
            json.dumps({"timestamp": "2024-03-15T10:00:00+00:00", "source": "test"}),
            2,
            3,
            0.0,
            "2024-03-15T10:00:00+00:00",
        ),
    )

    # 3. End of month (with timezone)
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "chunk3",
            "session1",
            "What happened on the last day?",
            json.dumps({"timestamp": "2024-03-31T23:59:59+00:00", "source": "test"}),
            4,
            5,
            0.0,
            "2024-03-31T23:59:59+00:00",
        ),
    )

    # 4. Next month
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "chunk4",
            "session1",
            "April fools!",
            json.dumps({"timestamp": "2024-04-01T00:00:00+00:00", "source": "test"}),
            6,
            7,
            0.0,
            "2024-04-01T00:00:00+00:00",
        ),
    )

    # FTS entries
    if store._fts_available:
        cursor.execute(
            "INSERT INTO session_chunks_fts (text, chunk_id, session_id) VALUES (?, ?, ?)",
            ("What happened on the first?", "chunk1", "session1"),
        )
        cursor.execute(
            "INSERT INTO session_chunks_fts (text, chunk_id, session_id) VALUES (?, ?, ?)",
            ("What happened on the ides?", "chunk2", "session1"),
        )
        cursor.execute(
            "INSERT INTO session_chunks_fts (text, chunk_id, session_id) VALUES (?, ?, ?)",
            ("What happened on the last day?", "chunk3", "session1"),
        )
        cursor.execute(
            "INSERT INTO session_chunks_fts (text, chunk_id, session_id) VALUES (?, ?, ?)",
            ("April fools!", "chunk4", "session1"),
        )

    store._conn.commit()
    return store


@pytest.mark.asyncio
async def test_search_session_chunks_date_filter(populated_store):
    """Test date filtering logic in search_session_chunks."""
    # Since we can't easily mock embeddings, we use the vector length
    # Our DB has zeroblob(16), we can just query without min_similarity

    # Test 1: Full range for March
    results = await populated_store.search_session_chunks(
        query_embedding=[0.0] * 4,  # dummy embedding
        start_date="2024-03-01",
        end_date="2024-03-31",
    )

    # Verify results
    assert len(results) > 0
    ids = [r.id for r in results]
    assert "chunk1" in ids
    assert "chunk2" in ids
    # chunk3 is correctly included with boundary fix
    assert "chunk3" in ids
    assert "chunk4" not in ids


@pytest.mark.asyncio
async def test_keyword_search_sessions_date_filter(populated_store):
    """Test date filtering logic in keyword_search_sessions."""
    if not populated_store._fts_available:
        pytest.skip("FTS5 not available")

    # Test 1: Search for "happened" in March
    results = await populated_store.keyword_search_sessions(
        fts_query="happened",
        start_date="2024-03-01",
        end_date="2024-03-31",
    )

    assert len(results) > 0
    ids = [r.id for r in results]
    assert "chunk1" in ids
    assert "chunk2" in ids
    assert "chunk3" in ids
    assert "chunk4" not in ids


@pytest_asyncio.fixture
async def store_with_empty_timestamps(store):
    """Create a store with a mix of timestamped and empty-timestamp rows."""
    cursor = store._conn.cursor()

    cursor.execute(
        "INSERT INTO session_hashes (session_id, content_hash, chunk_count, updated_at) VALUES (?, ?, ?, ?)",
        ("session_empty", "hash_empty", 3, 0.0),
    )

    # Row with proper timestamp
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "ts_chunk1",
            "session_empty",
            "Discussed bedroom lights configuration",
            json.dumps({"timestamp": "2024-03-15T10:00:00+00:00"}),
            0,
            1,
            0.0,
            "2024-03-15T10:00:00+00:00",
        ),
    )

    # Row with EMPTY timestamp (legacy / migration artifact)
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "ts_chunk_empty",
            "session_empty",
            "Undated legacy lights discussion",
            json.dumps({}),
            2,
            3,
            0.0,
            "",  # empty timestamp
        ),
    )

    # Row in April
    cursor.execute(
        "INSERT INTO session_chunks (id, session_id, text, embedding, metadata, start_msg, end_msg, updated_at, timestamp) VALUES (?, ?, ?, zeroblob(16), ?, ?, ?, ?, ?)",
        (
            "ts_chunk_april",
            "session_empty",
            "April lights conversation",
            json.dumps({"timestamp": "2024-04-10T10:00:00+00:00"}),
            4,
            5,
            0.0,
            "2024-04-10T10:00:00+00:00",
        ),
    )

    # FTS entries — all contain "lights" for cross-row FTS testing
    if store._fts_available:
        for cid, text in [
            ("ts_chunk1", "Discussed bedroom lights configuration"),
            ("ts_chunk_empty", "Undated legacy lights discussion"),
            ("ts_chunk_april", "April lights conversation"),
        ]:
            cursor.execute(
                "INSERT INTO session_chunks_fts (text, chunk_id, session_id) VALUES (?, ?, ?)",
                (text, cid, "session_empty"),
            )

    store._conn.commit()
    return store


class TestEmptyTimestampExclusion:
    """Verify that rows with timestamp = '' are excluded when date filters are active."""

    @pytest.mark.asyncio
    async def test_empty_timestamp_excluded_from_vector_search(
        self, store_with_empty_timestamps
    ):
        """Empty-timestamp rows must NOT leak through date-filtered vector search."""
        results = await store_with_empty_timestamps.search_session_chunks(
            query_embedding=[0.0] * 4,
            start_date="2024-03-01",
            end_date="2024-03-31",
        )
        ids = [r.id for r in results]
        assert "ts_chunk1" in ids, "Timestamped March row should be found"
        assert "ts_chunk_empty" not in ids, "Empty-timestamp row must be excluded"
        assert "ts_chunk_april" not in ids, "April row must be excluded"

    @pytest.mark.asyncio
    async def test_empty_timestamp_excluded_from_fts_search(
        self, store_with_empty_timestamps
    ):
        """Empty-timestamp rows must NOT leak through date-filtered FTS search."""
        if not store_with_empty_timestamps._fts_available:
            pytest.skip("FTS5 not available")

        results = await store_with_empty_timestamps.keyword_search_sessions(
            fts_query="lights",
            start_date="2024-03-01",
            end_date="2024-03-31",
        )
        ids = [r.id for r in results]
        assert "ts_chunk1" in ids, "Timestamped March row should be found"
        assert "ts_chunk_empty" not in ids, "Empty-timestamp row must be excluded"
        assert "ts_chunk_april" not in ids, "April row must be excluded"

    @pytest.mark.asyncio
    async def test_end_date_only_excludes_empty_timestamp(
        self, store_with_empty_timestamps
    ):
        """end_date without start_date must still exclude empty-timestamp rows."""
        results = await store_with_empty_timestamps.search_session_chunks(
            query_embedding=[0.0] * 4,
            end_date="2024-03-31",
        )
        ids = [r.id for r in results]
        assert "ts_chunk1" in ids, "March row should be found"
        assert "ts_chunk_empty" not in ids, "Empty-timestamp row must be excluded"

    @pytest.mark.asyncio
    async def test_no_date_filter_includes_empty_timestamp(
        self, store_with_empty_timestamps
    ):
        """Without date filters, empty-timestamp rows should still be returned."""
        results = await store_with_empty_timestamps.search_session_chunks(
            query_embedding=[0.0] * 4,
        )
        ids = [r.id for r in results]
        assert "ts_chunk_empty" in ids, (
            "Without date filter, all rows should be returned"
        )


class TestTemporalHintDetection:
    """Tests for _has_temporal_hint regex — verifies false positives are avoided."""

    @pytest.mark.parametrize(
        "query",
        [
            "yesterday I turned on the light",
            "what happened last week?",
            "wczoraj wyłączyłem światło",
            "co się stało ostatnio?",
            "dwa dni temu",
            "po godzinie wyłącz",
            "od kiedy to działa?",
            "2024-03-15",
        ],
    )
    def test_true_temporal_queries(self, query):
        """Queries with real temporal cues should match."""
        assert _has_temporal_hint(query), f"Expected temporal hint in: {query!r}"

    @pytest.mark.parametrize(
        "query",
        [
            "po prostu włącz światło",
            "po co to jest?",
            "daj mi to po polsku",
            "włącz światło w salonie",
            "jaka jest temperatura?",
        ],
    )
    def test_false_positive_polish_po(self, query):
        """Polish 'po' in non-temporal context must NOT trigger temporal expansion."""
        assert not _has_temporal_hint(query), (
            f"False positive temporal hint in: {query!r}"
        )


class TestSessionContextTemporalIntegration:
    """Integration: temporal hint -> expansion -> date-filtered search -> output."""

    @pytest.mark.asyncio
    async def test_temporal_flow_passes_dates_to_search(self):
        """Full flow: temporal query -> LLM expansion -> filtered vector+keyword search."""
        from custom_components.homeclaw.rag._session_context import get_session_context

        march_chunk = SearchResult(
            id="chunk_march",
            text="Discussed bedroom lights last month",
            distance=0.2,
            metadata={"timestamp": "2024-03-15T10:00:00+00:00"},
        )

        mock_store = MagicMock()
        mock_store.search_session_chunks = AsyncMock(return_value=[march_chunk])
        mock_store.keyword_search_sessions = AsyncMock(return_value=[])

        mock_embedding = MagicMock()
        mock_embedding.get_embeddings = AsyncMock(return_value=[[0.1] * 768])

        mock_provider = MagicMock()
        mock_provider.get_response = AsyncMock(
            return_value='{"start": "2024-03-01", "end": "2024-03-31"}'
        )

        # Query with "last month" triggers has_temporal_hint pattern
        results = await get_session_context(
            "what happened with bedroom lights last month?",
            mock_embedding,
            mock_store,
            min_similarity=0.5,
            top_k=3,
            provider=mock_provider,
            model=None,
        )

        # Verify date range was passed through to vector search
        call_kwargs = mock_store.search_session_chunks.call_args[1]
        assert call_kwargs["start_date"] == "2024-03-01"
        assert call_kwargs["end_date"] == "2024-03-31"

        # Verify formatted output
        assert len(results) == 1
        assert results[0]["text"] == "Discussed bedroom lights last month"
        assert results[0]["timestamp"] == "2024-03-15T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_partial_date_range_passes_start_only(self):
        """Partial range (start only) is forwarded to search methods."""
        from custom_components.homeclaw.rag._session_context import get_session_context

        mock_store = MagicMock()
        mock_store.search_session_chunks = AsyncMock(return_value=[])
        mock_store.keyword_search_sessions = AsyncMock(return_value=[])

        mock_embedding = MagicMock()
        mock_embedding.get_embeddings = AsyncMock(return_value=[[0.1] * 768])

        mock_provider = MagicMock()
        mock_provider.get_response = AsyncMock(
            return_value='{"start": "2024-03-01", "end": "N/A"}'
        )

        await get_session_context(
            "what happened since March?",
            mock_embedding,
            mock_store,
            min_similarity=0.5,
            top_k=3,
            provider=mock_provider,
            model=None,
        )

        call_kwargs = mock_store.search_session_chunks.call_args[1]
        assert call_kwargs["start_date"] == "2024-03-01"
        assert call_kwargs["end_date"] is None
