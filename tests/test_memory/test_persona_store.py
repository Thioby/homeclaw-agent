"""Tests for PersonaStore — L3 user persona storage."""

from __future__ import annotations

import pytest

from custom_components.homeclaw.memory.persona_store import Persona, PersonaStore
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
def persona_store(sqlite_store):
    import asyncio

    ps = PersonaStore(store=sqlite_store)
    asyncio.get_event_loop().run_until_complete(ps.async_initialize())
    return ps


class TestPersonaStore:
    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, persona_store) -> None:
        assert await persona_store.get_persona("nobody") is None

    @pytest.mark.asyncio
    async def test_save_and_get(self, persona_store) -> None:
        await persona_store.save_persona(
            "user1", "## Preferences\n- Short answers", memory_count=15
        )
        persona = await persona_store.get_persona("user1")
        assert persona is not None
        assert persona.content == "## Preferences\n- Short answers"
        assert persona.memory_count_at_generation == 15

    @pytest.mark.asyncio
    async def test_save_upserts_and_preserves_created_at(self, persona_store) -> None:
        await persona_store.save_persona("user1", "v1", memory_count=10)
        first = await persona_store.get_persona("user1")
        await persona_store.save_persona("user1", "v2", memory_count=40)
        second = await persona_store.get_persona("user1")
        assert second.content == "v2"
        assert second.memory_count_at_generation == 40
        assert second.created_at == first.created_at
        assert second.updated_at >= first.updated_at

    @pytest.mark.asyncio
    async def test_delete(self, persona_store) -> None:
        await persona_store.save_persona("user1", "v1", memory_count=10)
        assert await persona_store.delete_persona("user1") is True
        assert await persona_store.get_persona("user1") is None
        assert await persona_store.delete_persona("user1") is False
