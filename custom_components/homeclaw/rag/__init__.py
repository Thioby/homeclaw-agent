"""RAG (Retrieval-Augmented Generation) system for Homeclaw.

This module provides semantic search capabilities for Home Assistant entities,
learning from conversations to improve entity categorization over time.

Uses SQLite for vector storage - no external dependencies required.

Architecture:
    RAGManager (facade) delegates to:
    - RAGLifecycleManager: initialization, shutdown, reindexing
    - RAGContextRetriever: entity/session/memory context retrieval
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Re-export for external use
__all__ = [
    "RAGManager",
]


@dataclass
class RAGManager:
    """Facade for the RAG system.

    Orchestrates all RAG components via two internal managers:
    - RAGLifecycleManager: handles init/shutdown/reindex/metadata
    - RAGContextRetriever: handles context retrieval (search + memory)

    Public API is unchanged — all external callers go through this class.

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
    _lifecycle: Any | None = field(default=None, repr=False)
    _retriever: Any | None = field(default=None, repr=False)

    def _get_persist_directory(self) -> str:
        """Get the SQLite persist directory path."""
        config_dir = self.hass.config.path("homeclaw", "rag_db")
        return config_dir

    # ------------------------------------------------------------------
    # Lifecycle (delegate to RAGLifecycleManager)
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Initialize all RAG components."""
        if self._lifecycle and self._lifecycle.is_initialized:
            _LOGGER.debug("RAGManager already initialized")
            return

        from .lifecycle_manager import RAGLifecycleManager

        self._lifecycle = RAGLifecycleManager(
            hass=self.hass,
            config=self.config,
            config_entry=self.config_entry,
        )
        await self._lifecycle.async_initialize()

        # Wire up context retriever with the initialized components
        from .context_retriever import RAGContextRetriever

        self._retriever = RAGContextRetriever(
            hass=self.hass,
            query_engine=self._lifecycle.query_engine,
            intent_detector=self._lifecycle.intent_detector,
            embedding_provider=self._lifecycle.embedding_provider,
            store=self._lifecycle.store,
            indexer=self._lifecycle.indexer,
            session_indexer=self._lifecycle.session_indexer,
            memory_manager=self._lifecycle.memory_manager,
        )

    def _ensure_initialized(self) -> None:
        """Ensure RAG is initialized before operations."""
        if not self._lifecycle or not self._lifecycle.is_initialized:
            raise RuntimeError(
                "RAGManager not initialized. Call async_initialize() first."
            )

    async def async_shutdown(self) -> None:
        """Shutdown all RAG components gracefully."""
        if self._lifecycle:
            await self._lifecycle.async_shutdown()
        self._retriever = None

    @property
    def is_initialized(self) -> bool:
        """Check if RAG system is initialized."""
        return self._lifecycle is not None and self._lifecycle.is_initialized

    # ------------------------------------------------------------------
    # Context retrieval (delegate to RAGContextRetriever)
    # ------------------------------------------------------------------

    async def get_relevant_context(
        self,
        query: str,
        top_k: int = 10,
        user_id: str | None = None,
    ) -> str:
        """Get relevant entity context for a user query.

        Args:
            query: The user's query text.
            top_k: Maximum number of entities to include.
            user_id: Optional user ID for memory recall.

        Returns:
            Compressed context string for the LLM, or empty string if no results.
        """
        self._ensure_initialized()
        return await self._retriever.get_relevant_context(query, top_k, user_id)

    # ------------------------------------------------------------------
    # Session indexing (delegate to lifecycle components)
    # ------------------------------------------------------------------

    async def index_session(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        *,
        force: bool = False,
    ) -> int:
        """Index a conversation session for RAG retrieval.

        Args:
            session_id: Session identifier.
            messages: List of message dicts with 'role' and 'content' keys.
            force: If True, skip delta check and always reindex.

        Returns:
            Number of chunks indexed (0 if skipped due to delta threshold).
        """
        self._ensure_initialized()

        session_indexer = self._lifecycle.session_indexer
        if not session_indexer:
            _LOGGER.debug("Session indexer not available, skipping")
            return 0

        try:
            return await session_indexer.index_session(
                session_id=session_id,
                messages=messages,
                force=force,
            )
        except Exception as e:
            _LOGGER.warning("Session indexing failed for %s: %s", session_id, e)
            return 0

    async def sanitize_and_index_session(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        provider: Any,
        model: str | None = None,
    ) -> int:
        """Sanitize a session via LLM and then index the cleaned version.

        Uses an LLM to strip ephemeral state data (sensor readings, entity
        states) from the conversation, keeping only durable context
        (preferences, decisions, actions). The cleaned messages are then
        indexed into the RAG session store.

        Args:
            session_id: Session identifier.
            messages: Raw message dicts with 'role' and 'content' keys.
            provider: AI provider instance for sanitization LLM call.
            model: Optional model override for the LLM call.

        Returns:
            Number of chunks indexed (0 if sanitization or indexing failed).
        """
        self._ensure_initialized()

        session_indexer = self._lifecycle.session_indexer
        if not session_indexer:
            _LOGGER.debug("Session indexer not available, skipping sanitization")
            return 0

        try:
            from .session_sanitizer import sanitize_session_messages

            sanitized = await sanitize_session_messages(messages, provider, model)

            if not sanitized:
                _LOGGER.debug("Sanitization returned empty result for %s", session_id)
                return 0

            return await session_indexer.index_session(
                session_id=session_id,
                messages=sanitized,
                force=True,
            )
        except Exception as e:
            _LOGGER.warning(
                "Sanitize-and-index failed for session %s: %s", session_id, e
            )
            return 0

    async def remove_session_index(self, session_id: str) -> None:
        """Remove indexed session data when a session is deleted.

        Args:
            session_id: Session to remove from the index.
        """
        self._ensure_initialized()

        session_indexer = self._lifecycle.session_indexer
        if session_indexer:
            try:
                await session_indexer.remove_session(session_id)
            except Exception as e:
                _LOGGER.warning(
                    "Failed to remove session index for %s: %s", session_id, e
                )

    # ------------------------------------------------------------------
    # Learning (delegate to semantic learner)
    # ------------------------------------------------------------------

    async def learn_from_conversation(
        self,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Learn semantic corrections from a conversation.

        Args:
            user_message: The user's message.
            assistant_message: The assistant's response.
        """
        self._ensure_initialized()

        try:
            await self._lifecycle.learner.detect_and_persist(
                user_message=user_message,
                assistant_message=assistant_message,
            )
        except Exception as e:
            _LOGGER.warning("Failed to learn from conversation: %s", e)

    # ------------------------------------------------------------------
    # Memory capture (delegate to memory manager)
    # ------------------------------------------------------------------

    async def capture_explicit_commands(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        session_id: str = "",
    ) -> int:
        """Capture explicit "remember this" commands from messages.

        Args:
            messages: Conversation messages (role + content dicts).
            user_id: User who owns these memories.
            session_id: Session context.

        Returns:
            Number of new memories captured.
        """
        memory_mgr = self._lifecycle.memory_manager if self._lifecycle else None
        if not memory_mgr:
            return 0

        try:
            return await memory_mgr.capture_explicit_commands(
                messages=messages,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as e:
            _LOGGER.debug("Explicit memory capture failed: %s", e)
            return 0

    # ------------------------------------------------------------------
    # Entity indexing (delegate to entity indexer)
    # ------------------------------------------------------------------

    async def reindex_entity(self, entity_id: str) -> None:
        """Reindex a single entity.

        Args:
            entity_id: The entity ID to reindex.
        """
        self._ensure_initialized()
        await self._lifecycle.indexer.index_entity(entity_id)

    async def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from the index.

        Args:
            entity_id: The entity ID to remove.
        """
        self._ensure_initialized()
        await self._lifecycle.indexer.remove_entity(entity_id)

    async def full_reindex(self) -> None:
        """Perform a full reindex of all entities."""
        self._ensure_initialized()
        await self._lifecycle.indexer.full_reindex()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_stats(self) -> dict[str, Any]:
        """Get RAG system statistics.

        Returns:
            Dictionary with stats like document count, learned categories, etc.
        """
        self._ensure_initialized()

        lc = self._lifecycle
        stats: dict[str, Any] = {
            "indexed_entities": await lc.store.get_document_count(),
            "embedding_provider": lc.embedding_provider.provider_name,
            "embedding_dimension": lc.embedding_provider.dimension,
            "learned_categories": len(lc.learner.categories) if lc.learner else 0,
        }

        # Embedding cache stats
        if hasattr(lc.embedding_provider, "get_cache_stats"):
            stats["embedding_cache"] = lc.embedding_provider.get_cache_stats()
            stats["embedding_cache_db"] = await lc.store.get_cache_stats()

        # Session indexing stats
        if lc.session_indexer:
            try:
                stats["session_index"] = await lc.session_indexer.get_stats()
            except Exception:
                stats["session_index"] = {"error": "unavailable"}

        # Long-term memory stats
        if lc.memory_manager:
            try:
                stats["long_term_memory"] = await lc.memory_manager.get_stats()
            except Exception:
                stats["long_term_memory"] = {"error": "unavailable"}

        return stats

    # ------------------------------------------------------------------
    # Properties (expose sub-managers for external access)
    # ------------------------------------------------------------------

    @property
    def memory_manager(self) -> Any:
        """Access the MemoryManager instance (for direct API use)."""
        return self._lifecycle.memory_manager if self._lifecycle else None

    @property
    def identity_manager(self) -> Any:
        """Access the IdentityManager instance (for direct API use)."""
        return self._lifecycle.identity_manager if self._lifecycle else None

    # Backward compat: some callers access _memory_manager directly
    @property
    def _memory_manager(self) -> Any:
        """Backward-compatible access to memory manager."""
        return self._lifecycle.memory_manager if self._lifecycle else None

    @property
    def _store(self) -> Any:
        """Backward-compatible access to store."""
        return self._lifecycle.store if self._lifecycle else None

    @property
    def _embedding_provider(self) -> Any:
        """Backward-compatible access to embedding provider."""
        return self._lifecycle.embedding_provider if self._lifecycle else None

    @property
    def _indexer(self) -> Any:
        """Backward-compatible access to indexer."""
        return self._lifecycle.indexer if self._lifecycle else None

    @property
    def _query_engine(self) -> Any:
        """Backward-compatible access to query engine."""
        return self._lifecycle.query_engine if self._lifecycle else None

    @property
    def _intent_detector(self) -> Any:
        """Backward-compatible access to intent detector."""
        return self._lifecycle.intent_detector if self._lifecycle else None

    @property
    def _learner(self) -> Any:
        """Backward-compatible access to learner."""
        return self._lifecycle.learner if self._lifecycle else None

    @property
    def _session_indexer(self) -> Any:
        """Backward-compatible access to session indexer."""
        return self._lifecycle.session_indexer if self._lifecycle else None

    @property
    def _identity_manager(self) -> Any:
        """Backward-compatible access to identity manager."""
        return self._lifecycle.identity_manager if self._lifecycle else None

    @property
    def _initialized(self) -> bool:
        """Backward-compatible access to initialized flag."""
        return self._lifecycle is not None and self._lifecycle.is_initialized

    @_initialized.setter
    def _initialized(self, value: bool) -> None:
        """Backward-compatible setter (used in tests)."""
        if self._lifecycle:
            self._lifecycle._initialized = value
