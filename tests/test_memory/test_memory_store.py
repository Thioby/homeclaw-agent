"""Tests for MemoryStore — SQLite storage, search, dedup, CRUD."""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from custom_components.homeclaw.memory.memory_store import (
    CATEGORY_DECISION,
    CATEGORY_FACT,
    CATEGORY_PREFERENCE,
    DEDUP_SIMILARITY_THRESHOLD,
    Memory,
    MemoryStore,
)
from custom_components.homeclaw.rag.sqlite_store import SqliteStore


@pytest.fixture
def sqlite_store(tmp_path):
    """Create a real SqliteStore for integration tests."""
    import asyncio

    store = SqliteStore(persist_directory=str(tmp_path))
    asyncio.get_event_loop().run_until_complete(store.async_initialize())
    yield store
    if store._conn:
        store._conn.close()


@pytest.fixture
def memory_store(sqlite_store):
    """Create a MemoryStore backed by real SQLite."""
    import asyncio

    ms = MemoryStore(store=sqlite_store)
    asyncio.get_event_loop().run_until_complete(ms.async_initialize())
    return ms


def _make_embedding(value: float = 0.1, dims: int = 8) -> list[float]:
    """Create a simple test embedding."""
    return [value] * dims


class TestMemoryStoreInit:
    """Tests for memory store initialization."""

    @pytest.mark.asyncio
    async def test_creates_tables(self, sqlite_store) -> None:
        ms = MemoryStore(store=sqlite_store)
        await ms.async_initialize()

        cursor = sqlite_store._conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        )
        assert cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_creates_fts_table(self, sqlite_store) -> None:
        ms = MemoryStore(store=sqlite_store)
        await ms.async_initialize()

        assert ms._fts_available is True

    @pytest.mark.asyncio
    async def test_idempotent_init(self, sqlite_store) -> None:
        ms = MemoryStore(store=sqlite_store)
        await ms.async_initialize()
        await ms.async_initialize()  # Should not raise
        assert ms._tables_created is True


