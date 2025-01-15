"""RAG (Retrieval-Augmented Generation) system for Homeclaw.

This module provides semantic search capabilities for Home Assistant entities,
learning from conversations to improve entity categorization over time.

Uses SQLite for vector storage - no external dependencies required.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# RAG search configuration
RAG_MIN_SIMILARITY = 0.5  # Minimum cosine similarity (0-1) for search results
# 0.5 = 50% similarity, reasonable default
# Lower = more results (higher recall, lower precision)
# Higher = fewer but more relevant results (lower recall, higher precision)

# Re-export for external use
__all__ = [
    "RAGManager",
]


@dataclass
class RAGManager:
    """Facade for the RAG system.

    Orchestrates all RAG components: SQLite storage, embeddings,
    entity indexing, query engine, session indexing, and semantic learning.

    Usage:
        rag = RAGManager(hass, config, config_entry)
        await rag.async_initialize()
        context = await rag.get_relevant_context("turn on bedroom light")
        await rag.index_session(session_id, messages)
        await rag.async_shutdown()
    """

    hass: HomeAssistant
    config: dict[str, Any]
    config_entry: ConfigEntry | None = None
    _store: Any | None = field(default=None, repr=False)  # SqliteStore
    _embedding_provider: Any | None = field(
        default=None, repr=False
    )  # EmbeddingProvider
    _indexer: Any | None = field(default=None, repr=False)  # EntityIndexer
    _query_engine: Any | None = field(default=None, repr=False)  # QueryEngine
    _intent_detector: Any | None = field(default=None, repr=False)  # IntentDetector
    _learner: Any | None = field(default=None, repr=False)  # SemanticLearner
    _session_indexer: Any | None = field(default=None, repr=False)  # SessionIndexer
    _event_handlers: Any | None = field(
        default=None, repr=False
    )  # EntityRegistryEventHandler
    _state_handler: Any | None = field(default=None, repr=False)  # StateChangeHandler
    _memory_manager: Any | None = field(default=None, repr=False)  # MemoryManager
    _identity_manager: Any | None = field(default=None, repr=False)  # IdentityManager
    _initialized: bool = field(default=False, repr=False)

    def _get_persist_directory(self) -> str:
        """Get the SQLite persist directory path."""
        # Use HA config directory: /config/homeclaw/rag_db/
        config_dir = self.hass.config.path("homeclaw", "rag_db")
        return config_dir

    async def async_initialize(self) -> None:
        """Initialize all RAG components.

        This initializes:
        1. SQLite vector storage
        2. Embedding provider
        3. Entity indexer (imports lazily to avoid circular imports)
        4. Query engine
        5. Semantic learner
        6. Event handlers for entity registry updates
        """
        if self._initialized:
            _LOGGER.debug("RAGManager already initialized")
            return

        try:
            _LOGGER.info("Initializing RAG system...")

            # 1. Initialize SQLite storage
            from .sqlite_store import SqliteStore

            persist_dir = self._get_persist_directory()
            self._store = SqliteStore(persist_directory=persist_dir)
            await self._store.async_initialize()

            # 2. Initialize embedding provider (with caching wrapper)
            from .embeddings import CachedEmbeddingProvider, create_embedding_provider

            raw_provider = create_embedding_provider(
                self.hass, self.config, self.config_entry
            )
            # Wrap with SHA-256 content-addressable cache + retry logic
            self._embedding_provider = CachedEmbeddingProvider(
                inner=raw_provider,
                store=self._store,
            )
            _LOGGER.info(
                "RAG using embedding provider: %s (with cache)",
                self._embedding_provider.provider_name,
            )

            # 3. Initialize entity indexer
            from .entity_indexer import EntityIndexer

            self._indexer = EntityIndexer(
                hass=self.hass,
                store=self._store,
                embedding_provider=self._embedding_provider,
            )

            # 4. Initialize query engine
            from .query_engine import QueryEngine

            self._query_engine = QueryEngine(
                store=self._store,
                embedding_provider=self._embedding_provider,
            )

            # 5. Initialize intent detector (semantic intent detection with cached embeddings)
            from .intent_detector import IntentDetector

            self._intent_detector = IntentDetector(
                embedding_provider=self._embedding_provider,
            )
            await self._intent_detector.async_initialize()

            # 6. Initialize session indexer (conversation history indexing)
            from .session_indexer import SessionIndexer

            self._session_indexer = SessionIndexer(
                store=self._store,
                embedding_provider=self._embedding_provider,
            )
            _LOGGER.debug("Session indexer initialized")

            # 6b. Initialize long-term memory manager
            try:
                from ..memory.manager import MemoryManager

                self._memory_manager = MemoryManager(
                    store=self._store,
                    embedding_provider=self._embedding_provider,
                )
                await self._memory_manager.async_initialize()
                _LOGGER.info("Long-term memory manager initialized")
            except Exception as mem_err:
                _LOGGER.warning("Long-term memory init failed (non-fatal): %s", mem_err)
                self._memory_manager = None

            # 6c. Initialize identity manager
            try:
                from ..memory.identity_manager import IdentityManager

                self._identity_manager = IdentityManager(store=self._store)
                await self._identity_manager.async_initialize()
                _LOGGER.info("Identity manager initialized")
            except Exception as id_err:
                _LOGGER.warning("Identity manager init failed (non-fatal): %s", id_err)
                self._identity_manager = None

            # 7. Initialize semantic learner
            from .semantic_learner import SemanticLearner

            learner_storage_path = self.hass.config.path(
                "homeclaw", "learned_categories.json"
            )
            self._learner = SemanticLearner(
                hass=self.hass,
                indexer=self._indexer,
                storage_path=learner_storage_path,
            )
            await self._learner.async_load()

            # 7. Initialize event handlers
            from .event_handlers import EntityRegistryEventHandler, StateChangeHandler

            self._event_handlers = EntityRegistryEventHandler(
                hass=self.hass,
                indexer=self._indexer,
            )
            await self._event_handlers.async_start()

            # 8. Initialize state change handler (debounced reindexing on state changes)
            self._state_handler = StateChangeHandler(
                hass=self.hass,
                indexer=self._indexer,
            )
            await self._state_handler.async_start()

            # 8. Check if embedding provider or configuration changed (auto-reindex)
            provider_name = self._embedding_provider.provider_name
            stored_provider = await self._store.get_metadata("embedding_provider")

            reindex_needed = False

            if stored_provider and stored_provider != provider_name:
                _LOGGER.warning(
                    "Embedding provider changed from %s to %s, triggering full reindex",
                    stored_provider,
                    provider_name,
                )
                reindex_needed = True
            elif not stored_provider:
                # First run, store current provider
                await self._store.set_metadata("embedding_provider", provider_name)
                _LOGGER.info("Stored embedding provider: %s", provider_name)

            # Check if embedding dimension changed (e.g., model upgrade)
            stored_dimension = await self._store.get_metadata("embedding_dimension")
            current_dimension = str(self._embedding_provider.dimension)
            if stored_dimension and stored_dimension != current_dimension:
                _LOGGER.warning(
                    "Embedding dimension changed from %s to %s, triggering full reindex",
                    stored_dimension,
                    current_dimension,
                )
                reindex_needed = True
            elif not stored_dimension:
                await self._store.set_metadata("embedding_dimension", current_dimension)

            # Check if Gemini task type configuration changed (only for Gemini)
            if provider_name == "gemini":
                task_type_version = (
                    "v2_query_document_split"  # Increment when task type logic changes
                )
                stored_version = await self._store.get_metadata(
                    "gemini_task_type_version"
                )

                if stored_version and stored_version != task_type_version:
                    _LOGGER.warning(
                        "Gemini task type configuration changed (%s -> %s), triggering full reindex",
                        stored_version,
                        task_type_version,
                    )
                    reindex_needed = True
                elif not stored_version:
                    await self._store.set_metadata(
                        "gemini_task_type_version", task_type_version
                    )
                    _LOGGER.info(
                        "Stored Gemini task type version: %s", task_type_version
                    )

            # 9. Perform full reindex if needed
            doc_count = await self._store.get_document_count()
            if reindex_needed:
                _LOGGER.info("Reindexing all entities due to configuration change...")
                # Clear old embeddings (dimension may have changed)
                await self._store.clear_collection()
                self._store.cache_prune(max_entries=0)  # Purge entire embedding cache
                _LOGGER.info("Cleared old embeddings and cache")
                await self._indexer.full_reindex()
                # Update metadata after successful reindex
                await self._store.set_metadata("embedding_provider", provider_name)
                await self._store.set_metadata("embedding_dimension", current_dimension)
                if provider_name == "gemini":
                    await self._store.set_metadata(
                        "gemini_task_type_version", "v2_query_document_split"
                    )
            elif doc_count == 0:
                _LOGGER.info("No indexed entities found, performing full reindex...")
                await self._indexer.full_reindex()
            else:
                _LOGGER.info("RAG system has %d indexed entities", doc_count)

            self._initialized = True
            _LOGGER.info("RAG system initialized successfully")

        except Exception as e:
            _LOGGER.exception("Failed to initialize RAG system: %s", e)
            raise

    def _ensure_initialized(self) -> None:
        """Ensure RAG is initialized before operations."""
        if not self._initialized:
            raise RuntimeError(
                "RAGManager not initialized. Call async_initialize() first."
            )

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
        self._ensure_initialized()

        try:
            # Extract intent from query using semantic similarity (cached embeddings)
            intent = await self._intent_detector.detect_intent(query)

            # Pre-filter: Skip RAG if query clearly not HA-related
            if not intent:
                # Check for basic HA keywords (English + Polish)
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
            # Priority: domain > device_class (they often conflict, e.g. media_player vs motion)
            # Area is always safe to combine
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
                # Check if entity still exists in Home Assistant
                if self.hass.states.get(entity_id):
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
            # Graceful degradation - return empty context
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
            # Truncate long chunks to save tokens
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

    async def capture_explicit_commands(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        session_id: str = "",
    ) -> int:
        """Capture explicit "remember this" commands from messages.

        Safety net for when the LLM doesn't call memory_store on explicit
        user commands. All other memory capture is handled by the LLM via
        memory_store tool and AI-powered flush before compaction.

        Args:
            messages: Conversation messages (role + content dicts).
            user_id: User who owns these memories.
            session_id: Session context.

        Returns:
            Number of new memories captured.
        """
        if not self._memory_manager:
            return 0

        try:
            return await self._memory_manager.capture_explicit_commands(
                messages=messages,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as e:
            _LOGGER.debug("Explicit memory capture failed: %s", e)
            return 0

    @property
    def memory_manager(self) -> Any:
        """Access the MemoryManager instance (for direct API use)."""
        return self._memory_manager

    @property
    def identity_manager(self) -> Any:
        """Access the IdentityManager instance (for direct API use)."""
        return self._identity_manager

    async def learn_from_conversation(
        self,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Learn semantic corrections from a conversation.

        Analyzes the conversation for patterns like:
        - "switch.lamp is actually a light"
        - "treat sensor.xyz as a temperature sensor"

        Args:
            user_message: The user's message.
            assistant_message: The assistant's response.
        """
        self._ensure_initialized()

        try:
            await self._learner.detect_and_persist(
                user_message=user_message,
                assistant_message=assistant_message,
            )
        except Exception as e:
            _LOGGER.warning("Failed to learn from conversation: %s", e)
            # Graceful degradation - don't fail the main flow

    async def index_session(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        *,
        force: bool = False,
    ) -> int:
        """Index a conversation session for RAG retrieval.

        Delegates to SessionIndexer which handles chunking, delta detection,
        embedding, and storage. Called after each assistant response.

        Args:
            session_id: Session identifier.
            messages: List of message dicts with 'role' and 'content' keys.
            force: If True, skip delta check and always reindex.

        Returns:
            Number of chunks indexed (0 if skipped due to delta threshold).
        """
        self._ensure_initialized()

        if not self._session_indexer:
            _LOGGER.debug("Session indexer not available, skipping")
            return 0

        try:
            return await self._session_indexer.index_session(
                session_id=session_id,
                messages=messages,
                force=force,
            )
        except Exception as e:
            _LOGGER.warning("Session indexing failed for %s: %s", session_id, e)
            return 0

    async def remove_session_index(self, session_id: str) -> None:
        """Remove indexed session data when a session is deleted.

        Args:
            session_id: Session to remove from the index.
        """
        self._ensure_initialized()

        if self._session_indexer:
            try:
                await self._session_indexer.remove_session(session_id)
            except Exception as e:
                _LOGGER.warning(
                    "Failed to remove session index for %s: %s", session_id, e
                )

    async def reindex_entity(self, entity_id: str) -> None:
        """Reindex a single entity.

        Args:
            entity_id: The entity ID to reindex.
        """
        self._ensure_initialized()
        await self._indexer.index_entity(entity_id)

    async def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from the index.

        Args:
            entity_id: The entity ID to remove.
        """
        self._ensure_initialized()
        await self._indexer.remove_entity(entity_id)

    async def full_reindex(self) -> None:
        """Perform a full reindex of all entities."""
        self._ensure_initialized()
        await self._indexer.full_reindex()

    async def get_stats(self) -> dict[str, Any]:
        """Get RAG system statistics.

        Returns:
            Dictionary with stats like document count, learned categories, etc.
        """
        self._ensure_initialized()

        stats: dict[str, Any] = {
            "indexed_entities": await self._store.get_document_count(),
            "embedding_provider": self._embedding_provider.provider_name,
            "embedding_dimension": self._embedding_provider.dimension,
            "learned_categories": len(self._learner.categories) if self._learner else 0,
        }

        # Add embedding cache stats if available (duck-type check for CachedEmbeddingProvider)
        if hasattr(self._embedding_provider, "get_cache_stats"):
            stats["embedding_cache"] = self._embedding_provider.get_cache_stats()
            stats["embedding_cache_db"] = await self._store.get_cache_stats()

        # Add session indexing stats
        if self._session_indexer:
            try:
                stats["session_index"] = await self._session_indexer.get_stats()
            except Exception:
                stats["session_index"] = {"error": "unavailable"}

        # Add long-term memory stats
        if self._memory_manager:
            try:
                stats["long_term_memory"] = await self._memory_manager.get_stats()
            except Exception:
                stats["long_term_memory"] = {"error": "unavailable"}

        return stats

    async def async_shutdown(self) -> None:
        """Shutdown all RAG components gracefully."""
        _LOGGER.info("Shutting down RAG system...")

        try:
            if self._state_handler:
                await self._state_handler.async_stop()
                self._state_handler = None

            if self._event_handlers:
                await self._event_handlers.async_stop()
                self._event_handlers = None

            if self._learner:
                await self._learner.async_save()
                self._learner = None

            if self._store:
                await self._store.async_shutdown()
                self._store = None

            self._indexer = None
            self._query_engine = None
            self._session_indexer = None
            self._memory_manager = None
            self._identity_manager = None
            self._embedding_provider = None
            self._initialized = False

            _LOGGER.info("RAG system shut down successfully")

        except Exception as e:
            _LOGGER.error("Error during RAG shutdown: %s", e)
            raise

    @property
    def is_initialized(self) -> bool:
        """Check if RAG system is initialized."""
        return self._initialized
