"""Tests for the session indexer (Phase 5: Session Indexing)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.homeclaw.rag.session_indexer import (
    SessionChunk,
    SessionIndexer,
    chunk_conversation,
    _hash_text,
    CHUNK_MAX_CHARS,
    CHUNK_OVERLAP_CHARS,
    DELTA_MIN_MESSAGES,
    MIN_SESSION_MESSAGES,
)


# --- _hash_text tests ---


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

    def test_unicode(self):
        """Unicode text produces valid hash."""
        h = _hash_text("cześć, światło w sypialni")
        assert len(h) == 64


# --- chunk_conversation tests ---


class TestChunkConversation:
    """Tests for the sliding window chunking algorithm."""

    def test_empty_messages(self):
        """No messages produces no chunks."""
        assert chunk_conversation([]) == []

    def test_single_message(self):
        """Single message produces one chunk."""
        messages = [{"role": "user", "content": "Hello"}]
        chunks = chunk_conversation(messages)
        assert len(chunks) == 1
        assert chunks[0].text == "User: Hello"
        assert chunks[0].start_msg == 0
        assert chunks[0].end_msg == 0

    def test_user_and_assistant(self):
        """Two messages produce one chunk if below max_chars."""
        messages = [
            {"role": "user", "content": "What is the weather?"},
            {"role": "assistant", "content": "It is sunny today."},
        ]
        chunks = chunk_conversation(messages)
        assert len(chunks) == 1
        assert "User: What is the weather?" in chunks[0].text
        assert "Assistant: It is sunny today." in chunks[0].text

    def test_multiple_chunks_with_overlap(self):
        """Long conversation is split into overlapping chunks."""
        # Generate enough messages to exceed max_chars
        messages = []
        for i in range(40):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(
                {
                    "role": role,
                    "content": f"Message number {i} with some filler text to make it longer.",
                }
            )

        chunks = chunk_conversation(messages, max_chars=400, overlap_chars=80)

        assert len(chunks) > 1

        # All messages should be covered
        all_start_msgs = {c.start_msg for c in chunks}
        assert 0 in all_start_msgs

        # Chunks should overlap: end of one chunk overlaps with start of next
        for i in range(len(chunks) - 1):
            # The next chunk should start at or before the previous chunk's end
            assert chunks[i + 1].start_msg <= chunks[i].end_msg

    def test_chunk_hash_consistency(self):
        """Same messages produce same chunk hashes."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        chunks1 = chunk_conversation(messages)
        chunks2 = chunk_conversation(messages)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.hash == c2.hash

    def test_empty_content_skipped(self):
        """Messages with empty content are skipped."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "World"},
        ]
        chunks = chunk_conversation(messages)
        assert len(chunks) == 1
        assert "Hello" in chunks[0].text
        assert "World" in chunks[0].text
        # The empty message should be skipped entirely

    def test_whitespace_content_skipped(self):
        """Messages with only whitespace are skipped."""
        messages = [
            {"role": "user", "content": "   "},
            {"role": "assistant", "content": "response"},
        ]
        chunks = chunk_conversation(messages)
        assert len(chunks) == 1
        assert "Assistant: response" in chunks[0].text

    def test_system_role_labeling(self):
        """System messages get capitalized role label."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        chunks = chunk_conversation(messages)
        assert "System: You are helpful." in chunks[0].text

    def test_no_overlap_zero(self):
        """Zero overlap produces non-overlapping chunks."""
        messages = [
            {"role": "user", "content": "A" * 200},
            {"role": "assistant", "content": "B" * 200},
            {"role": "user", "content": "C" * 200},
            {"role": "assistant", "content": "D" * 200},
        ]
        chunks = chunk_conversation(messages, max_chars=250, overlap_chars=0)

        # With 0 overlap, chunks should not share messages
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                assert (
                    chunks[i + 1].start_msg > chunks[i].end_msg
                    or chunks[i + 1].start_msg == chunks[i].end_msg
                )

    def test_chunk_respects_max_chars(self):
        """Each chunk text should not greatly exceed max_chars."""
        messages = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": f"Message {i}: " + "x" * 100})

        chunks = chunk_conversation(messages, max_chars=500, overlap_chars=100)

        for chunk in chunks:
            # Allow some tolerance for the last line that pushed over
            assert len(chunk.text) < 800  # Should not be wildly over max_chars

    def test_session_chunk_dataclass(self):
        """SessionChunk dataclass works correctly."""
        chunk = SessionChunk(
            text="User: Hello\nAssistant: Hi",
            start_msg=0,
            end_msg=1,
            hash="abc123",
        )
        assert chunk.text == "User: Hello\nAssistant: Hi"
        assert chunk.start_msg == 0
        assert chunk.end_msg == 1
        assert chunk.hash == "abc123"


