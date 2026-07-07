"""Memory Manager — orchestrates auto-capture and auto-recall.

This is the main entry point for the LTM system. It wires together:
- MemoryStore (SQLite storage + search)
- Auto-capture (regex triggers → embed → store)
- Auto-recall (embed query → search → format for injection)

Integrates with the existing RAG embedding provider (CachedEmbeddingProvider)
so memory embeddings benefit from the same cache and retry logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .auto_capture import extract_explicit_commands
from .memory_store import Memory, MemoryStore
from .persona_store import PersonaStore
from .scenario_store import ScenarioStore

_LOGGER = logging.getLogger(__name__)

# Auto-recall configuration
RECALL_TOP_K = 3  # Max memories to inject
RECALL_MIN_SIMILARITY = (
    0.35  # Lower threshold than entity RAG (memories are more varied)
)

# RRF constant — dampens the impact of top ranks (standard value from the literature)
RRF_K = 60


@dataclass
class MemoryManager:
    """Facade for the Long-Term Memory system.

    Orchestrates memory storage, auto-capture from conversations,
    and auto-recall for system prompt injection.

    Args:
        store: SqliteStore instance from the RAG system.
        embedding_provider: CachedEmbeddingProvider from the RAG system.
    """

    store: Any  # SqliteStore
    embedding_provider: Any  # CachedEmbeddingProvider or EmbeddingProvider
    _memory_store: MemoryStore | None = field(default=None, repr=False)
    _scenario_store: ScenarioStore | None = field(default=None, repr=False)
    _persona_store: PersonaStore | None = field(default=None, repr=False)
    _initialized: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        """Initialize the memory system.

        Creates memory tables in the existing SQLite database.
        """
        if self._initialized:
            return

        self._memory_store = MemoryStore(store=self.store)
        await self._memory_store.async_initialize()

        self._scenario_store = ScenarioStore(store=self.store)
        await self._scenario_store.async_initialize()

        self._persona_store = PersonaStore(store=self.store)
        await self._persona_store.async_initialize()

        self._initialized = True
        _LOGGER.info("Memory manager initialized")

    def _ensure_initialized(self) -> None:
        """Ensure memory system is ready."""
        if not self._initialized or not self._memory_store:
            raise RuntimeError(
                "MemoryManager not initialized. Call async_initialize() first."
            )

    async def capture_explicit_commands(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        session_id: str = "",
    ) -> int:
        """Capture explicit "remember this" commands from messages.

        Safety net for when the LLM doesn't call memory_store on explicit
        user commands like "zapamiętaj" or "remember". All other memory
        capture is handled by the LLM via memory_store tool.

        Args:
            messages: Conversation messages (role + content dicts).
            user_id: User who owns these memories.
            session_id: Session where conversation happened.

        Returns:
            Number of new memories captured.
        """
        self._ensure_initialized()

        candidates = extract_explicit_commands(messages)
        if not candidates:
            return 0

        captured = 0
        for candidate in candidates:
            try:
                text = candidate["text"]
                embeddings = await self.embedding_provider.get_embeddings([text])
                if not embeddings or not embeddings[0]:
                    continue

                memory_id = await self._memory_store.store_memory(
                    text=text,
                    embedding=embeddings[0],
                    user_id=user_id,
                    category=candidate["category"],
                    importance=candidate["importance"],
                    source="auto",
                    session_id=session_id,
                )

                if memory_id:
                    captured += 1
                    _LOGGER.info(
                        "Explicit-captured [%s]: %s",
                        candidate["category"],
                        text[:80],
                    )
            except Exception as e:
                _LOGGER.debug("Failed to capture explicit command: %s", e)

        return captured

    async def recall_for_query(
        self,
        query: str,
        user_id: str,
        *,
        top_k: int = RECALL_TOP_K,
        min_similarity: float = RECALL_MIN_SIMILARITY,
    ) -> list[dict[str, Any]]:
        """Recall relevant memories for a user query.

        Performs hybrid search (vector + keyword) on user's memories
        and formats results for system prompt injection.

        Args:
            query: The user's query text.
            user_id: User whose memories to search.
            top_k: Maximum memories to return.
            min_similarity: Minimum relevance threshold.

        Returns:
            List of memory dictionaries, or empty list.
        """
        self._ensure_initialized()

        try:
            # Generate query embedding
            embeddings = await self.embedding_provider.get_embeddings([query])
            if not embeddings or not embeddings[0]:
                return []

            query_embedding = embeddings[0]

            # Vector search
            vector_results = await self._memory_store.search_memories(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=top_k * 3,  # Over-fetch for merge
                min_similarity=min_similarity,
            )

            # Keyword search (if available)
            keyword_results = []
            fts_query = _build_memory_fts_query(query)
            if fts_query:
                keyword_results = await self._memory_store.keyword_search_memories(
                    fts_query=fts_query,
                    user_id=user_id,
                    limit=top_k * 3,
                )

            # Merge results (hybrid: dedup by ID, boost overlapping)
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

        except Exception as e:
            _LOGGER.debug("Memory recall failed: %s", e)
            return []

    async def store_memory(
        self,
        text: str,
        user_id: str,
        *,
        category: str = "fact",
        importance: float = 0.8,
        source: str = "user",
        session_id: str = "",
        ttl_days: int | None = None,
    ) -> str | None:
        """Manually store a memory (called by agent tools or user).

        Args:
            text: What to remember.
            user_id: User who owns this memory.
            category: Memory category.
            importance: Importance score 0.0-1.0.
            source: Origin ("user", "agent").
            session_id: Optional session context.
            ttl_days: Time-to-live in days. None uses category default.

        Returns:
            Memory ID if stored, None if duplicate.
        """
        self._ensure_initialized()

        embeddings = await self.embedding_provider.get_embeddings([text])
        if not embeddings or not embeddings[0]:
            return None

        return await self._memory_store.store_memory(
            text=text,
            embedding=embeddings[0],
            user_id=user_id,
            category=category,
            importance=importance,
            source=source,
            session_id=session_id,
            ttl_days=ttl_days,
        )

    async def forget_memory(self, memory_id: str) -> bool:
        """Delete a specific memory.

        Args:
            memory_id: ID of the memory to delete.

        Returns:
            True if deleted successfully.
        """
        self._ensure_initialized()
        return await self._memory_store.delete_memory(memory_id)

    async def forget_all_user_memories(self, user_id: str) -> int:
        """Delete all memories for a user (GDPR).

        Args:
            user_id: User whose memories to purge.

        Returns:
            Number of memories deleted.
        """
        self._ensure_initialized()
        return await self._memory_store.delete_user_memories(user_id)

    async def search_memories(
        self,
        query: str,
        user_id: str,
        *,
        limit: int = 10,
    ) -> list[Memory]:
        """Search user memories by text query.

        Args:
            query: Search query.
            user_id: User whose memories to search.
            limit: Max results.

        Returns:
            List of Memory objects.
        """
        self._ensure_initialized()

        embeddings = await self.embedding_provider.get_embeddings([query])
        if not embeddings or not embeddings[0]:
            return []

        return await self._memory_store.search_memories(
            query_embedding=embeddings[0],
            user_id=user_id,
            limit=limit,
            min_similarity=0.2,  # Lower threshold for explicit search
        )

    async def list_memories(
        self,
        user_id: str,
        *,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        """List all memories for a user (paginated, no search).

        Args:
            user_id: User whose memories to list.
            category: Optional category filter.
            limit: Max results per page.
            offset: Pagination offset.

        Returns:
            List of Memory objects.
        """
        self._ensure_initialized()
        return await self._memory_store.list_memories(
            user_id, category=category, limit=limit, offset=offset
        )

    async def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Get memory statistics."""
        self._ensure_initialized()
        return await self._memory_store.get_stats(user_id)

    # --- AI-powered memory flush (pre-compaction) ---

    # Prompt that instructs the LLM to extract durable memories
    _FLUSH_SYSTEM_PROMPT = (
        "You are a memory extraction assistant. Analyze the conversation below and "
        "extract information worth remembering long-term.\n\n"
        "EXTRACT:\n"
        "- User preferences (likes, dislikes, preferred settings, routines)\n"
        "- Personal facts (name, family, pets, work, habits, home layout)\n"
        "- Decisions made (choices about setup, naming, configurations)\n"
        "- Problems solved (what broke, how it was fixed)\n"
        "- Interesting patterns (recurring topics, behavioral observations)\n\n"
        "FORMAT: Return a JSON array of memory objects. Each memory must have:\n"
        '- "text": The memory with context (2-3 sentences: WHAT + WHY + WHEN it matters)\n'
        '- "category": One of "preference", "fact", "decision", "observation"\n'
        '- "importance": 0.0-1.0 (how important is this to remember?)\n\n'
        "RULES:\n"
        "- Include CONTEXT — not just bare facts. Say WHY and WHEN it matters.\n"
        "- Write in the SAME LANGUAGE as the conversation.\n"
        "- Max 8 memories. Only extract what's genuinely worth remembering.\n"
        "- If nothing worth remembering, return an empty array: []\n\n"
        "Example output:\n"
        '[{"text": "User prefers warm white lights in the bedroom. Discussed during '
        'bedtime scene setup — partner finds cool white too harsh.", '
        '"category": "preference", "importance": 0.8}]'
    )

    _FLUSH_MAX_MEMORIES = 8

    # --- Scenario consolidation (L2) ---

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

    # --- Persona generation (L3) ---

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

    async def flush_from_messages(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        session_id: str = "",
        provider: Any | None = None,
    ) -> int:
        """AI-powered memory extraction from messages about to be compacted.

        Uses the LLM to analyze the conversation and extract durable memories
        with context. Falls back to explicit-command-only capture if no provider
        is available.

        Args:
            messages: Conversation messages that will be discarded.
            user_id: User who owns the resulting memories.
            session_id: Session context.
            provider: AI provider for LLM-powered extraction. If None, falls
                back to explicit command detection only.

        Returns:
            Number of new memories captured.
        """
        self._ensure_initialized()

        if provider:
            return await self._ai_flush(messages, user_id, session_id, provider)

        # Fallback: explicit commands only
        return await self._explicit_flush(messages, user_id, session_id)

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

    async def _ai_flush(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        session_id: str,
        provider: Any,
    ) -> int:
        """Extract memories using AI analysis."""
        import json as _json

        # Format conversation for the LLM
        formatted_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content") or ""
            if role == "system":
                continue
            if len(content) > 1000:
                content = content[:900] + "\n... [truncated]"
            formatted_lines.append(f"[{role}]: {content}")

        conversation_text = "\n\n".join(formatted_lines)

        # Cap input size
        if len(conversation_text) > 20_000:
            conversation_text = conversation_text[:20_000] + "\n\n... [truncated]"

        flush_messages = [
            {"role": "system", "content": self._FLUSH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract memories from this conversation ({len(messages)} messages):\n\n{conversation_text}",
            },
        ]

        try:
            # Use lightweight model for background memory extraction
            flush_kwargs: dict[str, Any] = {}
            if provider.lightweight_model:
                flush_kwargs["model"] = provider.lightweight_model

            response = await provider.get_response(flush_messages, **flush_kwargs)
            if not response:
                _LOGGER.debug("AI flush returned empty response")
                return 0

            # Parse JSON from response (handle markdown code blocks)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            memories = _json.loads(response)
            if not isinstance(memories, list):
                _LOGGER.warning("AI flush returned non-list: %s", type(memories))
                return 0

        except (_json.JSONDecodeError, Exception) as e:
            _LOGGER.warning("AI flush failed (%s), falling back to explicit capture", e)
            return await self._explicit_flush(messages, user_id, session_id)

        captured = 0
        for mem in memories[: self._FLUSH_MAX_MEMORIES]:
            try:
                text = mem.get("text", "")
                category = mem.get("category", "fact")
                importance = float(mem.get("importance", 0.7))

                if not text or len(text) < 10:
                    continue

                # Sanitize: reject memories containing control tokens or injections
                from .auto_capture import ANTI_PATTERNS

                if any(pattern.search(text) for pattern in ANTI_PATTERNS):
                    _LOGGER.warning(
                        "AI flush produced unsafe memory, skipping: %s", text[:80]
                    )
                    continue

                importance = max(0.1, min(1.0, importance))
                if category not in (
                    "preference",
                    "fact",
                    "decision",
                    "observation",
                    "entity",
                ):
                    category = "fact"

                embeddings = await self.embedding_provider.get_embeddings([text])
                if not embeddings or not embeddings[0]:
                    continue

                memory_id = await self._memory_store.store_memory(
                    text=text,
                    embedding=embeddings[0],
                    user_id=user_id,
                    category=category,
                    importance=importance,
                    source="ai_flush",
                    session_id=session_id,
                )

                if memory_id:
                    captured += 1
                    _LOGGER.info("AI-flush captured [%s]: %s", category, text[:80])
            except Exception as e:
                _LOGGER.debug("Failed to store AI-flush memory: %s", e)

        _LOGGER.info(
            "AI flush captured %d memories from %d messages", captured, len(messages)
        )
        return captured

    async def _explicit_flush(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        session_id: str,
    ) -> int:
        """Fallback: capture only explicit 'remember' commands."""
        candidates = extract_explicit_commands(messages, max_captures=5)
        if not candidates:
            return 0

        captured = 0
        for candidate in candidates:
            try:
                text = candidate["text"]
                embeddings = await self.embedding_provider.get_embeddings([text])
                if not embeddings or not embeddings[0]:
                    continue

                memory_id = await self._memory_store.store_memory(
                    text=text,
                    embedding=embeddings[0],
                    user_id=user_id,
                    category=candidate["category"],
                    importance=candidate["importance"],
                    source="auto",
                    session_id=session_id,
                )

                if memory_id:
                    captured += 1
            except Exception as e:
                _LOGGER.debug("Failed to flush explicit command: %s", e)

        return captured


def _build_memory_fts_query(query: str) -> str | None:
    """Build FTS5 query from raw text — same approach as RAG query engine."""
    import re

    tokens = re.findall(r"[A-Za-z0-9_\u00C0-\u024F]+", query)
    if not tokens:
        return None

    # Quote each token and AND them together
    quoted = [f'"{t}"' for t in tokens if len(t) >= 2]
    if not quoted:
        return None

    return " AND ".join(quoted)


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


def _format_memories_for_prompt(memories: list[Memory]) -> list[dict[str, Any]]:
    """Format memories for injection into the JSON context block.

    Args:
        memories: List of relevant Memory objects.

    Returns:
        List of dictionaries representing the memories.
    """
    import time as _time

    result = []
    now = _time.time()
    for mem in memories:
        mem_data = {
            "category": mem.category,
            "information": mem.text,
        }
        if mem.expires_at:
            days_left = max(0, (mem.expires_at - now) / 86400)
            mem_data["expires_in_days"] = int(days_left)
        result.append(mem_data)

    return result
