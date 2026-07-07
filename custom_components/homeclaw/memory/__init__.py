"""Long-Term Memory (LTM) system for Homeclaw.

Provides persistent memory across sessions — user preferences, facts, decisions
are captured via three mechanisms:

1. LLM proactive capture: The agent calls memory_store tool during conversations
   when it learns something worth remembering (primary mechanism).
2. AI-powered flush: Before context compaction, an LLM analyzes old messages and
   extracts durable memories with context (pre-compaction safety net).
3. Explicit command capture: Regex detects "zapamiętaj"/"remember" commands as a
   fallback if the LLM misses them.

Architecture:
- Storage: SQLite tables in the existing RAG database (no new dependencies)
- Auto-Recall: Relevant memories are injected into the system prompt before processing
- Layered memory: memories (L1 atoms) -> memory_scenarios (L2 LLM-grouped
  summaries, consolidated after flush) -> user_personas (L3 profile,
  regenerated every ~25 new memories, injected into the system prompt)
- Hybrid recall: vector + FTS5 keyword results fused with Reciprocal Rank
  Fusion; scenario summaries participate in recall alongside atoms

Usage:
    manager = MemoryManager(store, embedding_provider)
    await manager.async_initialize()

    # Auto-recall before query processing
    context = await manager.recall_for_query(query, user_id)

    # Manual management
    await manager.store_memory("User prefers short answers", user_id, category="preference")
    results = await manager.search_memories("answer style", user_id)
    await manager.forget_memory(memory_id)
"""

from __future__ import annotations

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
