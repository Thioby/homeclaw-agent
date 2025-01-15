"""Tests for RAG Optimizer module."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.rag.optimizer import (
    MAX_CHUNKS_PER_BATCH,
    MAX_TEXT_PER_BATCH,
    MIN_CHUNKS_TO_OPTIMIZE,
    TARGET_COMPRESSION_RATIO,
    AnalysisResult,
    OptimizationResult,
    RAGOptimizer,
)

# --- Fixtures ---


@pytest.fixture
def mock_store():
    """Return a mock SqliteStore with session chunk data."""
    store = MagicMock()
    store._conn = MagicMock()
    store._initialized = True
    store.get_session_chunk_stats = AsyncMock(
        return_value={
            "total_chunks": 25,
            "indexed_sessions": 5,
            "total_bytes": 50000,
            "total_mb": 0.05,
        }
    )
    store.delete_session_chunks = AsyncMock()
    store.add_session_chunks = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_provider():
    """Return a mock embedding provider."""
    provider = MagicMock()
    provider.dimension = 768
    provider.provider_name = "mock"
    provider.get_embeddings = AsyncMock(
        side_effect=lambda texts: [[0.1] * 768 for _ in texts]
    )
    return provider


@pytest.fixture
def mock_ai_provider():
    """Return a mock AI provider for condensation."""
    provider = MagicMock()
    provider.get_response = AsyncMock(
        return_value="Summary chunk 1: User asked about lights.\n---\nSummary chunk 2: Assistant turned on bedroom light."
    )
    return provider


@pytest.fixture
def mock_memory_manager():
    """Return a mock MemoryManager."""
    manager = MagicMock()
    manager.get_stats = AsyncMock(
        return_value={"total": 15, "categories": {"fact": 5, "preference": 10}}
    )
    manager.list_memories = AsyncMock(return_value=[])
    manager.forget_all_user_memories = AsyncMock(return_value=15)
    manager.store_memory = AsyncMock(return_value="new_id")
    return manager


@pytest.fixture
def optimizer(mock_store, mock_embedding_provider, mock_memory_manager):
    """Return a RAGOptimizer instance with mocked dependencies."""
    return RAGOptimizer(
        store=mock_store,
        embedding_provider=mock_embedding_provider,
        memory_manager=mock_memory_manager,
    )


def _make_session_chunks(session_id: str, count: int) -> list[dict]:
    """Helper to create mock session chunk rows."""
    return [
        {
            "id": f"chunk_{session_id}_{i}",
            "session_id": session_id,
            "text": f"User: Tell me about entity_{i}.\nAssistant: Entity_{i} is a light in the bedroom. It's currently on.",
            "metadata": json.dumps({"start_msg": i * 2, "end_msg": (i + 1) * 2}),
            "start_msg": i * 2,
            "end_msg": (i + 1) * 2,
        }
        for i in range(count)
    ]


def _setup_store_session_groups(mock_store, groups: dict[str, int]):
    """Configure mock store to return specific session groups.

    Args:
        mock_store: Mock SqliteStore.
        groups: Dict of session_id -> chunk_count.
    """
    # Mock cursor for _get_session_chunk_groups
    cursor = MagicMock()
    rows = [{"session_id": sid, "cnt": cnt} for sid, cnt in groups.items()]
    cursor.fetchall.return_value = rows
    mock_store._conn.cursor.return_value = cursor

    # Also set up for _get_full_session_chunks
    all_chunks = {}
    for sid, cnt in groups.items():
        chunks = _make_session_chunks(sid, cnt)
        all_chunks[sid] = chunks

    def side_effect_execute(sql, params=None):
        if "GROUP BY session_id" in sql:
            cursor.fetchall.return_value = rows
        elif "WHERE session_id = ?" in sql and params:
            sid = params[0]
            if sid in all_chunks:
                chunk_rows = []
                for c in all_chunks[sid]:
                    row = MagicMock()
                    row.__getitem__ = lambda self, key, c=c: c[key]
                    chunk_rows.append(row)
                cursor.fetchall.return_value = chunk_rows
            else:
                cursor.fetchall.return_value = []

    cursor.execute = MagicMock(side_effect=side_effect_execute)


# --- Test Classes ---


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        result = AnalysisResult(
            total_session_chunks=100,
            total_sessions=10,
            optimizable_sessions=7,
            estimated_chunks_after=45,
            total_memories=50,
            estimated_memories_after=40,
            total_size_mb=1.5,
            session_details=[{"session_id": "abc", "chunks": 15, "estimated_after": 6}],
        )
        d = result.to_dict()
        assert d["total_session_chunks"] == 100
        assert d["potential_chunk_savings"] == 55
        assert d["potential_memory_savings"] == 10
        assert d["total_size_mb"] == 1.5
        assert len(d["session_details"]) == 1

    def test_to_dict_truncates_session_details(self):
        """Test that session_details are limited to 20."""
        result = AnalysisResult(
            session_details=[
                {"session_id": f"s{i}", "chunks": i, "estimated_after": 1}
                for i in range(30)
            ],
        )
        d = result.to_dict()
        assert len(d["session_details"]) == 20


class TestOptimizationResult:
    """Tests for OptimizationResult dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        result = OptimizationResult(
            sessions_processed=5,
            chunks_before=50,
            chunks_after=20,
            memories_before=30,
            memories_after=25,
            errors=["Error 1"],
            duration_seconds=12.345,
        )
        d = result.to_dict()
        assert d["chunks_saved"] == 30
        assert d["memories_saved"] == 5
        assert d["duration_seconds"] == 12.3
        assert d["errors"] == ["Error 1"]

    def test_default_values(self):
        """Test default empty result."""
        result = OptimizationResult()
        d = result.to_dict()
        assert d["sessions_processed"] == 0
        assert d["chunks_saved"] == 0
        assert d["errors"] == []


