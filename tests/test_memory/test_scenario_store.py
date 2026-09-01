"""Tests for ScenarioStore — L2 scenario blocks over atomic memories."""

from __future__ import annotations

import pytest

from custom_components.homeclaw.memory.memory_store import MemoryStore
from custom_components.homeclaw.memory.scenario_store import Scenario, ScenarioStore
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


@pytest.fixture
def scenario_store(sqlite_store, memory_store):
    """Create a ScenarioStore (requires memories table to exist first)."""
    import asyncio

    ss = ScenarioStore(store=sqlite_store)
    asyncio.get_event_loop().run_until_complete(ss.async_initialize())
    return ss


def _basis_embedding(index: int, dims: int = 16) -> list[float]:
    """Orthogonal embeddings so store_memory dedup never triggers."""
    return [1.0 if i == index else 0.0 for i in range(dims)]


async def _store_n_memories(memory_store, n: int, user_id: str = "user1") -> list[str]:
    ids = []
    for i in range(n):
        mem_id = await memory_store.store_memory(
            text=f"Fact number {i} about the user",
            embedding=_basis_embedding(i),
            user_id=user_id,
        )
        assert mem_id is not None
        ids.append(mem_id)
    return ids


class TestScenarioStore:
    @pytest.mark.asyncio
    async def test_store_and_search_scenario(self, memory_store, scenario_store) -> None:
        mem_ids = await _store_n_memories(memory_store, 3)
        emb = _basis_embedding(0)
        scenario_id = await scenario_store.store_scenario(
            user_id="user1",
            title="Bedroom lighting",
            summary="User prefers warm white lights in the bedroom at night.",
            embedding=emb,
            memory_ids=mem_ids,
        )
        assert scenario_id is not None

        results = await scenario_store.search_scenarios(
            query_embedding=emb, user_id="user1", min_similarity=0.5
        )
        assert len(results) == 1
        assert results[0].title == "Bedroom lighting"
        assert results[0].memory_count == 3
        assert results[0].score > 0.9

    @pytest.mark.asyncio
    async def test_grouped_memories_leave_ungrouped_pool(
        self, memory_store, scenario_store
    ) -> None:
        mem_ids = await _store_n_memories(memory_store, 5)
        ungrouped_before = await scenario_store.list_ungrouped_memories("user1")
        assert len(ungrouped_before) == 5

        await scenario_store.store_scenario(
            user_id="user1",
            title="Group",
            summary="Summary.",
            embedding=_basis_embedding(0),
            memory_ids=mem_ids[:3],
        )
        ungrouped_after = await scenario_store.list_ungrouped_memories("user1")
        assert len(ungrouped_after) == 2
        assert {m.id for m in ungrouped_after} == set(mem_ids[3:])

    @pytest.mark.asyncio
    async def test_search_scoped_to_user(self, memory_store, scenario_store) -> None:
        mem_ids = await _store_n_memories(memory_store, 3, user_id="user1")
        emb = _basis_embedding(0)
        await scenario_store.store_scenario(
            user_id="user1", title="T", summary="S", embedding=emb, memory_ids=mem_ids
        )
        results = await scenario_store.search_scenarios(
            query_embedding=emb, user_id="other_user", min_similarity=0.1
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_user_scenarios_ungroups_memories(
        self, memory_store, scenario_store
    ) -> None:
        mem_ids = await _store_n_memories(memory_store, 3)
        await scenario_store.store_scenario(
            user_id="user1",
            title="T",
            summary="S",
            embedding=_basis_embedding(0),
            memory_ids=mem_ids,
        )
        assert await scenario_store.count_scenarios("user1") == 1

        deleted = await scenario_store.delete_user_scenarios("user1")
        assert deleted == 1
        assert await scenario_store.count_scenarios("user1") == 0
        # Members return to the ungrouped pool
        ungrouped = await scenario_store.list_ungrouped_memories("user1")
        assert len(ungrouped) == 3

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, sqlite_store, scenario_store) -> None:
        ss2 = ScenarioStore(store=sqlite_store)
        await ss2.async_initialize()  # must not raise on existing tables/columns
        assert await ss2.count_scenarios("nobody") == 0
