# Memory L1/L2/L3 Upgrade (RRF + Scenarios + Persona) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rozszerzenie systemu pamięci długoterminowej Homeclaw o trzy elementy zainspirowane TencentDB-Agent-Memory: fuzję RRF w hybrydowym recall, warstwę L2 (scenariusze grupujące powiązane wspomnienia) i warstwę L3 (automatycznie regenerowaną personę użytkownika wstrzykiwaną do system promptu).

**Architecture:** Obecne wspomnienia w tabeli `memories` stają się warstwą L1 (atomy). Nowa tabela `memory_scenarios` (L2) trzyma podsumowania grup wspomnień generowane przez lekki LLM podczas flushu; nowa tabela `user_personas` (L3) trzyma profil użytkownika w Markdown regenerowany co ~25 nowych wspomnień. Wszystko żyje w tej samej bazie SQLite (`vectors.db`, współdzielone `store._conn`), orkiestruje `MemoryManager`, a LLM jest dostępny wyłącznie przez `provider` przekazywany do `flush_from_messages` (tak jak dziś w `_ai_flush`).

**Tech Stack:** Python 3.12, Home Assistant custom component, sqlite3 (synchroniczne, wspólne połączenie `SqliteStore._conn`), FTS5, embeddingi przez `CachedEmbeddingProvider`, pytest + pytest-asyncio (`asyncio_mode = auto`).

## Global Constraints

- Zero nowych zależności runtime — dozwolone tylko: `aiohttp`, `voluptuous`, `pypdf`, stdlib.
- Wzorzec SQL: synchroniczny `sqlite3` przez `self.store._conn`, parametryzowane `?`, ręczny `conn.commit()`, `CREATE TABLE IF NOT EXISTS`, migracje kolumn przez try/except `SELECT` + `ALTER TABLE` (wzorzec z `memory_store.py:149-160`).
- Embeddingi: zawsze `await self.embedding_provider.get_embeddings([text])` i odczyt `embeddings[0]`; serializacja przez `self.store._embedding_to_blob(...)` / `self.store._read_embedding(...)`.
- Wywołania LLM: `await provider.get_response(messages, model=provider.lightweight_model jeśli ustawiony)` — wzorzec z `manager.py:_ai_flush`. Manager NIE trzyma providera jako pola.
- Każda nowa treść generowana przez LLM i trafiająca do promptu MUSI być sanityzowana przez `ANTI_PATTERNS` z `memory/auto_capture.py` (ochrona przed prompt injection).
- Wszystkie nowe operacje wywoływane z pipeline'u konwersacji są non-fatal: opakowane w try/except z `_LOGGER.debug`.
- Testy: `pytest tests/test_memory/ -v` (pełna suita: `pytest tests/ -v`, coverage musi zostać ≥ 70%). Fixtures wg wzorca z `tests/test_memory/test_manager.py` (real `SqliteStore(persist_directory=str(tmp_path))` + mock embedding provider `MagicMock` z `get_embeddings = AsyncMock(...)`).
- Kod i komentarze po angielsku; commit messages krótkie, lowercase, bez prefiksów typu "feat:" (wzorzec repo: "add deepseek provider"), **bez żadnych trailerów** (żadnych Co-Authored-By itp.).
- Znane, akceptowane uproszczenie: `memory_scenarios.memory_count` może się zdezaktualizować gdy wspomnienie-członek wygaśnie lub zostanie usunięte — pole jest informacyjne, nie funkcjonalne.

---

### Task 1: RRF w `_merge_memory_results`