@pytest.mark.asyncio
class TestRAGOptimizerAnalyze:
    """Tests for RAGOptimizer.analyze()."""

    async def test_analyze_basic(self, optimizer, mock_store):
        """Test basic analysis with optimizable sessions."""
        _setup_store_session_groups(
            mock_store,
            {
                "session1": 10,  # Optimizable (>= MIN_CHUNKS)
                "session2": 5,  # Optimizable
                "session3": 2,  # Not optimizable
            },
        )

        result = await optimizer.analyze(user_id="user1")

        assert result.total_session_chunks == 25
        assert result.total_sessions == 5
        assert result.total_size_mb == 0.05
        assert result.optimizable_sessions == 2  # session1 + session2
        assert result.total_memories == 15

    async def test_analyze_no_optimizable(self, optimizer, mock_store):
        """Test analysis when no sessions need optimization."""
        _setup_store_session_groups(
            mock_store,
            {
                "session1": 2,
                "session2": 1,
            },
        )

        result = await optimizer.analyze(user_id="user1")
        assert result.optimizable_sessions == 0

    async def test_analyze_without_memory_manager(
        self, mock_store, mock_embedding_provider
    ):
        """Test analysis without memory manager."""
        optimizer = RAGOptimizer(
            store=mock_store,
            embedding_provider=mock_embedding_provider,
            memory_manager=None,
        )
        _setup_store_session_groups(mock_store, {"s1": 5})

        result = await optimizer.analyze(user_id="user1")
        assert result.total_memories == 0

    async def test_analyze_handles_exception(self, optimizer, mock_store):
        """Test analysis gracefully handles errors."""
        mock_store.get_session_chunk_stats = AsyncMock(
            side_effect=Exception("DB error")
        )

        result = await optimizer.analyze(user_id="user1")
        assert result.total_session_chunks == 0


