"""Tests for the session indexer (Phase 5: Session Indexing)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.homeclaw.rag.session_indexer import (
    MAX_ROUND_CHARS,
    SessionIndexer,
    _hash_text,
    DELTA_MIN_ROUNDS,
)


class TestHashText:
    """Tests for the _hash_text helper."""

    def test_consistent(self):
        """Same text produces same hash."""
        assert _hash_text("hello world") == _hash_text("hello world")

    def test_unique(self):
        """Different texts produce different hashes."""
        assert _hash_text("hello") != _hash_text("world")

    def test_sha256_format(self):
        """Hash is 64-char hex string (SHA-256)."""
        h = _hash_text("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


@pytest.mark.asyncio
class TestSessionIndexer:
    """Tests for the SessionIndexer class."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock SqliteStore."""
        store = MagicMock()
        store.get_session_hash = AsyncMock(return_value=None)
        store.delete_session_chunks = AsyncMock()
        store.add_session_chunks = AsyncMock()
        store.get_session_chunk_stats = AsyncMock(
            return_value={
                "total_chunks": 0,
                "indexed_sessions": 0,
                "total_bytes": 0,
                "total_mb": 0,
            }
        )
        return store

    @pytest.fixture
    def mock_provider(self):
        """Create a mock EmbeddingProvider."""
        provider = MagicMock()
        provider.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        return provider

    @pytest.fixture
    def indexer(self, mock_store, mock_provider):
        """Create a SessionIndexer with mocked dependencies."""
        return SessionIndexer(store=mock_store, embedding_provider=mock_provider)

    async def test_index_session_basic(self, indexer, mock_store, mock_provider):
        """Test basic session indexing."""
        rounds = [
            {
                "user_message": "What lights do I have?",
                "assistant_message": "You have 5 lights.",
                "user_facts": "Has 5 lights",
                "timestamp": "2024-03-10",
            }
        ]
        # Skip delta check
        result = await indexer.index_session("sess1", rounds, force=True)

        assert result == 1
        mock_store.delete_session_chunks.assert_called_once_with("sess1")
        mock_store.add_session_chunks.assert_called_once()

        call_kwargs = mock_store.add_session_chunks.call_args.kwargs
        assert len(call_kwargs["ids"]) == 1
        assert "Has 5 lights" not in call_kwargs["texts"][0]
        assert "What lights do I have?" in call_kwargs["texts"][0]

    async def test_index_session_too_few_rounds(self, indexer, mock_store):
        """Session with 0 valid rounds is skipped."""
        result = await indexer.index_session("sess1", [])
        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_delta_threshold(
        self, indexer, mock_store, mock_provider
    ):
        """Session is skipped if not enough new rounds since last index."""
        rounds = [{"user_message": "a", "assistant_message": "b"}]
        indexer._delta_tracker["sess1"] = 1

        result = await indexer.index_session("sess1", rounds)
        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_delta_exceeded(
        self, indexer, mock_store, mock_provider
    ):
        """Session IS indexed when delta threshold is exceeded."""
        rounds = [
            {"user_message": "1", "assistant_message": "1"},
            {"user_message": "2", "assistant_message": "2"},
            {"user_message": "3", "assistant_message": "3"},
        ]
        indexer._delta_tracker["sess1"] = 1
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]] * 3

        result = await indexer.index_session("sess1", rounds)
        assert result == 3

    async def test_index_session_force(self, indexer, mock_store, mock_provider):
        """Force=True bypasses delta check."""
        rounds = [{"user_message": "a", "assistant_message": "b"}]
        indexer._delta_tracker["sess1"] = 1

        result = await indexer.index_session("sess1", rounds, force=True)
        assert result == 1

    async def test_index_session_content_hash_unchanged(
        self, indexer, mock_store, mock_provider
    ):
        """Session is skipped if content hash hasn't changed."""
        rounds = [{"user_message": "a", "assistant_message": "b", "user_facts": "c"}]

        full_text = "\n".join(
            f"User: {r['user_message']}\nAssistant: {r['assistant_message']}\nFacts: {r.get('user_facts', '')}"
            for r in rounds
        )
        expected_hash = _hash_text(full_text)

        mock_store.get_session_hash.return_value = expected_hash

        result = await indexer.index_session("sess1", rounds, force=False)
        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_embedding_failure(
        self, indexer, mock_store, mock_provider
    ):
        """Embedding failure returns 0 chunks."""
        rounds = [{"user_message": "a", "assistant_message": "b"}]
        mock_provider.get_embeddings.side_effect = Exception("API Error")

        result = await indexer.index_session("sess1", rounds, force=True)
        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_remove_session(self, indexer, mock_store):
        """Test removing session from index."""
        indexer._delta_tracker["sess1"] = 5
        await indexer.remove_session("sess1")
        mock_store.delete_session_chunks.assert_called_once_with("sess1")
        assert "sess1" not in indexer._delta_tracker

    async def test_get_stats(self, indexer, mock_store):
        """Test retrieving session index stats."""
        indexer._delta_tracker["sess1"] = 5
        indexer._delta_tracker["sess2"] = 3
        stats = await indexer.get_stats()
        assert stats["tracked_sessions"] == 2
        mock_store.get_session_chunk_stats.assert_called_once()

    async def test_oversized_round_truncated(self, indexer, mock_store, mock_provider):
        """Oversized round text is truncated to MAX_ROUND_CHARS before embedding."""
        huge_text = "x" * 5000
        rounds = [
            {
                "user_message": huge_text,
                "assistant_message": "ok",
                "user_facts": "",
                "timestamp": "2024-03-10",
            }
        ]
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        await indexer.index_session("sess_big", rounds, force=True)

        # Verify the key sent to embedding was truncated
        call_args = mock_provider.get_embeddings.call_args[0][0]
        assert len(call_args[0]) <= MAX_ROUND_CHARS

    async def test_oversized_round_with_facts_truncated(
        self, indexer, mock_store, mock_provider
    ):
        """Round with large message + facts is truncated to MAX_ROUND_CHARS."""
        rounds = [
            {
                "user_message": "a" * 1000,
                "assistant_message": "b" * 1000,
                "user_facts": "c" * 500,
                "timestamp": "2024-03-10",
            }
        ]
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        await indexer.index_session("sess_facts", rounds, force=True)

        call_args = mock_provider.get_embeddings.call_args[0][0]
        assert len(call_args[0]) <= MAX_ROUND_CHARS
