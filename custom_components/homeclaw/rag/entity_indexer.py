"""Entity indexer for RAG system.

This module converts Home Assistant entities into searchable documents
for the vector database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import EntityRegistry

from .sqlite_store import SqliteStore
from .embeddings import EmbeddingProvider

_LOGGER = logging.getLogger(__name__)

# Batch size for embedding generation to avoid rate limits
EMBEDDING_BATCH_SIZE = 50


@dataclass
class EntityDocument:
    """Document representation of a Home Assistant entity."""

    id: str  # entity_id
    text: str  # searchable text
    metadata: dict[str, Any]  # domain, area, state, learned_category, etc.


@dataclass
class EntityIndexer:
    """Indexes Home Assistant entities into the vector database.

    Converts entities to searchable documents with embeddings.
    """

    hass: HomeAssistant
    store: SqliteStore
    embedding_provider: EmbeddingProvider
    _learned_categories: dict[str, str] = field(default_factory=dict)

    def set_learned_categories(self, categories: dict[str, str]) -> None:
        """Set learned categories from semantic learner.

        Args:
            categories: Mapping of entity_id to learned category.
        """
        self._learned_categories = categories

    def _get_entity_registry(self) -> EntityRegistry:
        """Get the entity registry from Home Assistant."""
        from homeassistant.helpers import entity_registry as er

        return er.async_get(self.hass)

    def _build_document_text(
        self,
        entity_id: str,
        friendly_name: str | None,
        domain: str,
        device_class: str | None,
        area_name: str | None,
        state: str | None,
    ) -> str:
        """Build searchable text from entity data.

        Creates a rich text representation including:
        - Friendly name
        - Domain
        - Device class
        - Area/room
        - Learned category (if any)

        Args:
            entity_id: The entity ID.
            friendly_name: Human-readable name.
            domain: Entity domain (light, switch, sensor, etc.).
            device_class: Device classification (if any).
            area_name: Area/room name (if assigned).
            state: Current state value.

        Returns:
            Searchable text string.
        """
        parts = []

        # Friendly name is most important for search
        if friendly_name:
            parts.append(friendly_name)

        # Add domain context
        parts.append(domain)

        # Add device class if available
        if device_class:
            parts.append(device_class)

        # Add area/room context
        if area_name:
            parts.append(f"in {area_name}")
            parts.append(area_name)  # Also add standalone for matching

        # Add state for actionable entities
        if state and domain in ("light", "switch", "cover", "lock", "fan", "climate"):
            # Add both raw state and human-readable version
            parts.append(state)

            # Add semantic state descriptions for better matching
            if domain == "light":
                if state == "on":
                    parts.append("turned on")
                    parts.append("active")
                    parts.append("lit")
                elif state == "off":
                    parts.append("turned off")
                    parts.append("inactive")
                    parts.append("dark")
            elif domain in ("switch", "fan"):
                if state == "on":
                    parts.append("turned on")
                    parts.append("running")
                    parts.append("active")
                elif state == "off":
                    parts.append("turned off")
                    parts.append("stopped")
                    parts.append("inactive")
            elif domain == "cover":
                if state == "open":
                    parts.append("opened")
                    parts.append("up")
                elif state == "closed":
                    parts.append("closed")
                    parts.append("down")
                elif state == "opening":
                    parts.append("opening")
                elif state == "closing":
                    parts.append("closing")
            elif domain == "lock":
                if state == "locked":
                    parts.append("secured")
                    parts.append("locked")
                elif state == "unlocked":
                    parts.append("unsecured")
                    parts.append("open")
            elif domain == "climate":
                # Add temperature/hvac mode if available in state
                parts.append(f"mode {state}")

        # Add learned category if available
        learned_cat = self._learned_categories.get(entity_id)
        if learned_cat:
            parts.append(f"category:{learned_cat}")
            parts.append(learned_cat)

        # Add entity_id for exact matching
        parts.append(entity_id)

        return " ".join(parts)

    def _build_metadata(
        self,
        entity_id: str,
        domain: str,
        device_class: str | None,
        area_id: str | None,
        area_name: str | None,
        state: str | None,
        friendly_name: str | None,
    ) -> dict[str, Any]:
        """Build metadata dictionary for the document.

        Args:
            entity_id: The entity ID.
            domain: Entity domain.
            device_class: Device classification.
            area_id: Area registry ID.
            area_name: Area name.
            state: Current state.
            friendly_name: Human-readable name.

        Returns:
            Metadata dictionary.
        """
        metadata = {
            "entity_id": entity_id,
            "domain": domain,
        }

        if device_class:
            metadata["device_class"] = device_class

        if area_id:
            metadata["area_id"] = area_id

        if area_name:
            metadata["area_name"] = area_name

        if state:
            metadata["state"] = state

        if friendly_name:
            metadata["friendly_name"] = friendly_name

        # Add learned category
        learned_cat = self._learned_categories.get(entity_id)
        if learned_cat:
            metadata["learned_category"] = learned_cat

        return metadata

    async def _get_entity_data(self, entity_id: str) -> EntityDocument | None:
        """Get entity data and convert to document.

        Args:
            entity_id: The entity ID to process.

        Returns:
            EntityDocument or None if entity not found.
        """
        registry = self._get_entity_registry()
        entry = registry.async_get(entity_id)

        if not entry:
            _LOGGER.debug("Entity not in registry: %s", entity_id)
            return None

        # Get state for additional context
        state = self.hass.states.get(entity_id)
        state_value = state.state if state else None
        friendly_name = (
            state.attributes.get("friendly_name") if state else None
        ) or entry.name

        # Get area info
        area_id = entry.area_id
        area_name = None
        if area_id:
            from homeassistant.helpers import area_registry as ar

            area_registry = ar.async_get(self.hass)
            area = area_registry.async_get_area(area_id)
            if area:
                area_name = area.name

        # Get device class
        device_class = entry.device_class or entry.original_device_class

        # Parse domain from entity_id
        domain = entity_id.split(".")[0]

        # Build document
        text = self._build_document_text(
            entity_id=entity_id,
            friendly_name=friendly_name,
            domain=domain,
            device_class=device_class,
            area_name=area_name,
            state=state_value,
        )

        metadata = self._build_metadata(
            entity_id=entity_id,
            domain=domain,
            device_class=device_class,
            area_id=area_id,
            area_name=area_name,
            state=state_value,
            friendly_name=friendly_name,
        )

        return EntityDocument(id=entity_id, text=text, metadata=metadata)

    async def index_entity(self, entity_id: str) -> None:
        """Index or reindex a single entity.

        Args:
            entity_id: The entity ID to index.
        """
        doc = await self._get_entity_data(entity_id)
        if not doc:
            _LOGGER.debug("Skipping non-existent entity: %s", entity_id)
            return

        try:
            # Generate embedding
            embeddings = await self.embedding_provider.get_embeddings([doc.text])
            if not embeddings:
                _LOGGER.warning("Failed to generate embedding for %s", entity_id)
                return

            # Upsert to store
            await self.store.upsert_documents(
                ids=[doc.id],
                texts=[doc.text],
                embeddings=embeddings,
                metadatas=[doc.metadata],
            )
            _LOGGER.debug("Indexed entity: %s", entity_id)

        except Exception as e:
            _LOGGER.error("Failed to index entity %s: %s", entity_id, e)

    async def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from the index.

        Args:
            entity_id: The entity ID to remove.
        """
        try:
            await self.store.delete_documents([entity_id])
            _LOGGER.debug("Removed entity from index: %s", entity_id)
        except Exception as e:
            _LOGGER.error("Failed to remove entity %s: %s", entity_id, e)

    async def full_reindex(self) -> None:
        """Perform a full reindex of all entities.

        Clears the existing index and reindexes all entities
        from the Home Assistant entity registry.
        """
        _LOGGER.info("Starting full entity reindex...")

        try:
            # Clear existing documents
            await self.store.clear_collection()

            # Get all entities from registry
            registry = self._get_entity_registry()
            entities = list(registry.entities.values())

            _LOGGER.info("Indexing %d entities...", len(entities))

            # Process in batches to avoid rate limits
            all_docs: list[EntityDocument] = []

            for entry in entities:
                doc = await self._get_entity_data(entry.entity_id)
                if doc:
                    all_docs.append(doc)

            # Generate embeddings in batches
            for i in range(0, len(all_docs), EMBEDDING_BATCH_SIZE):
                batch = all_docs[i : i + EMBEDDING_BATCH_SIZE]
                texts = [doc.text for doc in batch]

                try:
                    embeddings = await self.embedding_provider.get_embeddings(texts)

                    await self.store.add_documents(
                        ids=[doc.id for doc in batch],
                        texts=texts,
                        embeddings=embeddings,
                        metadatas=[doc.metadata for doc in batch],
                    )

                    _LOGGER.debug(
                        "Indexed batch %d-%d of %d",
                        i + 1,
                        min(i + EMBEDDING_BATCH_SIZE, len(all_docs)),
                        len(all_docs),
                    )

                except Exception as e:
                    _LOGGER.error("Failed to index batch: %s", e)
                    # Continue with next batch

            final_count = await self.store.get_document_count()
            _LOGGER.info("Full reindex complete. Indexed %d entities.", final_count)

        except Exception as e:
            _LOGGER.exception("Full reindex failed: %s", e)
            raise

    async def index_entities_batch(self, entity_ids: list[str]) -> None:
        """Index multiple entities in a batch.

        Args:
            entity_ids: List of entity IDs to index.
        """
        if not entity_ids:
            return

        docs: list[EntityDocument] = []
        for entity_id in entity_ids:
            doc = await self._get_entity_data(entity_id)
            if doc:
                docs.append(doc)

        if not docs:
            return

        try:
            texts = [doc.text for doc in docs]
            embeddings = await self.embedding_provider.get_embeddings(texts)

            await self.store.upsert_documents(
                ids=[doc.id for doc in docs],
                texts=texts,
                embeddings=embeddings,
                metadatas=[doc.metadata for doc in docs],
            )
            _LOGGER.debug("Batch indexed %d entities", len(docs))

        except Exception as e:
            _LOGGER.error("Failed to batch index entities: %s", e)