@pytest.mark.asyncio
class TestRAGOptimizerSessions:
    """Tests for RAGOptimizer.optimize_sessions()."""

    async def test_optimize_sessions_no_optimizable(
        self, optimizer, mock_store, mock_ai_provider
    ):
        """Test optimization when no sessions are optimizable."""
        _setup_store_session_groups(
            mock_store,
            {
                "s1": 1,
                "s2": 2,
            },
        )

        result = await optimizer.optimize_sessions(mock_ai_provider)
        assert result.sessions_processed == 0
        assert result.chunks_before == 0

    async def test_optimize_sessions_progress_callback(
        self, optimizer, mock_store, mock_ai_provider
    ):
        """Test that progress callback is called."""
        _setup_store_session_groups(mock_store, {"s1": 5})

        progress_events = []

        async def callback(event):
            progress_events.append(event)

        await optimizer.optimize_sessions(mock_ai_provider, progress_callback=callback)

        # Should have received at least status and progress events
        assert len(progress_events) > 0
        types = [e["type"] for e in progress_events]
        assert "status" in types

    async def test_optimize_sessions_handles_provider_error(
        self, optimizer, mock_store, mock_ai_provider
    ):
        """Test graceful handling when AI provider fails."""
        _setup_store_session_groups(mock_store, {"s1": 5})
        mock_ai_provider.get_response = AsyncMock(side_effect=Exception("API error"))

        result = await optimizer.optimize_sessions(mock_ai_provider)
        assert len(result.errors) > 0
        assert "API error" in result.errors[0]

    async def test_optimize_sessions_with_model(
        self, optimizer, mock_store, mock_ai_provider
    ):
        """Test that model parameter is passed to provider."""
        _setup_store_session_groups(mock_store, {"s1": 5})

        await optimizer.optimize_sessions(mock_ai_provider, model="gpt-4o")

        # Verify get_response was called with model kwarg
        call_kwargs = mock_ai_provider.get_response.call_args
        if call_kwargs:
            assert call_kwargs[1].get("model") == "gpt-4o" or "model" in str(
                call_kwargs
            )


@pytest.mark.asyncio
class TestRAGOptimizerMemories:
    """Tests for RAGOptimizer.optimize_memories()."""

    async def test_optimize_memories_no_manager(
        self, mock_store, mock_embedding_provider, mock_ai_provider
    ):
        """Test memory optimization without memory manager."""
        optimizer = RAGOptimizer(
            store=mock_store,
            embedding_provider=mock_embedding_provider,
            memory_manager=None,
        )
        result = await optimizer.optimize_memories(mock_ai_provider, user_id="user1")
        assert result.memories_before == 0

    async def test_optimize_memories_too_few(
        self, optimizer, mock_ai_provider, mock_memory_manager
    ):
        """Test that small memory sets are skipped."""
        mock_memory_manager.list_memories = AsyncMock(
            return_value=[
                MagicMock(text="fact1", category="fact", importance=0.8, source="auto"),
                MagicMock(text="fact2", category="fact", importance=0.7, source="auto"),
            ]
        )

        result = await optimizer.optimize_memories(mock_ai_provider, user_id="user1")
        assert result.memories_before == 2
        assert result.memories_after == 2

    async def test_optimize_memories_condensation(
        self, optimizer, mock_ai_provider, mock_memory_manager
    ):
        """Test that memories are condensed by category."""
        memories = [
            MagicMock(
                text=f"Preference {i}",
                category="preference",
                importance=0.8,
                source="auto",
            )
            for i in range(6)
        ] + [
            MagicMock(text=f"Fact {i}", category="fact", importance=0.9, source="auto")
            for i in range(4)
        ]
        mock_memory_manager.list_memories = AsyncMock(return_value=memories)

        # AI response for preference condensation
        mock_ai_provider.get_response = AsyncMock(
            return_value="[preference] Combined preference about lighting\n[preference] Combined preference about temperature"
        )

        result = await optimizer.optimize_memories(mock_ai_provider, user_id="user1")
        assert result.memories_before == 10

    async def test_optimize_memories_no_user_id(self, optimizer, mock_ai_provider):
        """Test memory optimization without user_id."""
        result = await optimizer.optimize_memories(mock_ai_provider, user_id=None)
        assert result.memories_before == 0


