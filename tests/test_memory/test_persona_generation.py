"""Tests for MemoryManager persona generation (L3)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeclaw.memory.manager import MemoryManager
from custom_components.homeclaw.rag.sqlite_store import SqliteStore


@pytest.fixture
def sqlite_store(tmp_path):
    import asyncio

    store = SqliteStore(persist_directory=str(tmp_path))
    asyncio.get_event_loop().run_until_complete(store.async_initialize())
    yield store
    if store._conn:
        store._conn.close()


@pytest.fixture
def mock_embedding_provider():
    provider = MagicMock()
    provider.get_embeddings = AsyncMock(return_value=[[0.5] * 8])
    provider.provider_name = "test"
    provider.dimension = 8
    return provider


@pytest.fixture
def memory_manager(sqlite_store, mock_embedding_provider):
    import asyncio

    mm = MemoryManager(store=sqlite_store, embedding_provider=mock_embedding_provider)
    asyncio.get_event_loop().run_until_complete(mm.async_initialize())
    return mm


def _basis_embedding(index: int, dims: int = 64) -> list[float]:
    return [1.0 if i == index else 0.0 for i in range(dims)]


async def _seed_memories(manager: MemoryManager, n: int, user_id: str = "user1") -> None:
    for i in range(n):
        mem_id = await manager._memory_store.store_memory(
            text=f"Fact {i}: user likes option {i}",
            embedding=_basis_embedding(i),
            user_id=user_id,
        )
        assert mem_id is not None


def _mock_provider(response: str = "## Preferences\n- Likes options") -> MagicMock:
    provider = MagicMock()
    provider.lightweight_model = None
    provider.get_response = AsyncMock(return_value=response)
    return provider


class TestPersonaGeneration:
    @pytest.mark.asyncio
    async def test_initializes_persona_store(self, memory_manager) -> None:
        assert memory_manager._persona_store is not None

    @pytest.mark.asyncio
    async def test_too_few_memories_skips(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 5)
        provider = _mock_provider()
        assert await memory_manager.maybe_regenerate_persona("user1", provider) is False
        provider.get_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_generates_when_enough_memories(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 10)
        provider = _mock_provider("## Preferences\n- User likes many options")
        assert await memory_manager.maybe_regenerate_persona("user1", provider) is True
        content = await memory_manager.get_persona_content("user1")
        assert content == "## Preferences\n- User likes many options"

    @pytest.mark.asyncio
    async def test_no_regen_below_delta(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 10)
        provider = _mock_provider()
        assert await memory_manager.maybe_regenerate_persona("user1", provider) is True
        # Second call right away: 0 new memories since generation -> skip
        provider2 = _mock_provider()
        assert await memory_manager.maybe_regenerate_persona("user1", provider2) is False
        provider2.get_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_llm_response_skips_save(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 10)
        provider = _mock_provider("")
        assert await memory_manager.maybe_regenerate_persona("user1", provider) is False
        assert await memory_manager.get_persona_content("user1") is None

    @pytest.mark.asyncio
    async def test_get_persona_content_missing_user(self, memory_manager) -> None:
        assert await memory_manager.get_persona_content("nobody") is None
