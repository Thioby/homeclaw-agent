"""Tests for MemoryManager.consolidate_scenarios — L2 consolidation via LLM."""

from __future__ import annotations

import json
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


def _basis_embedding(index: int, dims: int = 32) -> list[float]:
    return [1.0 if i == index else 0.0 for i in range(dims)]


async def _seed_memories(manager: MemoryManager, n: int, user_id: str = "user1") -> None:
    """Insert n memories directly via the store (bypasses embedding mock)."""
    for i in range(n):
        mem_id = await manager._memory_store.store_memory(
            text=f"Fact {i}: user does thing number {i} regularly",
            embedding=_basis_embedding(i),
            user_id=user_id,
        )
        assert mem_id is not None


def _mock_provider(response: str) -> MagicMock:
    provider = MagicMock()
    provider.lightweight_model = None
    provider.get_response = AsyncMock(return_value=response)
    return provider


class TestConsolidateScenarios:
    @pytest.mark.asyncio
    async def test_initializes_scenario_store(self, memory_manager) -> None:
        assert memory_manager._scenario_store is not None

    @pytest.mark.asyncio
    async def test_below_threshold_skips_llm(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 3)
        provider = _mock_provider("[]")
        created = await memory_manager.consolidate_scenarios("user1", provider)
        assert created == 0
        provider.get_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_scenarios_from_llm_output(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 12)
        response = json.dumps([
            {
                "title": "Daily routines",
                "summary": "The user has several regular daily habits.",
                "memory_indices": [0, 1, 2, 3],
            }
        ])
        provider = _mock_provider(response)
        created = await memory_manager.consolidate_scenarios("user1", provider)
        assert created == 1
        # 4 memories grouped -> 8 remain ungrouped
        ungrouped = await memory_manager._scenario_store.list_ungrouped_memories("user1")
        assert len(ungrouped) == 8

    @pytest.mark.asyncio
    async def test_rejects_too_small_clusters(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 12)
        response = json.dumps([
            {"title": "Tiny", "summary": "S.", "memory_indices": [0, 1]}
        ])
        provider = _mock_provider(response)
        created = await memory_manager.consolidate_scenarios("user1", provider)
        assert created == 0

    @pytest.mark.asyncio
    async def test_invalid_json_is_nonfatal(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 12)
        provider = _mock_provider("not json at all")
        created = await memory_manager.consolidate_scenarios("user1", provider)
        assert created == 0

    @pytest.mark.asyncio
    async def test_out_of_range_indices_ignored(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 12)
        response = json.dumps([
            {"title": "Bad", "summary": "S.", "memory_indices": [0, 1, 99, -5]}
        ])
        provider = _mock_provider(response)
        created = await memory_manager.consolidate_scenarios("user1", provider)
        assert created == 0  # only 2 valid indices -> below min cluster size


class TestScenarioRecall:
    @pytest.mark.asyncio
    async def test_recall_includes_matching_scenarios(self, memory_manager) -> None:
        # Store one scenario whose embedding matches the mocked query embedding
        query_embedding = [0.5] * 8  # matches mock_embedding_provider output
        scenario_id = await memory_manager._scenario_store.store_scenario(
            user_id="user1",
            title="Evening routine",
            summary="User dims lights and lowers blinds around 22:00.",
            embedding=query_embedding,
            memory_ids=["dummy-member-id"],
        )
        assert scenario_id is not None

        results = await memory_manager.recall_for_query("evening", "user1")
        scenario_entries = [r for r in results if r.get("category") == "scenario"]
        assert len(scenario_entries) == 1
        assert scenario_entries[0]["topic"] == "Evening routine"
        assert "dims lights" in scenario_entries[0]["information"]

    @pytest.mark.asyncio
    async def test_recall_without_scenarios_unchanged(self, memory_manager) -> None:
        results = await memory_manager.recall_for_query("anything", "user1")
        assert results == []