@pytest.mark.asyncio
class TestRAGOptimizerAll:
    """Tests for RAGOptimizer.optimize_all()."""

    async def test_optimize_all_combines_results(
        self, optimizer, mock_store, mock_ai_provider, mock_memory_manager
    ):
        """Test that optimize_all combines session and memory results."""
        _setup_store_session_groups(mock_store, {"s1": 1})
        mock_memory_manager.list_memories = AsyncMock(return_value=[])

        progress_events = []

        async def callback(event):
            progress_events.append(event)

        result = await optimizer.optimize_all(
            mock_ai_provider, user_id="user1", progress_callback=callback
        )

        # Should have phase events
        types = [e["type"] for e in progress_events]
        assert "phase" in types
        assert "complete" in types
        assert result.duration_seconds >= 0


class TestChunkBatching:
    """Tests for _build_chunk_batches()."""

    def test_single_batch(self, optimizer):
        """Test that small chunk sets fit in one batch."""
        chunks = [{"text": "short chunk"} for _ in range(5)]
        batches = optimizer._build_chunk_batches(chunks)
        assert len(batches) == 1
        assert len(batches[0]) == 5

    def test_text_size_batching(self, optimizer):
        """Test batching based on text size limit."""
        # Create chunks that together exceed MAX_TEXT_PER_BATCH
        big_text = "x" * (MAX_TEXT_PER_BATCH // 2 + 100)
        chunks = [
            {"text": big_text},
            {"text": big_text},
            {"text": big_text},
        ]
        batches = optimizer._build_chunk_batches(chunks)
        assert len(batches) >= 2

    def test_count_batching(self, optimizer):
        """Test batching based on MAX_CHUNKS_PER_BATCH."""
        chunks = [{"text": "small"} for _ in range(MAX_CHUNKS_PER_BATCH + 5)]
        batches = optimizer._build_chunk_batches(chunks)
        assert len(batches) == 2
        assert len(batches[0]) == MAX_CHUNKS_PER_BATCH
        assert len(batches[1]) == 5

    def test_empty_chunks(self, optimizer):
        """Test empty input."""
        batches = optimizer._build_chunk_batches([])
        assert batches == []


class TestParseCondensedChunks:
    """Tests for _parse_condensed_chunks()."""

    def test_standard_separator(self, optimizer):
        """Test parsing with standard --- separator."""
        response = (
            "Chunk 1: User asked about lights.\n---\nChunk 2: Assistant responded."
        )
        result = optimizer._parse_condensed_chunks(response)
        assert len(result) == 2
        assert "Chunk 1" in result[0]
        assert "Chunk 2" in result[1]

    def test_no_separator(self, optimizer):
        """Test parsing without separator returns single chunk."""
        response = "Just a single condensed paragraph about the conversation."
        result = optimizer._parse_condensed_chunks(response)
        assert len(result) == 1

    def test_skips_short_fragments(self, optimizer):
        """Test that very short fragments are skipped."""
        response = "A proper chunk with sufficient content.\n---\nToo short\n---\nAnother proper chunk with enough text."
        result = optimizer._parse_condensed_chunks(response)
        assert len(result) == 2  # "Too short" should be skipped

    def test_empty_response(self, optimizer):
        """Test empty response."""
        result = optimizer._parse_condensed_chunks("")
        assert result == []

    def test_whitespace_handling(self, optimizer):
        """Test that chunks are properly trimmed."""
        response = "  Chunk 1 with enough spaces and content here  \n---\n  Chunk 2 with enough spaces and content here  "
        result = optimizer._parse_condensed_chunks(response)
        assert result[0] == "Chunk 1 with enough spaces and content here"
        assert result[1] == "Chunk 2 with enough spaces and content here"


@pytest.mark.asyncio
class TestCondenseMemories:
    """Tests for _condense_memories()."""

    async def test_parses_category_brackets(self, optimizer, mock_ai_provider):
        """Test that [category] prefixes are parsed correctly."""
        mock_ai_provider.get_response = AsyncMock(
            return_value="[fact] User's name is Adam\n[preference] Likes warm lights"
        )

        memories = [
            MagicMock(
                text="Name is Adam", category="fact", importance=0.9, source="auto"
            ),
            MagicMock(
                text="Warm lights", category="preference", importance=0.8, source="auto"
            ),
            MagicMock(
                text="Also warm", category="preference", importance=0.7, source="auto"
            ),
        ]

        result = await optimizer._condense_memories(memories, mock_ai_provider, None)
        assert len(result) == 2
        assert result[0]["category"] == "fact"
        assert result[1]["category"] == "preference"

    async def test_fallback_on_empty_response(self, optimizer, mock_ai_provider):
        """Test that original memories are returned on empty response."""
        mock_ai_provider.get_response = AsyncMock(return_value="")

        memories = [
            MagicMock(
                text="Memory 1 with enough text",
                category="fact",
                importance=0.8,
                source="auto",
            ),
            MagicMock(
                text="Memory 2 with enough text",
                category="fact",
                importance=0.7,
                source="auto",
            ),
            MagicMock(
                text="Memory 3 with enough text",
                category="fact",
                importance=0.6,
                source="auto",
            ),
        ]

        with pytest.raises(ValueError, match="Empty response"):
            await optimizer._condense_memories(memories, mock_ai_provider, None)

    async def test_model_passed_to_provider(self, optimizer, mock_ai_provider):
        """Test that model parameter is forwarded."""
        mock_ai_provider.get_response = AsyncMock(
            return_value="[fact] Condensed memory text here"
        )

        memories = [
            MagicMock(
                text="m1 enough text here",
                category="fact",
                importance=0.8,
                source="auto",
            ),
            MagicMock(
                text="m2 enough text here",
                category="fact",
                importance=0.7,
                source="auto",
            ),
            MagicMock(
                text="m3 enough text here",
                category="fact",
                importance=0.6,
                source="auto",
            ),
        ]

        await optimizer._condense_memories(memories, mock_ai_provider, "gpt-4o-mini")
        call_kwargs = mock_ai_provider.get_response.call_args[1]
        assert call_kwargs.get("model") == "gpt-4o-mini"


@pytest.mark.asyncio
class TestProgressCallback:
    """Tests for _send_progress()."""

    async def test_sends_progress(self):
        """Test that progress callback is called with correct data."""
        events = []

        async def callback(event):
            events.append(event)

        await RAGOptimizer._send_progress(callback, "status", "Testing", progress=50)
        assert len(events) == 1
        assert events[0]["type"] == "status"
        assert events[0]["message"] == "Testing"
        assert events[0]["progress"] == 50

    async def test_none_callback(self):
        """Test that None callback is handled gracefully."""
        # Should not raise
        await RAGOptimizer._send_progress(None, "status", "Testing")

    async def test_callback_exception_ignored(self):
        """Test that callback exceptions are silently ignored."""

        async def bad_callback(event):
            raise RuntimeError("Callback error")

        # Should not raise
        await RAGOptimizer._send_progress(bad_callback, "status", "Testing")


@pytest.mark.asyncio
class TestGetSessionChunkGroups:
    """Tests for _get_session_chunk_groups()."""

    async def test_returns_groups(self, optimizer, mock_store):
        """Test basic group retrieval."""
        _setup_store_session_groups(mock_store, {"s1": 10, "s2": 5})

        groups = await optimizer._get_session_chunk_groups()
        assert groups == {"s1": 10, "s2": 5}

    async def test_handles_no_connection(self, optimizer, mock_store):
        """Test handling when store connection is None."""
        mock_store._conn = None

        groups = await optimizer._get_session_chunk_groups()
        assert groups == {}

    async def test_handles_exception(self, optimizer, mock_store):
        """Test handling of database errors."""
        mock_store._conn.cursor.side_effect = Exception("DB error")

        groups = await optimizer._get_session_chunk_groups()
        assert groups == {}
