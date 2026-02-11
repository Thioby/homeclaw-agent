"""RAG lifecycle management.

Handles initialization, shutdown, reindexing, and metadata tracking
for the RAG subsystem. Separated from the main RAGManager facade
to isolate complex setup/teardown logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class RAGLifecycleManager:
    """Manages RAG component initialization, shutdown, and reindexing.

    This class owns all the subsystem instances created during initialization
    and exposes them as attributes so the RAGManager facade can use them.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the lifecycle manager (no components created yet).

        Args:
            hass: Home Assistant instance.
            config: Integration configuration dict.
            config_entry: Optional HA config entry for provider credentials.
        """
        self.hass = hass
        self.config = config
        self.config_entry = config_entry

        # Component references — populated by async_initialize
        self.store: Any | None = None
        self.embedding_provider: Any | None = None
        self.indexer: Any | None = None
        self.query_engine: Any | None = None
        self.intent_detector: Any | None = None
        self.learner: Any | None = None
        self.session_indexer: Any | None = None
        self.event_handlers: Any | None = None
        self.state_handler: Any | None = None
        self.memory_manager: Any | None = None
        self.identity_manager: Any | None = None

        self._initialized: bool = False

    @property
    def is_initialized(self) -> bool:
        """Check if the RAG system has been initialized."""
        return self._initialized

    def _get_persist_directory(self) -> str:
        """Get the SQLite persist directory path."""
        return self.hass.config.path("homeclaw", "rag_db")

    async def async_initialize(self) -> None:
        """Initialize all RAG components.

        This initializes:
        1. SQLite vector storage
        2. Embedding provider
        3. Entity indexer
        4. Query engine
        5. Intent detector
        6. Session indexer + memory/identity managers
        7. Semantic learner
        8. Event handlers
        9. Metadata checks / auto-reindex
        """
        if self._initialized:
            _LOGGER.debug("RAGLifecycleManager already initialized")
            return

        try:
            _LOGGER.info("Initializing RAG system...")

            # 1. SQLite storage
            from .sqlite_store import SqliteStore

            persist_dir = self._get_persist_directory()
            self.store = SqliteStore(persist_directory=persist_dir)
            await self.store.async_initialize()

            # 2. Embedding provider (with caching wrapper)
            from .embeddings import CachedEmbeddingProvider, create_embedding_provider

            raw_provider = create_embedding_provider(
                self.hass, self.config, self.config_entry
            )
            self.embedding_provider = CachedEmbeddingProvider(
                inner=raw_provider,
                store=self.store,
            )
            _LOGGER.info(
                "RAG using embedding provider: %s (with cache)",
                self.embedding_provider.provider_name,
            )

            # 3. Entity indexer
            from .entity_indexer import EntityIndexer

            self.indexer = EntityIndexer(
                hass=self.hass,
                store=self.store,
                embedding_provider=self.embedding_provider,
            )

            # 4. Query engine
            from .query_engine import QueryEngine

            self.query_engine = QueryEngine(
                store=self.store,
                embedding_provider=self.embedding_provider,
            )

            # 5. Intent detector
            from .intent_detector import IntentDetector

            self.intent_detector = IntentDetector(
                embedding_provider=self.embedding_provider,
            )
            await self.intent_detector.async_initialize()

            # 6. Session indexer
            from .session_indexer import SessionIndexer

            self.session_indexer = SessionIndexer(
                store=self.store,
                embedding_provider=self.embedding_provider,
            )
            _LOGGER.debug("Session indexer initialized")

            # 6b. Long-term memory manager
            try:
                from ..memory.manager import MemoryManager

                self.memory_manager = MemoryManager(
                    store=self.store,
                    embedding_provider=self.embedding_provider,
                )
                await self.memory_manager.async_initialize()
                _LOGGER.info("Long-term memory manager initialized")
            except Exception as mem_err:
                _LOGGER.warning("Long-term memory init failed (non-fatal): %s", mem_err)
                self.memory_manager = None

            # 6c. Identity manager
            try:
                from ..memory.identity_manager import IdentityManager

                self.identity_manager = IdentityManager(store=self.store)
                await self.identity_manager.async_initialize()
                _LOGGER.info("Identity manager initialized")
            except Exception as id_err:
                _LOGGER.warning("Identity manager init failed (non-fatal): %s", id_err)
                self.identity_manager = None

            # 7. Semantic learner
            from .semantic_learner import SemanticLearner

            learner_storage_path = self.hass.config.path(
                "homeclaw", "learned_categories.json"
            )
            self.learner = SemanticLearner(
                hass=self.hass,
                indexer=self.indexer,
                storage_path=learner_storage_path,
            )
            await self.learner.async_load()

            # 8. Event handlers
            from .event_handlers import EntityRegistryEventHandler, StateChangeHandler

            self.event_handlers = EntityRegistryEventHandler(
                hass=self.hass,
                indexer=self.indexer,
            )
            await self.event_handlers.async_start()

            self.state_handler = StateChangeHandler(
                hass=self.hass,
                indexer=self.indexer,
            )
            await self.state_handler.async_start()

            # 9. Metadata checks / auto-reindex
            await self._check_and_reindex()

            self._initialized = True
            _LOGGER.info("RAG system initialized successfully")

        except Exception as e:
            _LOGGER.exception("Failed to initialize RAG system: %s", e)
            raise

    async def _check_and_reindex(self) -> None:
        """Check metadata (provider, dimension, task type) and reindex if needed."""
        provider_name = self.embedding_provider.provider_name
        stored_provider = await self.store.get_metadata("embedding_provider")

        reindex_needed = False

        if stored_provider and stored_provider != provider_name:
            _LOGGER.warning(
                "Embedding provider changed from %s to %s, triggering full reindex",
                stored_provider,
                provider_name,
            )
            reindex_needed = True
        elif not stored_provider:
            await self.store.set_metadata("embedding_provider", provider_name)
            _LOGGER.info("Stored embedding provider: %s", provider_name)

        # Dimension check
        stored_dimension = await self.store.get_metadata("embedding_dimension")
        current_dimension = str(self.embedding_provider.dimension)
        if stored_dimension and stored_dimension != current_dimension:
            _LOGGER.warning(
                "Embedding dimension changed from %s to %s, triggering full reindex",
                stored_dimension,
                current_dimension,
            )
            reindex_needed = True
        elif not stored_dimension:
            await self.store.set_metadata("embedding_dimension", current_dimension)

        # Gemini task type check
        if provider_name == "gemini":
            task_type_version = "v2_query_document_split"
            stored_version = await self.store.get_metadata("gemini_task_type_version")

            if stored_version and stored_version != task_type_version:
                _LOGGER.warning(
                    "Gemini task type configuration changed (%s -> %s), triggering full reindex",
                    stored_version,
                    task_type_version,
                )
                reindex_needed = True
            elif not stored_version:
                await self.store.set_metadata(
                    "gemini_task_type_version", task_type_version
                )
                _LOGGER.info("Stored Gemini task type version: %s", task_type_version)

        # Perform reindex if needed
        doc_count = await self.store.get_document_count()
        if reindex_needed:
            _LOGGER.info("Reindexing all entities due to configuration change...")
            await self.store.clear_collection()
            self.store.cache_prune(max_entries=0)
            _LOGGER.info("Cleared old embeddings and cache")
            await self.indexer.full_reindex()
            await self.store.set_metadata("embedding_provider", provider_name)
            await self.store.set_metadata("embedding_dimension", current_dimension)
            if provider_name == "gemini":
                await self.store.set_metadata(
                    "gemini_task_type_version", "v2_query_document_split"
                )
        elif doc_count == 0:
            _LOGGER.info("No indexed entities found, performing full reindex...")
            await self.indexer.full_reindex()
        else:
            _LOGGER.info("RAG system has %d indexed entities", doc_count)

    async def async_shutdown(self) -> None:
        """Shutdown all RAG components gracefully."""
        _LOGGER.info("Shutting down RAG system...")

        try:
            if self.state_handler:
                await self.state_handler.async_stop()
                self.state_handler = None

            if self.event_handlers:
                await self.event_handlers.async_stop()
                self.event_handlers = None

            if self.learner:
                await self.learner.async_save()
                self.learner = None

            if self.store:
                await self.store.async_shutdown()
                self.store = None

            self.indexer = None
            self.query_engine = None
            self.session_indexer = None
            self.memory_manager = None
            self.identity_manager = None
            self.embedding_provider = None
            self.intent_detector = None
            self._initialized = False

            _LOGGER.info("RAG system shut down successfully")

        except Exception as e:
            _LOGGER.error("Error during RAG shutdown: %s", e)
            raise