# --- SessionIndexer tests ---


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
        provider.get_embeddings = AsyncMock(
            return_value=[[0.1, 0.2, 0.3]]  # 3-dim for testing
        )
        return provider

    @pytest.fixture
    def indexer(self, mock_store, mock_provider):
        """Create a SessionIndexer with mocked dependencies."""
        return SessionIndexer(store=mock_store, embedding_provider=mock_provider)

    async def test_index_session_basic(self, indexer, mock_store, mock_provider):
        """Test basic session indexing."""
        messages = [
            {"role": "user", "content": "What lights do I have?"},
            {"role": "assistant", "content": "You have 5 lights."},
            {"role": "user", "content": "Turn on bedroom light"},
            {"role": "assistant", "content": "Done, bedroom light is on."},
        ]
        # Provide embeddings for each chunk
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        result = await indexer.index_session("sess1", messages)

        assert result > 0
        mock_store.delete_session_chunks.assert_called_once_with("sess1")
        mock_store.add_session_chunks.assert_called_once()

    async def test_index_session_too_few_messages(self, indexer, mock_store):
        """Session with < MIN_SESSION_MESSAGES is skipped."""
        messages = [{"role": "user", "content": "Hello"}]

        result = await indexer.index_session("sess1", messages)

        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_delta_threshold(
        self, indexer, mock_store, mock_provider
    ):
        """Session is skipped if not enough new messages since last index."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        # Simulate that we already indexed 2 messages
        indexer._delta_tracker["sess1"] = 2

        result = await indexer.index_session("sess1", messages)

        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_delta_exceeded(
        self, indexer, mock_store, mock_provider
    ):
        """Session IS indexed when delta threshold is exceeded."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "Great!"},
            {"role": "user", "content": "What lights?"},
            {"role": "assistant", "content": "Five lights."},
        ]
        # Simulate that we already indexed 2 messages, now 6 => 4 new (>= DELTA_MIN_MESSAGES)
        indexer._delta_tracker["sess1"] = 2
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        result = await indexer.index_session("sess1", messages)

        assert result > 0

    async def test_index_session_force(self, indexer, mock_store, mock_provider):
        """Force=True bypasses delta check."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        # Delta tracker says we already indexed these
        indexer._delta_tracker["sess1"] = 2
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        result = await indexer.index_session("sess1", messages, force=True)

        assert result > 0

    async def test_index_session_content_hash_unchanged(
        self, indexer, mock_store, mock_provider
    ):
        """Session is skipped if content hash hasn't changed."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Bye"},
            {"role": "assistant", "content": "Goodbye"},
        ]
        # Compute what the hash would be
        full_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'].strip()}"
            for m in messages
        )
        expected_hash = _hash_text(full_text)

        # Store already has this hash
        mock_store.get_session_hash.return_value = expected_hash

        result = await indexer.index_session("sess1", messages)

        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_embedding_failure(
        self, indexer, mock_store, mock_provider
    ):
        """Embedding failure returns 0 chunks."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "More"},
            {"role": "assistant", "content": "Content"},
        ]
        mock_provider.get_embeddings.side_effect = Exception("API Error")

        result = await indexer.index_session("sess1", messages)

        assert result == 0
        mock_store.delete_session_chunks.assert_not_called()

    async def test_index_session_filters_non_relevant_roles(
        self, indexer, mock_store, mock_provider
    ):
        """Only user/assistant messages are indexed, system messages are ignored."""
        messages = [
            {"role": "system", "content": "You are a helper"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Turn on light"},
            {"role": "assistant", "content": "Done"},
        ]
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        result = await indexer.index_session("sess1", messages)

        assert result > 0
        # Verify the embedded texts don't contain the system message
        call_args = mock_store.add_session_chunks.call_args
        texts = call_args.kwargs.get("texts") or call_args[1].get("texts")
        for text in texts:
            assert "You are a helper" not in text

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

    async def test_index_session_updates_delta_tracker(
        self, indexer, mock_store, mock_provider
    ):
        """Delta tracker is updated after successful indexing."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "More"},
            {"role": "assistant", "content": "Content"},
        ]
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        await indexer.index_session("sess1", messages)

        # Delta tracker should be updated to current message count
        assert indexer._delta_tracker["sess1"] == 4

    async def test_index_session_deterministic_ids(
        self, indexer, mock_store, mock_provider
    ):
        """Chunk IDs are deterministic for the same content."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "More content"},
            {"role": "assistant", "content": "More response"},
        ]
        mock_provider.get_embeddings.return_value = [[0.1, 0.2, 0.3]]

        await indexer.index_session("sess1", messages)

        call1_ids = mock_store.add_session_chunks.call_args.kwargs.get(
            "ids"
        ) or mock_store.add_session_chunks.call_args[1].get("ids")

        # Reset and index again
        mock_store.reset_mock()
        mock_store.get_session_hash.return_value = None
        indexer._delta_tracker.clear()

        await indexer.index_session("sess1", messages)

        call2_ids = mock_store.add_session_chunks.call_args.kwargs.get(
            "ids"
        ) or mock_store.add_session_chunks.call_args[1].get("ids")

        assert call1_ids == call2_ids