Zamiana ważonego merge (vector 0.7 / keyword 0.3, wrażliwego na skalę score'ów) na Reciprocal Rank Fusion — rank-based, odporny na nieporównywalne skale cosine vs BM25.

**Files:**
- Modify: `custom_components/homeclaw/memory/manager.py:538-578` (funkcja `_merge_memory_results`)
- Test: `tests/test_memory/test_manager.py` (klasa z testami merge, okolice linii 270-313)

**Interfaces:**
- Consumes: `Memory` dataclass z `memory/memory_store.py` (pola: `id`, `importance`, `score`).
- Produces: `_merge_memory_results(vector_results: list[Memory], keyword_results: list[Memory], *, limit: int = 5, rrf_k: int = 60) -> list[Memory]` — sygnatura wywołania w `recall_for_query` (`_merge_memory_results(vector_results, keyword_results, limit=top_k)`) pozostaje bez zmian.

- [ ] **Step 1: Napisz failing testy RRF**

W `tests/test_memory/test_manager.py` znajdź istniejące testy `test_merge_results_dedup` (linie ~271-296) i `test_merge_results_limit` (~298-313). Usuń `test_merge_results_dedup` (zakłada skalę ważonych score'ów: `assert merged[0].score > 0.5` — z RRF score to ~1/61+1/61≈0.033). Zostaw `test_merge_results_limit` (przechodzi niezależnie od algorytmu). W ich miejsce (ta sama klasa testowa) dodaj:

```python
    def _mem(self, mem_id: str, score: float = 0.5, importance: float = 0.5) -> Memory:
        return Memory(
            id=mem_id,
            user_id="u",
            text=f"text {mem_id}",
            category="fact",
            importance=importance,
            created_at=0,
            updated_at=0,
            score=score,
        )

    def test_merge_rrf_overlap_ranks_first(self) -> None:
        """A memory present in both result lists outranks single-list ones."""
        vector = [self._mem("a", 0.9), self._mem("b", 0.8)]
        keyword = [self._mem("b", 0.7), self._mem("c", 0.6)]
        merged = _merge_memory_results(vector, keyword, limit=3)
        assert merged[0].id == "b"

    def test_merge_rrf_scale_invariance(self) -> None:
        """Tiny cosine scores are not drowned out by large keyword scores."""
        vector = [self._mem("a", 0.02)]
        keyword = [self._mem("c", 0.99)]
        merged = _merge_memory_results(vector, keyword, limit=3)
        # Both are rank 1 in their list -> identical RRF contribution
        assert merged[0].score == pytest.approx(merged[1].score)

    def test_merge_rrf_score_value(self) -> None:
        """Rank 1 in a single list yields exactly 1/(k+1) with k=60."""
        merged = _merge_memory_results([self._mem("a")], [], limit=1)
        assert merged[0].score == pytest.approx(1.0 / 61.0)

    def test_merge_rrf_importance_tiebreak(self) -> None:
        """Equal RRF scores are broken by importance."""
        vector = [self._mem("a", importance=0.2)]
        keyword = [self._mem("b", importance=0.9)]
        merged = _merge_memory_results(vector, keyword, limit=2)
        assert merged[0].id == "b"
```

Upewnij się, że plik importuje `pytest` (jest) oraz `Memory` i `_merge_memory_results` (są, linie ~13-19).

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_manager.py -v -k "merge"`
Expected: FAIL — `test_merge_rrf_score_value` (stary algorytm daje `0.5*0.7=0.35`, nie `1/61`), `test_merge_rrf_scale_invariance` (stary daje `0.02*0.7` vs `0.99*0.3`).

- [ ] **Step 3: Zamień implementację na RRF**

W `custom_components/homeclaw/memory/manager.py` zastąp całą funkcję `_merge_memory_results` (linie 538-578):

```python
# RRF constant — dampens the impact of top ranks (standard value from the literature)
RRF_K = 60


def _merge_memory_results(
    vector_results: list[Memory],
    keyword_results: list[Memory],
    *,
    limit: int = 5,
    rrf_k: int = RRF_K,
) -> list[Memory]:
    """Merge vector and keyword results using Reciprocal Rank Fusion.

    RRF is rank-based, so it is robust to incomparable score scales
    (cosine similarity vs normalized BM25). A memory appearing in both
    lists accumulates contributions from both ranks.
    """
    seen: dict[str, Memory] = {}
    scores: dict[str, float] = {}

    for result_list in (vector_results, keyword_results):
        for rank, mem in enumerate(result_list):
            if mem.id not in seen:
                seen[mem.id] = mem
            scores[mem.id] = scores.get(mem.id, 0.0) + 1.0 / (rrf_k + rank + 1)

    ranked = sorted(
        seen.values(),
        key=lambda m: (scores.get(m.id, 0), m.importance),
        reverse=True,
    )

    for mem in ranked:
        mem.score = scores.get(mem.id, 0)

    return ranked[:limit]
```

Umieść stałą `RRF_K` obok pozostałych stałych modułu (przy `RECALL_TOP_K`, linie 23-27). Usuń parametry `vector_weight`/`keyword_weight` — nic poza tą funkcją ich nie używa (zweryfikuj: `grep -rn "vector_weight\|keyword_weight" custom_components/ tests/`).

- [ ] **Step 4: Uruchom testy pamięci**

Run: `pytest tests/test_memory/ -v`
Expected: PASS (wszystkie, w tym nowe `test_merge_rrf_*`).

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/manager.py tests/test_memory/test_manager.py
git commit -m "replace weighted memory merge with reciprocal rank fusion"
```

---

### Task 2: `ScenarioStore` — warstwa L2 (storage)

Nowa tabela `memory_scenarios` + kolumna `scenario_id` na `memories` + CRUD i wyszukiwanie wektorowe scenariuszy.

**Files:**
- Create: `custom_components/homeclaw/memory/scenario_store.py`
- Test: `tests/test_memory/test_scenario_store.py`

**Interfaces:**
- Consumes: `SqliteStore` (pola/metody: `_conn`, `_embedding_to_blob`, `_read_embedding`), `cosine_similarity` z `rag/_store_utils.py`, `Memory` z `memory/memory_store.py`. Wymaga wcześniejszej inicjalizacji `MemoryStore` (tabela `memories` musi istnieć).
- Produces (używane w Taskach 3, 4, 9):
  - `Scenario` dataclass: `id: str, user_id: str, title: str, summary: str, memory_count: int, created_at: float, updated_at: float, score: float = 0.0`
  - `ScenarioStore(store=sqlite_store)` z metodami:
    - `async_initialize() -> None`
    - `store_scenario(*, user_id: str, title: str, summary: str, embedding: list[float], memory_ids: list[str]) -> str | None`
    - `search_scenarios(query_embedding: list[float], user_id: str, *, limit: int = 2, min_similarity: float = 0.4) -> list[Scenario]`
    - `list_ungrouped_memories(user_id: str, *, limit: int = 100) -> list[Memory]`
    - `count_scenarios(user_id: str) -> int`
    - `delete_user_scenarios(user_id: str) -> int`

- [ ] **Step 1: Napisz failing testy**

Utwórz `tests/test_memory/test_scenario_store.py`:

```python
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
```

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_scenario_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.homeclaw.memory.scenario_store'`.

- [ ] **Step 3: Zaimplementuj `scenario_store.py`**

Utwórz `custom_components/homeclaw/memory/scenario_store.py`:

```python
"""L2 scenario storage — groups related atomic memories into summarized blocks.

Scenarios are generated by an LLM (see MemoryManager.consolidate_scenarios)
and stored in the same SQLite database as memories. Each memory belongs to
at most one scenario via the memories.scenario_id column (added here by
migration). Scenario summaries carry their own embedding so they participate
in semantic recall alongside atomic memories.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..rag._store_utils import cosine_similarity as _cosine_similarity
from .memory_store import Memory

_LOGGER = logging.getLogger(__name__)

# Recall defaults for scenario search
SCENARIO_RECALL_TOP_K = 2
SCENARIO_RECALL_MIN_SIMILARITY = 0.4


@dataclass
class Scenario:
    """A summarized block of related memories (L2 layer)."""

    id: str
    user_id: str
    title: str
    summary: str
    memory_count: int
    created_at: float
    updated_at: float
    score: float = 0.0  # Search relevance score (filled during search)


@dataclass
class ScenarioStore:
    """SQLite storage for L2 scenarios. Shares the RAG database connection."""

    store: Any  # SqliteStore — avoid circular import
    _tables_created: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        """Create scenario table and migrate memories.scenario_id column.

        Must run AFTER MemoryStore.async_initialize (memories table required).
        """
        if self._tables_created:
            return

        conn = self.store._conn
        if conn is None:
            raise RuntimeError("SqliteStore connection not available")

        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_scenarios (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                embedding BLOB NOT NULL,
                memory_count INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenarios_user_id
            ON memory_scenarios(user_id)
        """)

        # Migration: add scenario_id column to memories if missing
        try:
            cursor.execute("SELECT scenario_id FROM memories LIMIT 1")
        except Exception:
            _LOGGER.info("Migrating memories table: adding scenario_id column")
            cursor.execute("ALTER TABLE memories ADD COLUMN scenario_id TEXT")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_scenario
            ON memories(user_id, scenario_id)
        """)

        conn.commit()
        self._tables_created = True
        _LOGGER.info("Scenario store tables initialized")

    async def store_scenario(
        self,
        *,
        user_id: str,
        title: str,
        summary: str,
        embedding: list[float],
        memory_ids: list[str],
    ) -> str | None:
        """Insert a scenario and link member memories to it."""
        conn = self.store._conn
        if conn is None or not memory_ids:
            return None

        scenario_id = str(uuid.uuid4())
        now = time.time()
        embedding_blob = self.store._embedding_to_blob(embedding)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory_scenarios
                (id, user_id, title, summary, embedding, memory_count,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scenario_id, user_id, title, summary, embedding_blob,
             len(memory_ids), now, now),
        )

        placeholders = ",".join("?" * len(memory_ids))
        cursor.execute(
            f"UPDATE memories SET scenario_id = ?, updated_at = ? "
            f"WHERE id IN ({placeholders}) AND user_id = ?",
            (scenario_id, now, *memory_ids, user_id),
        )

        conn.commit()
        return scenario_id

    async def search_scenarios(
        self,
        query_embedding: list[float],
        user_id: str,
        *,
        limit: int = SCENARIO_RECALL_TOP_K,
        min_similarity: float = SCENARIO_RECALL_MIN_SIMILARITY,
    ) -> list[Scenario]:
        """Vector search over scenario summaries (full scan + Python cosine)."""
        conn = self.store._conn
        if conn is None:
            return []

        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM memory_scenarios WHERE user_id = ?", (user_id,)
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            stored_embedding = self.store._read_embedding(row["embedding"])
            similarity = _cosine_similarity(query_embedding, stored_embedding)
            if similarity >= min_similarity:
                results.append(
                    Scenario(
                        id=row["id"],
                        user_id=row["user_id"],
                        title=row["title"],
                        summary=row["summary"],
                        memory_count=row["memory_count"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        score=similarity,
                    )
                )

        results.sort(key=lambda s: s.score, reverse=True)
        return results[:limit]

    async def list_ungrouped_memories(
        self, user_id: str, *, limit: int = 100
    ) -> list[Memory]:
        """Return non-expired memories not yet assigned to any scenario."""
        conn = self.store._conn
        if conn is None:
            return []

        now = time.time()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM memories WHERE user_id = ? AND scenario_id IS NULL "
            "AND (expires_at IS NULL OR expires_at > ?) "
            "ORDER BY created_at ASC LIMIT ?",
            (user_id, now, limit),
        )
        rows = cursor.fetchall()
        return [
            Memory(
                id=row["id"],
                user_id=row["user_id"],
                text=row["text"],
                category=row["category"],
                importance=row["importance"],
                source=row["source"],
                session_id=row["session_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                expires_at=row["expires_at"],
            )
            for row in rows
        ]

    async def count_scenarios(self, user_id: str) -> int:
        conn = self.store._conn
        if conn is None:
            return 0
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM memory_scenarios WHERE user_id = ?", (user_id,)
        )
        return cursor.fetchone()[0]

    async def delete_user_scenarios(self, user_id: str) -> int:
        """Delete all scenarios for a user; members return to ungrouped pool."""
        conn = self.store._conn
        if conn is None:
            return 0
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE memories SET scenario_id = NULL WHERE user_id = ?", (user_id,)
        )
        cursor.execute(
            "DELETE FROM memory_scenarios WHERE user_id = ?", (user_id,)
        )
        deleted = cursor.rowcount
        conn.commit()
        return deleted
```

- [ ] **Step 4: Uruchom testy**

Run: `pytest tests/test_memory/test_scenario_store.py -v`
Expected: PASS (5 testów).

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/scenario_store.py tests/test_memory/test_scenario_store.py
git commit -m "add scenario store for l2 memory layer"
```

---

### Task 3: Konsolidacja scenariuszy w `MemoryManager`

LLM grupuje niepogrupowane wspomnienia w scenariusze. `MemoryManager` zyskuje `_scenario_store` i metodę `consolidate_scenarios`.

**Files:**
- Modify: `custom_components/homeclaw/memory/manager.py` (pola dataclass ~linie 30-45, `async_initialize` ~47-58, nowa metoda po `flush_from_messages`)
- Test: `tests/test_memory/test_scenario_consolidation.py`

**Interfaces:**
- Consumes: `ScenarioStore` z Task 2 (`store_scenario`, `list_ungrouped_memories`), `ANTI_PATTERNS` z `memory/auto_capture.py`, `provider.get_response` / `provider.lightweight_model`.
- Produces: `MemoryManager.consolidate_scenarios(user_id: str, provider: Any) -> int` (zwraca liczbę utworzonych scenariuszy); pole `MemoryManager._scenario_store: ScenarioStore | None` (używane w Task 4 i 9).

- [ ] **Step 1: Napisz failing testy**

Utwórz `tests/test_memory/test_scenario_consolidation.py`:

```python
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
```

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_scenario_consolidation.py -v`
Expected: FAIL — `AttributeError: 'MemoryManager' object has no attribute '_scenario_store'` / `consolidate_scenarios`.

- [ ] **Step 3: Zaimplementuj konsolidację**

W `custom_components/homeclaw/memory/manager.py`:

(a) Dodaj import u góry pliku (obok importu `MemoryStore`):

```python
from .scenario_store import ScenarioStore
```

(b) Dodaj pole do dataclass `MemoryManager` (po `_memory_store`):

```python
    _scenario_store: ScenarioStore | None = field(default=None, repr=False)
```

(c) W `async_initialize` po inicjalizacji `_memory_store` (kolejność WYMAGANA — migracja scenario_id potrzebuje tabeli memories):

```python
        self._scenario_store = ScenarioStore(store=self.store)
        await self._scenario_store.async_initialize()
```

(d) Dodaj atrybuty klasy obok `_FLUSH_SYSTEM_PROMPT`:

```python
    _SCENARIO_SYSTEM_PROMPT = (
        "You are a memory organization assistant. You receive a numbered list "
        "of atomic memories about a user. Group RELATED memories into "
        "scenarios — coherent topics like 'bedroom lighting setup', "
        "'morning routine', 'vacation planning'.\n\n"
        "FORMAT: Return a JSON array of scenario objects. Each must have:\n"
        '- "title": Short scenario name (2-5 words)\n'
        '- "summary": 2-4 sentences summarizing what these memories say together\n'
        '- "memory_indices": Array of memory numbers belonging to this scenario\n\n'
        "RULES:\n"
        "- Only group memories genuinely about the same topic.\n"
        "- A scenario needs at least 3 memories. Leave loners ungrouped.\n"
        "- Each memory belongs to at most one scenario.\n"
        "- Write title and summary in the SAME LANGUAGE as the memories.\n"
        "- If no coherent groups exist, return an empty array: []"
    )

    _SCENARIO_MIN_UNGROUPED = 12
    _SCENARIO_MIN_CLUSTER = 3
    _SCENARIO_MAX_INPUT = 100
```

(e) Dodaj metodę (po `flush_from_messages`):

```python
    async def consolidate_scenarios(self, user_id: str, provider: Any) -> int:
        """Group ungrouped memories into L2 scenario blocks using an LLM.

        Returns the number of scenarios created. Skips silently when there
        are too few ungrouped memories to be worth an LLM call.
        """
        self._ensure_initialized()
        import json as _json

        ungrouped = await self._scenario_store.list_ungrouped_memories(
            user_id, limit=self._SCENARIO_MAX_INPUT
        )
        if len(ungrouped) < self._SCENARIO_MIN_UNGROUPED:
            return 0

        numbered = "\n".join(
            f"{i}. [{m.category}] {m.text}" for i, m in enumerate(ungrouped)
        )
        messages = [
            {"role": "system", "content": self._SCENARIO_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Group these memories into scenarios:\n\n{numbered}",
            },
        ]

        try:
            kwargs: dict[str, Any] = {}
            if provider.lightweight_model:
                kwargs["model"] = provider.lightweight_model

            response = await provider.get_response(messages, **kwargs)
            if not response:
                return 0

            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            scenarios = _json.loads(response)
            if not isinstance(scenarios, list):
                return 0
        except Exception as e:
            _LOGGER.debug("Scenario consolidation LLM call failed: %s", e)
            return 0

        from .auto_capture import ANTI_PATTERNS

        created = 0
        for sc in scenarios:
            try:
                title = str(sc.get("title", "")).strip()
                summary = str(sc.get("summary", "")).strip()
                indices = sc.get("memory_indices", [])
                if not title or not summary or not isinstance(indices, list):
                    continue

                member_ids = list(dict.fromkeys(
                    ungrouped[i].id
                    for i in indices
                    if isinstance(i, int) and 0 <= i < len(ungrouped)
                ))
                if len(member_ids) < self._SCENARIO_MIN_CLUSTER:
                    continue

                if any(p.search(title) or p.search(summary) for p in ANTI_PATTERNS):
                    _LOGGER.warning(
                        "Scenario consolidation produced unsafe content, skipping: %s",
                        title[:80],
                    )
                    continue

                embeddings = await self.embedding_provider.get_embeddings(
                    [f"{title}\n{summary}"]
                )
                if not embeddings or not embeddings[0]:
                    continue

                scenario_id = await self._scenario_store.store_scenario(
                    user_id=user_id,
                    title=title,
                    summary=summary,
                    embedding=embeddings[0],
                    memory_ids=member_ids,
                )
                if scenario_id:
                    created += 1
                    _LOGGER.info("Consolidated scenario: %s (%d memories)",
                                 title[:60], len(member_ids))
            except Exception as e:
                _LOGGER.debug("Failed to store scenario: %s", e)

        return created
```

- [ ] **Step 4: Uruchom testy**

Run: `pytest tests/test_memory/test_scenario_consolidation.py tests/test_memory/test_manager.py -v`
Expected: PASS (nowe + wszystkie dotychczasowe testy managera).

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/manager.py tests/test_memory/test_scenario_consolidation.py
git commit -m "add llm scenario consolidation to memory manager"
```

---

### Task 4: Scenariusze w recall (`recall_for_query`)

Podsumowania scenariuszy uczestniczą w recall obok atomów — trafiają do `long_term_memories` z kategorią `scenario`.

**Files:**
- Modify: `custom_components/homeclaw/memory/manager.py:123-184` (metoda `recall_for_query`)
- Test: `tests/test_memory/test_scenario_consolidation.py` (dopisz klasę)

**Interfaces:**
- Consumes: `ScenarioStore.search_scenarios` (Task 2), stałe `SCENARIO_RECALL_TOP_K`, `SCENARIO_RECALL_MIN_SIMILARITY` z `scenario_store.py`.
- Produces: `recall_for_query` zwraca dotychczasowe dicty `{"category", "information", ...}` plus dicty scenariuszy `{"category": "scenario", "topic": <title>, "information": <summary>}`. Konsument (`rag/context_retriever.py:112-121`) nie wymaga zmian — serializuje listę do JSON as-is.

- [ ] **Step 1: Napisz failing test**

Dopisz do `tests/test_memory/test_scenario_consolidation.py`:

```python
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
```

- [ ] **Step 2: Uruchom testy — pierwszy ma failować**

Run: `pytest tests/test_memory/test_scenario_consolidation.py -v -k "Recall"`
Expected: `test_recall_includes_matching_scenarios` FAIL (brak wpisów `scenario`), `test_recall_without_scenarios_unchanged` PASS.

- [ ] **Step 3: Zaimplementuj recall scenariuszy**

W `custom_components/homeclaw/memory/manager.py`, w `recall_for_query`, zastąp końcówkę metody (od `# Merge results` do `return _format_memories_for_prompt(merged)` włącznie):

```python
            # Merge results (hybrid RRF: rank-based fusion)
            merged = _merge_memory_results(vector_results, keyword_results, limit=top_k)

            # L2 scenario recall — summaries of related memory groups
            scenario_context: list[dict[str, Any]] = []
            if self._scenario_store:
                try:
                    scenarios = await self._scenario_store.search_scenarios(
                        query_embedding=query_embedding,
                        user_id=user_id,
                    )
                    scenario_context = [
                        {
                            "category": "scenario",
                            "topic": s.title,
                            "information": s.summary,
                        }
                        for s in scenarios
                    ]
                except Exception as e:
                    _LOGGER.debug("Scenario recall failed: %s", e)

            if not merged and not scenario_context:
                return []

            # Format for system prompt injection
            return _format_memories_for_prompt(merged) + scenario_context
```

(`search_scenarios` używa swoich domyślnych `limit=SCENARIO_RECALL_TOP_K=2`, `min_similarity=0.4` — nie przekazuj ich jawnie.)

- [ ] **Step 4: Uruchom testy pamięci**

Run: `pytest tests/test_memory/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/manager.py tests/test_memory/test_scenario_consolidation.py
git commit -m "include scenario summaries in memory recall"
```

---

### Task 5: `PersonaStore` — warstwa L3 (storage)

Tabela `user_personas`: jeden profil Markdown per user + licznik wspomnień w momencie generacji (do progu regeneracji).

**Files:**
- Create: `custom_components/homeclaw/memory/persona_store.py`
- Test: `tests/test_memory/test_persona_store.py`

**Interfaces:**
- Consumes: `SqliteStore._conn`.
- Produces (używane w Task 6, 8, 9):
  - `Persona` dataclass: `user_id: str, content: str, memory_count_at_generation: int, created_at: float, updated_at: float`
  - `PersonaStore(store=sqlite_store)` z metodami:
    - `async_initialize() -> None`
    - `get_persona(user_id: str) -> Persona | None`
    - `save_persona(user_id: str, content: str, *, memory_count: int) -> None` (upsert; `created_at` zachowywane przy update)
    - `delete_persona(user_id: str) -> bool`

- [ ] **Step 1: Napisz failing testy**

Utwórz `tests/test_memory/test_persona_store.py`:

```python
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
```

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_persona_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.homeclaw.memory.persona_store'`.

- [ ] **Step 3: Zaimplementuj `persona_store.py`**

Utwórz `custom_components/homeclaw/memory/persona_store.py`:

```python
"""L3 persona storage — one LLM-distilled user profile per user.

The persona is a Markdown summary of everything the memory system knows
about a user, regenerated periodically (see MemoryManager) and injected
into the system prompt on every conversation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class Persona:
    """A distilled user profile (L3 layer)."""

    user_id: str
    content: str
    memory_count_at_generation: int
    created_at: float
    updated_at: float


@dataclass
class PersonaStore:
    """SQLite storage for user personas. Shares the RAG database connection."""

    store: Any  # SqliteStore — avoid circular import
    _table_created: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        if self._table_created:
            return

        conn = self.store._conn
        if conn is None:
            raise RuntimeError("SqliteStore connection not available")

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_personas (
                user_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_count_at_generation INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.commit()
        self._table_created = True
        _LOGGER.info("Persona store table initialized")

    async def get_persona(self, user_id: str) -> Persona | None:
        conn = self.store._conn
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_personas WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Persona(
            user_id=row["user_id"],
            content=row["content"],
            memory_count_at_generation=row["memory_count_at_generation"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def save_persona(
        self, user_id: str, content: str, *, memory_count: int
    ) -> None:
        conn = self.store._conn
        if conn is None:
            return
        now = time.time()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_personas
                (user_id, content, memory_count_at_generation,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                content = excluded.content,
                memory_count_at_generation = excluded.memory_count_at_generation,
                updated_at = excluded.updated_at
            """,
            (user_id, content, memory_count, now, now),
        )
        conn.commit()

    async def delete_persona(self, user_id: str) -> bool:
        conn = self.store._conn
        if conn is None:
            return False
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_personas WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
```

- [ ] **Step 4: Uruchom testy**

Run: `pytest tests/test_memory/test_persona_store.py -v`
Expected: PASS (4 testy).

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/persona_store.py tests/test_memory/test_persona_store.py
git commit -m "add persona store for l3 memory layer"
```

---

### Task 6: Generacja persony w `MemoryManager`

`maybe_regenerate_persona` — regeneruje profil gdy przybyło ≥ 25 wspomnień od ostatniej generacji; `get_persona_content` — odczyt do wstrzyknięcia w prompt.

**Files:**
- Modify: `custom_components/homeclaw/memory/manager.py` (pola dataclass, `async_initialize`, nowe metody po `consolidate_scenarios`)
- Test: `tests/test_memory/test_persona_generation.py`

**Interfaces:**
- Consumes: `PersonaStore` (Task 5), `MemoryStore.get_memory_count(user_id)` (`memory_store.py:516`), `MemoryStore.list_memories(user_id, ...)` (`memory_store.py:610` — paginowane, sortowane `importance DESC, created_at DESC`; jeśli sygnatura ma keyword-only args, wywołuj zgodnie z nią), `ANTI_PATTERNS` z `auto_capture.py`.
- Produces (używane w Task 7, 8):
  - `MemoryManager.maybe_regenerate_persona(user_id: str, provider: Any) -> bool` (True = wygenerowano)
  - `MemoryManager.get_persona_content(user_id: str) -> str | None` (zwraca `None` gdy manager niezainicjalizowany lub brak persony — NIE rzuca)
  - pole `MemoryManager._persona_store: PersonaStore | None`

- [ ] **Step 1: Napisz failing testy**

Utwórz `tests/test_memory/test_persona_generation.py`:

```python
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
```

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_persona_generation.py -v`
Expected: FAIL — brak `_persona_store` / `maybe_regenerate_persona`.

- [ ] **Step 3: Zaimplementuj generację persony**

W `custom_components/homeclaw/memory/manager.py`:

(a) Import obok `ScenarioStore`:

```python
from .persona_store import PersonaStore
```

(b) Pole dataclass po `_scenario_store`:

```python
    _persona_store: PersonaStore | None = field(default=None, repr=False)
```

(c) W `async_initialize` po inicjalizacji `_scenario_store`:

```python
        self._persona_store = PersonaStore(store=self.store)
        await self._persona_store.async_initialize()
```

(d) Atrybuty klasy obok `_SCENARIO_SYSTEM_PROMPT`:

```python
    _PERSONA_SYSTEM_PROMPT = (
        "You are a user profiling assistant. You receive memories about a "
        "user collected by a smart-home assistant. Distill them into a "
        "concise persona profile the assistant reads before every "
        "conversation.\n\n"
        "FORMAT: Markdown, max 250 words, with these sections "
        "(omit empty ones):\n"
        "## Preferences\n## Facts\n## Routines\n## Communication style\n\n"
        "RULES:\n"
        "- Write in the SAME LANGUAGE as the memories.\n"
        "- State only what the memories support — no speculation.\n"
        "- Prefer stable traits over one-off events.\n"
        "- Plain statements only, no meta-commentary."
    )

    _PERSONA_MIN_MEMORIES = 10
    _PERSONA_REGEN_DELTA = 25
    _PERSONA_MAX_INPUT = 200
    _PERSONA_MAX_CHARS = 4000
```

(e) Metody po `consolidate_scenarios`:

```python
    async def maybe_regenerate_persona(self, user_id: str, provider: Any) -> bool:
        """Regenerate the L3 persona when enough new memories accumulated.

        Triggers when the user has at least _PERSONA_MIN_MEMORIES memories
        and either no persona exists yet or _PERSONA_REGEN_DELTA memories
        were added since the last generation. Returns True when a new
        persona was generated and saved.
        """
        self._ensure_initialized()

        count = await self._memory_store.get_memory_count(user_id)
        if count < self._PERSONA_MIN_MEMORIES:
            return False

        existing = await self._persona_store.get_persona(user_id)
        if (
            existing
            and count - existing.memory_count_at_generation
            < self._PERSONA_REGEN_DELTA
        ):
            return False

        memories = await self._memory_store.list_memories(
            user_id, limit=self._PERSONA_MAX_INPUT, offset=0
        )
        if not memories:
            return False

        lines = "\n".join(f"- [{m.category}] {m.text}" for m in memories)
        messages = [
            {"role": "system", "content": self._PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": f"Memories about the user:\n\n{lines}"},
        ]

        try:
            kwargs: dict[str, Any] = {}
            if provider.lightweight_model:
                kwargs["model"] = provider.lightweight_model
            content = await provider.get_response(messages, **kwargs)
        except Exception as e:
            _LOGGER.debug("Persona generation LLM call failed: %s", e)
            return False

        if not content:
            return False

        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        from .auto_capture import ANTI_PATTERNS

        if any(p.search(content) for p in ANTI_PATTERNS):
            _LOGGER.warning("Persona generation produced unsafe content, skipping")
            return False

        if len(content) > self._PERSONA_MAX_CHARS:
            content = content[: self._PERSONA_MAX_CHARS]

        await self._persona_store.save_persona(
            user_id, content, memory_count=count
        )
        _LOGGER.info(
            "Regenerated persona for user %s (%d memories)", user_id, count
        )
        return True

    async def get_persona_content(self, user_id: str) -> str | None:
        """Return the persona Markdown for prompt injection, or None."""
        if not self._initialized or not self._persona_store:
            return None
        persona = await self._persona_store.get_persona(user_id)
        return persona.content if persona else None
```

Uwaga: jeśli faktyczna sygnatura `MemoryStore.list_memories` (memory_store.py:610) różni się (np. `category` jako pozycyjny), dopasuj wywołanie do niej — kontrakt: pobierz do 200 wspomnień usera posortowanych `importance DESC`.

- [ ] **Step 4: Uruchom testy**

Run: `pytest tests/test_memory/test_persona_generation.py tests/test_memory/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/manager.py tests/test_memory/test_persona_generation.py
git commit -m "add persona generation to memory manager"
```

---

### Task 7: Triggery konsolidacji i persony we flushu

Po udanym AI-flushu (jedyne miejsce, gdzie manager ma `provider`) odpalamy konsolidację L2 i regenerację L3 — obie non-fatal.

**Files:**
- Modify: `custom_components/homeclaw/memory/manager.py:340-353` (metoda `flush_from_messages`)
- Test: `tests/test_memory/test_persona_generation.py` (dopisz klasę)

**Interfaces:**
- Consumes: `consolidate_scenarios` (Task 3), `maybe_regenerate_persona` (Task 6).
- Produces: `flush_from_messages` zachowuje sygnaturę i typ zwrotny (`int` — liczba zapisanych wspomnień; wynik konsolidacji/persony NIE wpływa na zwracaną wartość). Konsument: `core/compaction.py:171-181` — bez zmian.

- [ ] **Step 1: Napisz failing test**

Dopisz do `tests/test_memory/test_persona_generation.py`:

```python
class TestFlushTriggers:
    @pytest.mark.asyncio
    async def test_flush_triggers_consolidation_and_persona(
        self, memory_manager, monkeypatch
    ) -> None:
        calls = []

        async def fake_consolidate(user_id, provider):
            calls.append(("consolidate", user_id))
            return 0

        async def fake_persona(user_id, provider):
            calls.append(("persona", user_id))
            return False

        async def fake_ai_flush(messages, user_id, session_id, provider):
            return 2  # pretend 2 memories captured

        monkeypatch.setattr(memory_manager, "consolidate_scenarios", fake_consolidate)
        monkeypatch.setattr(memory_manager, "maybe_regenerate_persona", fake_persona)
        monkeypatch.setattr(memory_manager, "_ai_flush", fake_ai_flush)

        provider = MagicMock()
        captured = await memory_manager.flush_from_messages(
            [{"role": "user", "content": "hi"}], "user1", provider=provider
        )
        assert captured == 2
        assert ("consolidate", "user1") in calls
        assert ("persona", "user1") in calls

    @pytest.mark.asyncio
    async def test_flush_without_provider_skips_triggers(
        self, memory_manager, monkeypatch
    ) -> None:
        calls = []

        async def fake_consolidate(user_id, provider):
            calls.append("consolidate")
            return 0

        monkeypatch.setattr(memory_manager, "consolidate_scenarios", fake_consolidate)

        await memory_manager.flush_from_messages(
            [{"role": "user", "content": "hi"}], "user1"
        )
        assert calls == []

    @pytest.mark.asyncio
    async def test_trigger_failure_does_not_break_flush(
        self, memory_manager, monkeypatch
    ) -> None:
        async def boom(user_id, provider):
            raise RuntimeError("llm down")

        async def fake_ai_flush(messages, user_id, session_id, provider):
            return 1

        monkeypatch.setattr(memory_manager, "consolidate_scenarios", boom)
        monkeypatch.setattr(memory_manager, "maybe_regenerate_persona", boom)
        monkeypatch.setattr(memory_manager, "_ai_flush", fake_ai_flush)

        captured = await memory_manager.flush_from_messages(
            [{"role": "user", "content": "hi"}], "user1", provider=MagicMock()
        )
        assert captured == 1  # flush result survives trigger failures
```

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_persona_generation.py -v -k "Flush"`
Expected: FAIL — `test_flush_triggers_consolidation_and_persona` (triggery nie są wołane).

- [ ] **Step 3: Zaimplementuj triggery**

W `custom_components/homeclaw/memory/manager.py` zastąp ciało `flush_from_messages` (po docstringu — zachowaj istniejący docstring):

```python
        self._ensure_initialized()

        if provider:
            captured = await self._ai_flush(messages, user_id, session_id, provider)
        else:
            # Fallback: explicit commands only
            captured = await self._explicit_flush(messages, user_id, session_id)

        # Post-flush maintenance of higher memory layers (L2 + L3).
        # Both are best-effort: a failure must never break compaction.
        if provider:
            try:
                await self.consolidate_scenarios(user_id, provider)
            except Exception as e:
                _LOGGER.debug("Scenario consolidation failed (non-fatal): %s", e)
            try:
                await self.maybe_regenerate_persona(user_id, provider)
            except Exception as e:
                _LOGGER.debug("Persona regeneration failed (non-fatal): %s", e)

        return captured
```

- [ ] **Step 4: Uruchom testy pamięci**

Run: `pytest tests/test_memory/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/manager.py tests/test_memory/test_persona_generation.py
git commit -m "trigger scenario consolidation and persona regen after memory flush"
```

---

### Task 8: Wstrzyknięcie persony do system promptu

Persona trafia do system promptu w `agent_compat._get_system_prompt`, w bloku `<user-persona>` — po kontekście identity, przed katalogiem narzędzi ON_DEMAND.

**Files:**
- Modify: `custom_components/homeclaw/agent_compat.py:688-732` (metoda `_get_system_prompt`)
- Test: pełna istniejąca suita (regresja) — metoda jest pokryta pośrednio przez testy `agent_compat`/`conversation`

**Interfaces:**
- Consumes: `MemoryManager.get_persona_content(user_id)` (Task 6), `self._rag_manager._memory_manager` (property RAGManager — ten sam dostęp co w `agent_compat.py:475`).
- Produces: system prompt z opcjonalnym blokiem `\n\n<user-persona>\n{content}\n</user-persona>` dodawanym po treści identity/BASE, przed doklejeniem ON_DEMAND tool catalog.

- [ ] **Step 1: Zaimplementuj wstrzyknięcie**

W `custom_components/homeclaw/agent_compat.py`, w metodzie `_get_system_prompt`, wstaw NOWY blok bezpośrednio po zamknięciu `try/except` budującego `system_prompt` z identity (po linii `system_prompt = BASE_SYSTEM_PROMPT` w `except`), a PRZED komentarzem `# Append ON_DEMAND tool catalog...`:

```python
        # Append user persona (L3 memory layer) when available
        if self._rag_manager and self._rag_manager.is_initialized:
            mem_mgr = getattr(self._rag_manager, "_memory_manager", None)
            if mem_mgr:
                try:
                    persona_text = await mem_mgr.get_persona_content(user_id)
                    if persona_text:
                        system_prompt = (
                            f"{system_prompt}\n\n<user-persona>\n"
                            f"{persona_text}\n</user-persona>"
                        )
                except Exception as e:
                    _LOGGER.debug("Persona injection failed (non-fatal): %s", e)
```

Wzorzec dostępu (`is_initialized` + `getattr(..., "_memory_manager", None)`) skopiowany z istniejącego kodu w `agent_compat.py:474-477` — użyj identycznego.

- [ ] **Step 2: Regresja — pełna suita**

Run: `pytest tests/ -v`
Expected: PASS, coverage ≥ 70%. Testy `_get_system_prompt` używają mocków `_rag_manager` bez `_memory_manager` — `getattr(..., None)` sprawia, że dla nich zachowanie jest niezmienione. UWAGA: jeśli któryś test mockuje `_rag_manager` jako `MagicMock` (gdzie `getattr` zwraca auto-mock zamiast None), `get_persona_content` zwróci `AsyncMock`, a `if persona_text:` będzie truthy — wtedy w takim teście dodaj `mock_rag_manager._memory_manager = None` albo `mock_rag_manager.is_initialized = False`. Napraw wyłącznie przez doprecyzowanie mocków, nie przez zmianę logiki produkcyjnej.

- [ ] **Step 3: Commit**

```bash
git add custom_components/homeclaw/agent_compat.py tests/
git commit -m "inject user persona into system prompt"
```

---

### Task 9: GDPR + statystyki + eksporty

Kasowanie wszystkich danych usera obejmuje scenariusze i personę; statystyki WS raportują nowe warstwy; `memory/__init__.py` eksportuje nowe klasy.

**Files:**
- Modify: `custom_components/homeclaw/memory/manager.py` (metoda `forget_all_user_memories` ~linia 240, metoda `get_stats` ~linia 306)
- Modify: `custom_components/homeclaw/memory/__init__.py` (eksporty)
- Test: `tests/test_memory/test_persona_generation.py` (dopisz klasę)

**Interfaces:**
- Consumes: `ScenarioStore.delete_user_scenarios`, `ScenarioStore.count_scenarios` (Task 2), `PersonaStore.delete_persona`, `PersonaStore.get_persona` (Task 5).
- Produces: `forget_all_user_memories(user_id)` usuwa też L2/L3; dict z `get_stats(user_id)` zyskuje klucze `"scenarios": int` i `"persona_generated": bool` (konsument `ws_handlers/rag.py:56` przekazuje dict as-is do frontendu — bez zmian w handlerze).

- [ ] **Step 1: Napisz failing testy**

Dopisz do `tests/test_memory/test_persona_generation.py`:

```python
class TestGdprAndStats:
    @pytest.mark.asyncio
    async def test_forget_all_wipes_scenarios_and_persona(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 5)
        mem_ids = [
            m.id
            for m in await memory_manager._scenario_store.list_ungrouped_memories("user1")
        ]
        await memory_manager._scenario_store.store_scenario(
            user_id="user1", title="T", summary="S",
            embedding=_basis_embedding(0), memory_ids=mem_ids[:3],
        )
        await memory_manager._persona_store.save_persona("user1", "profile", memory_count=5)

        await memory_manager.forget_all_user_memories("user1")

        assert await memory_manager._scenario_store.count_scenarios("user1") == 0
        assert await memory_manager.get_persona_content("user1") is None

    @pytest.mark.asyncio
    async def test_stats_include_layer_info(self, memory_manager) -> None:
        await _seed_memories(memory_manager, 3)
        stats = await memory_manager.get_stats("user1")
        assert stats["scenarios"] == 0
        assert stats["persona_generated"] is False

        await memory_manager._persona_store.save_persona("user1", "p", memory_count=3)
        stats = await memory_manager.get_stats("user1")
        assert stats["persona_generated"] is True
```

- [ ] **Step 2: Uruchom testy — mają failować**

Run: `pytest tests/test_memory/test_persona_generation.py -v -k "Gdpr"`
Expected: FAIL — brak kluczy `scenarios`/`persona_generated` (i ewentualnie persona przeżywa `forget_all_user_memories`).

- [ ] **Step 3: Zaimplementuj**

(a) W `custom_components/homeclaw/memory/manager.py`, w `forget_all_user_memories` (~linia 240), po istniejącym usunięciu wspomnień z `_memory_store`, a przed `return`, dodaj:

```python
        if self._scenario_store:
            try:
                await self._scenario_store.delete_user_scenarios(user_id)
            except Exception as e:
                _LOGGER.debug("Failed to delete user scenarios: %s", e)
        if self._persona_store:
            try:
                await self._persona_store.delete_persona(user_id)
            except Exception as e:
                _LOGGER.debug("Failed to delete user persona: %s", e)
```

(Zachowaj istniejącą wartość zwracaną metody bez zmian.)

(b) W `get_stats` (~linia 306), tuż przed `return`, wzbogać zwracany dict (nazwa zmiennej lokalnej wg istniejącego kodu — najpewniej `stats`):

```python
        if self._scenario_store:
            stats["scenarios"] = await self._scenario_store.count_scenarios(user_id)
        if self._persona_store:
            persona = await self._persona_store.get_persona(user_id)
            stats["persona_generated"] = persona is not None
```

(c) W `custom_components/homeclaw/memory/__init__.py` rozszerz eksporty:

```python
from .manager import MemoryManager
from .persona_store import Persona, PersonaStore
from .scenario_store import Scenario, ScenarioStore

__all__ = [
    "MemoryManager",
    "Persona",
    "PersonaStore",
    "Scenario",
    "ScenarioStore",
]
```

Zaktualizuj też docstring modułu `memory/__init__.py` — do sekcji "Architecture" dopisz:

```
- Layered memory: memories (L1 atoms) -> memory_scenarios (L2 LLM-grouped
  summaries, consolidated after flush) -> user_personas (L3 profile,
  regenerated every ~25 new memories, injected into the system prompt)
- Hybrid recall: vector + FTS5 keyword results fused with Reciprocal Rank
  Fusion; scenario summaries participate in recall alongside atoms
```

- [ ] **Step 4: Uruchom pełną suitę**

Run: `pytest tests/ -v`
Expected: PASS, coverage ≥ 70%.

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/memory/ tests/test_memory/test_persona_generation.py
git commit -m "wipe l2/l3 layers on user forget and expose layer stats"
```