class TestStoreMemory:
    """Tests for storing memories."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        memory_id = await memory_store.store_memory(
            text="User prefers short answers",
            embedding=emb,
            user_id="user1",
            category=CATEGORY_PREFERENCE,
        )

        assert memory_id is not None

        # Should be searchable
        results = await memory_store.search_memories(
            query_embedding=emb, user_id="user1", min_similarity=0.5
        )
        assert len(results) == 1
        assert results[0].text == "User prefers short answers"
        assert results[0].category == CATEGORY_PREFERENCE

    @pytest.mark.asyncio
    async def test_deduplication_blocks_identical(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        id1 = await memory_store.store_memory(
            text="User likes cats",
            embedding=emb,
            user_id="user1",
        )
        id2 = await memory_store.store_memory(
            text="User likes cats (duplicate)",
            embedding=emb,  # Identical embedding = cosine sim 1.0
            user_id="user1",
        )

        assert id1 is not None
        assert id2 is None  # Blocked by dedup

    @pytest.mark.asyncio
    async def test_dedup_allows_different_users(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        id1 = await memory_store.store_memory(
            text="Same text", embedding=emb, user_id="user1"
        )
        id2 = await memory_store.store_memory(
            text="Same text", embedding=emb, user_id="user2"
        )

        # Different users should both succeed
        assert id1 is not None
        assert id2 is not None

    @pytest.mark.asyncio
    async def test_dedup_updates_importance(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        id1 = await memory_store.store_memory(
            text="A fact",
            embedding=emb,
            user_id="user1",
            importance=0.3,
        )
        # Try to store duplicate with higher importance
        id2 = await memory_store.store_memory(
            text="A fact duplicate",
            embedding=emb,
            user_id="user1",
            importance=0.9,
        )

        assert id1 is not None
        assert id2 is None  # Blocked

        # Check importance was updated
        results = await memory_store.search_memories(
            query_embedding=emb, user_id="user1", min_similarity=0.5
        )
        assert results[0].importance == 0.9

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, memory_store) -> None:
        emb = _make_embedding(0.3)
        memory_id = await memory_store.store_memory(
            text="A fact with metadata",
            embedding=emb,
            user_id="user1",
            source="agent",
            session_id="session-123",
            metadata={"origin": "tool_call"},
        )
        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_category_validation(self, memory_store) -> None:
        emb = _make_embedding(0.2)
        memory_id = await memory_store.store_memory(
            text="Invalid category text",
            embedding=emb,
            user_id="user1",
            category="invalid_category",
        )
        # Should default to 'other'
        assert memory_id is not None
        results = await memory_store.search_memories(
            query_embedding=emb, user_id="user1", min_similarity=0.5
        )
        assert results[0].category == "other"


class TestSearchMemories:
    """Tests for memory search."""

    @pytest.mark.asyncio
    async def test_search_returns_relevant(self, memory_store) -> None:
        await memory_store.store_memory(
            text="Light preference",
            embedding=_make_embedding(0.8),
            user_id="user1",
        )
        await memory_store.store_memory(
            text="Temperature preference",
            embedding=_make_embedding(0.2),
            user_id="user1",
        )

        # Search with embedding close to first memory
        results = await memory_store.search_memories(
            query_embedding=_make_embedding(0.8),
            user_id="user1",
            min_similarity=0.5,
        )
        assert len(results) >= 1
        assert results[0].text == "Light preference"

    @pytest.mark.asyncio
    async def test_search_respects_min_similarity(self, memory_store) -> None:
        await memory_store.store_memory(
            text="A memory",
            embedding=_make_embedding(0.9),
            user_id="user1",
        )

        # Very different embedding should not match with high threshold
        results = await memory_store.search_memories(
            query_embedding=_make_embedding(-0.9),
            user_id="user1",
            min_similarity=0.99,
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_user_isolation(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        await memory_store.store_memory(
            text="User1 memory", embedding=emb, user_id="user1"
        )
        await memory_store.store_memory(
            text="User2 memory", embedding=_make_embedding(0.6), user_id="user2"
        )

        results = await memory_store.search_memories(
            query_embedding=emb, user_id="user1"
        )
        assert all(r.user_id == "user1" for r in results)

    @pytest.mark.asyncio
    async def test_search_by_category(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        await memory_store.store_memory(
            text="A preference",
            embedding=emb,
            user_id="user1",
            category=CATEGORY_PREFERENCE,
        )
        await memory_store.store_memory(
            text="A fact",
            embedding=_make_embedding(0.6),
            user_id="user1",
            category=CATEGORY_FACT,
        )

        results = await memory_store.search_memories(
            query_embedding=emb,
            user_id="user1",
            category=CATEGORY_PREFERENCE,
        )
        assert all(r.category == CATEGORY_PREFERENCE for r in results)

    @pytest.mark.asyncio
    async def test_search_empty_returns_empty(self, memory_store) -> None:
        results = await memory_store.search_memories(
            query_embedding=_make_embedding(0.5),
            user_id="nonexistent_user",
        )
        assert results == []


class TestKeywordSearch:
    """Tests for FTS5 keyword search."""

    @pytest.mark.asyncio
    async def test_keyword_search_finds_match(self, memory_store) -> None:
        await memory_store.store_memory(
            text="User prefers warm white lights in bedroom",
            embedding=_make_embedding(0.5),
            user_id="user1",
            category=CATEGORY_PREFERENCE,
        )

        results = await memory_store.keyword_search_memories(
            fts_query='"warm" AND "lights"',
            user_id="user1",
        )
        assert len(results) == 1
        assert "warm" in results[0].text.lower()

    @pytest.mark.asyncio
    async def test_keyword_search_respects_user(self, memory_store) -> None:
        await memory_store.store_memory(
            text="User prefers warm lights",
            embedding=_make_embedding(0.5),
            user_id="user1",
        )

        results = await memory_store.keyword_search_memories(
            fts_query='"warm"',
            user_id="user2",  # Different user
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_keyword_search_empty_query(self, memory_store) -> None:
        results = await memory_store.keyword_search_memories(
            fts_query="", user_id="user1"
        )
        assert results == []


class TestDeleteMemory:
    """Tests for memory deletion."""

    @pytest.mark.asyncio
    async def test_delete_by_id(self, memory_store) -> None:
        emb = _make_embedding(0.5)
        memory_id = await memory_store.store_memory(
            text="To delete", embedding=emb, user_id="user1"
        )

        result = await memory_store.delete_memory(memory_id)
        assert result is True

        # Verify gone
        results = await memory_store.search_memories(
            query_embedding=emb, user_id="user1"
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, memory_store) -> None:
        result = await memory_store.delete_memory("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user_memories(self, memory_store) -> None:
        # Use varied embeddings to avoid deduplication
        for i in range(5):
            emb = [0.0] * 8
            emb[i % 8] = 1.0  # Unique orthogonal embeddings
            await memory_store.store_memory(
                text=f"Memory {i}",
                embedding=emb,
                user_id="user1",
            )

        count = await memory_store.delete_user_memories("user1")
        assert count == 5

        remaining = await memory_store.get_memory_count("user1")
        assert remaining == 0


class TestStats:
    """Tests for memory statistics."""

    @pytest.mark.asyncio
    async def test_stats_empty(self, memory_store) -> None:
        stats = await memory_store.get_stats()
        assert stats["total"] == 0
        assert stats["categories"] == {}

    @pytest.mark.asyncio
    async def test_stats_with_data(self, memory_store) -> None:
        # Use orthogonal embeddings so dedup doesn't block
        emb1 = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        emb2 = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        emb3 = [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        await memory_store.store_memory(
            text="Pref 1",
            embedding=emb1,
            user_id="user1",
            category=CATEGORY_PREFERENCE,
        )
        await memory_store.store_memory(
            text="Fact 1",
            embedding=emb2,
            user_id="user1",
            category=CATEGORY_FACT,
        )
        await memory_store.store_memory(
            text="Pref 2",
            embedding=emb3,
            user_id="user2",
            category=CATEGORY_PREFERENCE,
        )

        stats = await memory_store.get_stats()
        assert stats["total"] == 3
        assert stats["categories"][CATEGORY_PREFERENCE] == 2
        assert stats["categories"][CATEGORY_FACT] == 1
        assert stats["unique_users"] == 2

    @pytest.mark.asyncio
    async def test_stats_per_user(self, memory_store) -> None:
        await memory_store.store_memory(
            text="User1 mem", embedding=_make_embedding(0.1), user_id="user1"
        )
        await memory_store.store_memory(
            text="User2 mem", embedding=_make_embedding(0.2), user_id="user2"
        )

        stats = await memory_store.get_stats(user_id="user1")
        assert stats["total"] == 1
