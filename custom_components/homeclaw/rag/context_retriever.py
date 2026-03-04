"""RAG context retrieval logic.

Handles semantic search for entities + session history + long-term memory,
combining them into a single context string for the LLM.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from ._session_context import get_session_context
from ._temporal import has_temporal_hint

# Backward-compatible alias — tests import _has_temporal_hint from here.
_has_temporal_hint = has_temporal_hint

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Re-use the minimum similarity threshold from the package
RAG_MIN_SIMILARITY = 0.5


class RAGContextRetriever:
    """Retrieves relevant context from RAG subsystems.

    Combines entity search, session history search, and long-term memory
    recall into a single compressed context string.

    All components are injected; this class holds no lifecycle logic.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        query_engine: Any,
        intent_detector: Any,
        embedding_provider: Any,
        store: Any,
        indexer: Any,
        session_indexer: Any | None = None,
        memory_manager: Any | None = None,
    ) -> None:
        """Initialize the context retriever.

        Args:
            hass: Home Assistant instance.
            query_engine: QueryEngine for hybrid search.
            intent_detector: IntentDetector for semantic intent extraction.
            embedding_provider: EmbeddingProvider (cached) for query embeddings.
            store: SqliteStore for low-level search operations.
            indexer: EntityIndexer for stale-entity removal.
            session_indexer: Optional SessionIndexer.
            memory_manager: Optional MemoryManager for long-term recall.
        """
        self._hass = hass
        self._query_engine = query_engine
        self._intent_detector = intent_detector
        self._embedding_provider = embedding_provider
        self._store = store
        self._indexer = indexer
        self._session_indexer = session_indexer
        self._memory_manager = memory_manager

    async def get_relevant_context(
        self,
        query: str,
        top_k: int = 10,
        user_id: str | None = None,
        provider: Any | None = None,
        model: str | None = None,
    ) -> str:
        """Get relevant entity context for a user query.

        Uses semantic search to find entities related to the query
        and returns a structured JSON context string suitable for LLM.

        Includes self-healing: removes stale entities from the index
        if they no longer exist in Home Assistant.

        If user_id is provided and long-term memory is initialized,
        relevant memories are also included in the context.

        Args:
            query: The user's query text.
            top_k: Maximum number of entities to include.
            user_id: Optional user ID for memory recall.
            provider: Optional AI provider for query expansion.
            model: Optional model name for query expansion.

        Returns:
            JSON-formatted context string for the LLM, or empty string if no results.
        """
        try:
            results = await self._search_entities(query, top_k)
            valid_results = await self._validate_and_heal(results)

            context_data: dict[str, Any] = {}

            # Build entity context from valid results
            if valid_results:
                entity_context = self._query_engine.build_compressed_context(
                    valid_results
                )
                if entity_context:
                    context_data["relevant_entities"] = entity_context

            # Search session chunks for conversational context
            try:
                session_ctx = await get_session_context(
                    query,
                    self._embedding_provider,
                    self._store,
                    RAG_MIN_SIMILARITY,
                    top_k=3,
                    provider=provider,
                    model=model,
                )
                if session_ctx:
                    context_data["previous_conversations"] = session_ctx
            except Exception as sess_err:
                _LOGGER.debug("Session context retrieval failed: %s", sess_err)

            # Recall long-term memories (if user_id provided)
            if user_id and self._memory_manager:
                try:
                    memory_context = await self._memory_manager.recall_for_query(
                        query, user_id
                    )
                    if memory_context:
                        context_data["long_term_memories"] = memory_context
                except Exception as mem_err:
                    _LOGGER.debug("Memory recall failed: %s", mem_err)

            if context_data:
                context_str = json.dumps(
                    context_data, ensure_ascii=False, separators=(",", ":")
                )
                _LOGGER.debug(
                    "RAG context generated (%d chars) for query: %s...",
                    len(context_str),
                    query[:50],
                )
                return context_str

            return ""

        except Exception as e:
            _LOGGER.warning("RAG context retrieval failed: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _search_entities(
        self,
        query: str,
        top_k: int,
    ) -> list[Any]:
        """Run hybrid entity search with intent-based filtering and fallback.

        Args:
            query: The user's query text.
            top_k: Maximum number of entities to return.

        Returns:
            List of SearchResult objects (may be empty).
        """
        intent = await self._intent_detector.detect_intent(query)

        # Pre-filter: Skip RAG if query clearly not HA-related
        if not intent and not self._looks_ha_related(query):
            _LOGGER.debug(
                "RAG pre-filter: Query doesn't appear HA-related, skipping search: %s",
                query[:100],
            )
            return []

        where_filter = self._build_intent_filter(intent)
        if where_filter:
            _LOGGER.debug(
                "RAG using hybrid search with intent filters: %s (raw: %s)",
                where_filter,
                intent,
            )

        results = await self._query_engine.hybrid_search(
            query=query,
            top_k=top_k,
            where=where_filter if where_filter else None,
            min_similarity=RAG_MIN_SIMILARITY,
        )

        # Fallback: if no results with filters, retry without
        if not results and where_filter:
            _LOGGER.debug(
                "RAG hybrid search with filters returned 0 results, falling back without filters"
            )
            results = await self._query_engine.hybrid_search(
                query=query, top_k=top_k, min_similarity=RAG_MIN_SIMILARITY
            )

        if not results:
            _LOGGER.debug("RAG search returned no results above similarity threshold")
        elif results:
            top_entries = [f"{r.id}={1.0 - r.distance:.3f}" for r in results[:5]]
            _LOGGER.debug(
                "RAG search returned %d results (top scores: %s)",
                len(results),
                ", ".join(top_entries),
            )

        return results

    async def _validate_and_heal(self, results: list[Any]) -> list[Any]:
        """Validate entities exist in HA and remove stale ones from index.

        Args:
            results: SearchResult list from hybrid search.

        Returns:
            Filtered list with only currently-valid entities.
        """
        valid = []
        stale = []

        for result in results:
            if self._hass.states.get(result.id):
                valid.append(result)
            else:
                stale.append(result.id)

        if stale:
            _LOGGER.warning(
                "Found %d stale entities in RAG index, removing: %s", len(stale), stale
            )
            for entity_id in stale:
                try:
                    await self._indexer.remove_entity(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to remove stale entity %s: %s", entity_id, e)

        return valid

    @staticmethod
    def _looks_ha_related(query: str) -> bool:
        """Cheap keyword check for Home Assistant relevance."""
        query_lower = query.lower()
        ha_keywords = [
            "light",
            "turn",
            "switch",
            "temperature",
            "sensor",
            "automation",
            "scene",
            "device",
            "home",
            "room",
            "cover",
            "blind",
            "lock",
            "fan",
            "climate",
            "thermostat",
            "światło",
            "światła",
            "włącz",
            "wyłącz",
            "temperatura",
            "czujnik",
            "urządzenie",
            "dom",
            "pokój",
            "roleta",
        ]
        return any(kw in query_lower for kw in ha_keywords)

    @staticmethod
    def _build_intent_filter(intent: dict[str, Any] | None) -> dict[str, Any]:
        """Convert detected intent into a where-filter dict."""
        if not intent:
            return {}

        where: dict[str, Any] = {}
        domain = intent.get("domain")
        if domain:
            where["domain"] = domain
        else:
            device_class = intent.get("device_class")
            if device_class:
                where["device_class"] = device_class
        area = intent.get("area")
        if area:
            where["area_name"] = area
        return where
