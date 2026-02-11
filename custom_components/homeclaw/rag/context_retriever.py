"""RAG context retrieval logic.

Handles semantic search for entities + session history + long-term memory,
combining them into a single context string for the LLM.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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
    ) -> str:
        """Get relevant entity context for a user query.

        Uses semantic search to find entities related to the query
        and returns a compressed context string suitable for LLM.

        Includes self-healing: removes stale entities from the index
        if they no longer exist in Home Assistant.

        If user_id is provided and long-term memory is initialized,
        relevant memories are also included in the context.

        Args:
            query: The user's query text.
            top_k: Maximum number of entities to include.
            user_id: Optional user ID for memory recall.

        Returns:
            Compressed context string for the LLM, or empty string if no results.
        """
        try:
            # Extract intent from query using semantic similarity (cached embeddings)
            intent = await self._intent_detector.detect_intent(query)

            # Pre-filter: Skip RAG if query clearly not HA-related
            if not intent:
                query_lower = query.lower()
                ha_keywords = [
                    # English
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
                    # Polish
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

                if not any(keyword in query_lower for keyword in ha_keywords):
                    _LOGGER.debug(
                        "RAG pre-filter: Query doesn't appear HA-related, skipping search: %s",
                        query[:100],
                    )
                    return ""

            # Determine which filters to apply
            use_domain = intent.get("domain")
            use_device_class = intent.get("device_class") if not use_domain else None
            use_area = intent.get("area")

            # Build where filter from intent (if any)
            where_filter: dict[str, Any] = {}
            if use_domain:
                where_filter["domain"] = use_domain
            if use_device_class:
                where_filter["device_class"] = use_device_class
            if use_area:
                where_filter["area_name"] = use_area

            if where_filter:
                _LOGGER.debug(
                    "RAG using hybrid search with intent filters: %s (raw: %s)",
                    where_filter,
                    intent,
                )

            # Use hybrid search (vector + FTS5 keyword)
            results = await self._query_engine.hybrid_search(
                query=query,
                top_k=top_k,
                where=where_filter if where_filter else None,
                min_similarity=RAG_MIN_SIMILARITY,
            )

            # Fallback: if no results with filters, retry without filters
            if not results and where_filter:
                _LOGGER.debug(
                    "RAG hybrid search with filters returned 0 results, falling back without filters"
                )
                results = await self._query_engine.hybrid_search(
                    query=query,
                    top_k=top_k,
                    min_similarity=RAG_MIN_SIMILARITY,
                )

            # Early return if no results pass threshold
            if not results:
                _LOGGER.debug(
                    "RAG search returned no results above similarity threshold"
                )
                return ""

            # Log top similarity scores with entity IDs for diagnostics
            if results:
                top_entries = [f"{r.id}={1.0 - r.distance:.3f}" for r in results[:5]]
                _LOGGER.debug(
                    "RAG search returned %d results (top scores: %s)",
                    len(results),
                    ", ".join(top_entries),
                )

            # Validate entities exist and remove stale ones
            valid_results = []
            stale_entities = []

            for result in results:
                entity_id = result.id
                if self._hass.states.get(entity_id):
                    valid_results.append(result)
                else:
                    stale_entities.append(entity_id)

            # Remove stale entities from index (self-healing)
            if stale_entities:
                _LOGGER.warning(
                    "Found %d stale entities in RAG index, removing: %s",
                    len(stale_entities),
                    stale_entities,
                )
                for entity_id in stale_entities:
                    try:
                        await self._indexer.remove_entity(entity_id)
                    except Exception as e:
                        _LOGGER.error(
                            "Failed to remove stale entity %s: %s", entity_id, e
                        )

            # Build entity context from valid results
            entity_context = self._query_engine.build_compressed_context(valid_results)

            # Search session chunks for conversational context
            session_context = ""
            try:
                session_context = await self._get_session_context(query)
            except Exception as sess_err:
                _LOGGER.debug("Session context retrieval failed: %s", sess_err)

            # Recall long-term memories (if user_id provided)
            memory_context = ""
            if user_id and self._memory_manager:
                try:
                    memory_context = await self._memory_manager.recall_for_query(
                        query, user_id
                    )
                except Exception as mem_err:
                    _LOGGER.debug("Memory recall failed: %s", mem_err)

            # Combine all context sources
            parts = [p for p in [memory_context, entity_context, session_context] if p]
            context = "\n\n".join(parts)

            if context:
                _LOGGER.debug(
                    "RAG context generated (%d chars, memory=%d, entity=%d, session=%d) for query: %s...",
                    len(context),
                    len(memory_context),
                    len(entity_context),
                    len(session_context),
                    query[:50],
                )
            return context

        except Exception as e:
            _LOGGER.warning("RAG context retrieval failed: %s", e)
            return ""

    async def _get_session_context(
        self,
        query: str,
        top_k: int = 3,
    ) -> str:
        """Search session chunks for relevant conversational context.

        Args:
            query: The user's query text.
            top_k: Maximum number of session chunks to include.

        Returns:
            Formatted session context string, or empty string if no results.
        """
        from .embeddings import get_embedding_for_query
        from .query_engine import build_fts_query, merge_hybrid_results

        # Vector search on session chunks
        query_embedding = await get_embedding_for_query(self._embedding_provider, query)
        vector_results = await self._store.search_session_chunks(
            query_embedding=query_embedding,
            n_results=top_k * 4,
            min_similarity=RAG_MIN_SIMILARITY,
        )

        # Keyword search on session chunks (if FTS5 available)
        keyword_results = []
        fts_query = build_fts_query(query)
        if fts_query:
            keyword_results = await self._store.keyword_search_sessions(
                fts_query=fts_query,
                n_results=top_k * 4,
            )

        # Merge if we have both types of results
        if vector_results and keyword_results:
            results = merge_hybrid_results(
                vector_results,
                keyword_results,
                vector_weight=0.7,
                text_weight=0.3,
            )
        elif vector_results:
            results = vector_results
        elif keyword_results:
            results = keyword_results
        else:
            return ""

        # Apply similarity threshold and limit
        results = [r for r in results if (1.0 - r.distance) >= RAG_MIN_SIMILARITY][
            :top_k
        ]

        if not results:
            return ""

        # Format session chunks as context
        lines = ["Relevant previous conversations:"]
        for r in results:
            text = r.text
            if len(text) > 500:
                text = text[:500] + "..."
            lines.append(f"---\n{text}")

        _LOGGER.debug(
            "Session context: %d chunks found for query: %s...",
            len(results),
            query[:50],
        )
        return "\n".join(lines)
