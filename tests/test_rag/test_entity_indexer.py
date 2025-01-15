"""Tests for entity indexer."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Note: homeassistant mocks are set up in conftest.py

from custom_components.homeclaw.rag.entity_indexer import (
    EntityDocument,
    EntityIndexer,
)


@dataclass
class MockEntityEntry:
    """Mock entity registry entry."""

    entity_id: str
    name: str | None = None
    area_id: str | None = None
    device_class: str | None = None
    original_device_class: str | None = None


@dataclass
class MockState:
    """Mock Home Assistant state."""

    entity_id: str
    state: str
    attributes: dict


@dataclass
class MockArea:
    """Mock area registry entry."""

    name: str
    id: str


class TestEntityIndexer:
    """Tests for EntityIndexer class."""

    @pytest.fixture
    def mock_store(self):
        """Return a mock ChromaStore."""
        store = MagicMock()
        store.add_documents = AsyncMock()
        store.upsert_documents = AsyncMock()
        store.delete_documents = AsyncMock()
        store.clear_collection = AsyncMock()
        store.get_document_count = AsyncMock(return_value=0)
        return store

    @pytest.fixture
    def mock_embedding_provider(self):
        """Return a mock embedding provider."""
        provider = MagicMock()
        provider.get_embeddings = AsyncMock(
            side_effect=lambda texts: [[0.1] * 768 for _ in texts]
        )
        return provider

    @pytest.fixture
    def indexer(self, hass, mock_store, mock_embedding_provider):
        """Return an EntityIndexer instance."""
        return EntityIndexer(
            hass=hass,
            store=mock_store,
            embedding_provider=mock_embedding_provider,
        )

    def test_build_document_text(self, indexer):
        """Test building searchable text from entity data."""
        text = indexer._build_document_text(
            entity_id="light.bedroom_lamp",
            friendly_name="Bedroom Lamp",
            domain="light",
            device_class="light",
            area_name="Bedroom",
            state="on",
        )

        assert "Bedroom Lamp" in text
        assert "light" in text
        assert "Bedroom" in text
        assert "light.bedroom_lamp" in text

    def test_build_document_text_with_learned_category(self, indexer):
        """Test that learned categories are included in text."""
        indexer.set_learned_categories({"switch.lamp": "light"})

        text = indexer._build_document_text(
            entity_id="switch.lamp",
            friendly_name="Lamp Switch",
            domain="switch",
            device_class=None,
            area_name="Living Room",
            state="on",
        )

        assert "light" in text
        assert "category:light" in text

    def test_build_metadata(self, indexer):
        """Test building metadata dictionary."""
        metadata = indexer._build_metadata(
            entity_id="sensor.temperature",
            domain="sensor",
            device_class="temperature",
            area_id="bedroom",
            area_name="Bedroom",
            state="22.5",
            friendly_name="Bedroom Temperature",
        )

        assert metadata["entity_id"] == "sensor.temperature"
        assert metadata["domain"] == "sensor"
        assert metadata["device_class"] == "temperature"
        assert metadata["area_id"] == "bedroom"
        assert metadata["area_name"] == "Bedroom"
        assert metadata["state"] == "22.5"
        assert metadata["friendly_name"] == "Bedroom Temperature"

    def test_build_metadata_with_learned_category(self, indexer):
        """Test that learned categories are included in metadata."""
        indexer.set_learned_categories({"switch.lamp": "light"})

        metadata = indexer._build_metadata(
            entity_id="switch.lamp",
            domain="switch",
            device_class=None,
            area_id=None,
            area_name=None,
            state="on",
            friendly_name="Lamp",
        )

        assert metadata["learned_category"] == "light"

    @pytest.mark.asyncio
    async def test_index_entity(self, indexer, mock_store, mock_embedding_provider):
        """Test indexing a single entity."""
        # Setup mocks
        mock_entry = MockEntityEntry(
            entity_id="light.test",
            name="Test Light",
            area_id="bedroom",
            device_class="light",
        )
        mock_state = MockState(
            entity_id="light.test",
            state="on",
            attributes={"friendly_name": "Test Light"},
        )
        mock_area = MockArea(name="Bedroom", id="bedroom")

        mock_registry = MagicMock()
        mock_registry.async_get = lambda eid: mock_entry

        mock_area_registry = MagicMock()
        mock_area_registry.async_get_area = lambda aid: mock_area

        # Use a lambda to return the mock state directly
        with patch("homeassistant.core.StateMachine.get", return_value=mock_state):
            # Patch the _get_entity_registry method directly on the indexer
            indexer._get_entity_registry = lambda: mock_registry

            # Patch at the module level for area_registry
            ar_module = sys.modules["homeassistant.helpers.area_registry"]
            original_ar_async_get = ar_module.async_get
            ar_module.async_get = lambda hass: mock_area_registry

            try:
                await indexer.index_entity("light.test")
            finally:
                ar_module.async_get = original_ar_async_get

        # Verify embedding was generated and stored
        mock_embedding_provider.get_embeddings.assert_called_once()
        mock_store.upsert_documents.assert_called_once()

        # Verify the stored data
        call_args = mock_store.upsert_documents.call_args
        assert call_args[1]["ids"] == ["light.test"]
        assert "Test Light" in call_args[1]["texts"][0]

    @pytest.mark.asyncio
    async def test_index_nonexistent_entity(self, indexer, mock_store):
        """Test indexing an entity that doesn't exist."""
        mock_registry = MagicMock()
        mock_registry.async_get = lambda eid: None

        # No state for nonexistent entity
        with patch("homeassistant.core.StateMachine.get", return_value=None):
            # Patch the _get_entity_registry method directly on the indexer
            indexer._get_entity_registry = lambda: mock_registry

            await indexer.index_entity("nonexistent.entity")

        # Should not call store methods
        mock_store.upsert_documents.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_entity(self, indexer, mock_store):
        """Test removing an entity from the index."""
        await indexer.remove_entity("light.test")

        mock_store.delete_documents.assert_called_once_with(["light.test"])

    @pytest.mark.asyncio
    async def test_full_reindex(self, indexer, mock_store, mock_embedding_provider):
        """Test full reindex of all entities."""
        # Setup mock entities
        mock_entries = [
            MockEntityEntry(entity_id="light.one", name="Light One"),
            MockEntityEntry(entity_id="light.two", name="Light Two"),
        ]

        mock_registry = MagicMock()
        mock_registry.entities = {e.entity_id: e for e in mock_entries}
        mock_registry.async_get = lambda eid: mock_registry.entities.get(eid)

        mock_area_registry = MagicMock()
        mock_area_registry.async_get_area = lambda aid: None

        def get_state(entity_id):
            return MockState(
                entity_id=entity_id,
                state="on",
                attributes={"friendly_name": entity_id},
            )

        # Patch directly on the indexer
        indexer._get_entity_registry = lambda: mock_registry

        # Patch area_registry at module level
        ar_module = sys.modules["homeassistant.helpers.area_registry"]
        original_ar_async_get = ar_module.async_get
        ar_module.async_get = lambda hass: mock_area_registry

        try:
            with patch("homeassistant.core.StateMachine.get", side_effect=get_state):
                await indexer.full_reindex()
        finally:
            ar_module.async_get = original_ar_async_get

        # Should clear and then add
        mock_store.clear_collection.assert_called_once()
        mock_store.add_documents.assert_called()

    @pytest.mark.asyncio
    async def test_index_entities_batch(self, indexer, mock_store, mock_embedding_provider):
        """Test batch indexing of entities."""
        mock_entries = [
            MockEntityEntry(entity_id="light.one", name="Light One"),
            MockEntityEntry(entity_id="light.two", name="Light Two"),
        ]

        mock_registry = MagicMock()
        mock_registry.entities = {e.entity_id: e for e in mock_entries}
        mock_registry.async_get = lambda eid: mock_registry.entities.get(eid)

        mock_area_registry = MagicMock()
        mock_area_registry.async_get_area = lambda aid: None

        def get_state(entity_id):
            return MockState(
                entity_id=entity_id,
                state="on",
                attributes={"friendly_name": entity_id},
            )

        # Patch directly on the indexer
        indexer._get_entity_registry = lambda: mock_registry

        # Patch area_registry at module level
        ar_module = sys.modules["homeassistant.helpers.area_registry"]
        original_ar_async_get = ar_module.async_get
        ar_module.async_get = lambda hass: mock_area_registry

        try:
            with patch("homeassistant.core.StateMachine.get", side_effect=get_state):
                await indexer.index_entities_batch(["light.one", "light.two"])
        finally:
            ar_module.async_get = original_ar_async_get

        # Should generate embeddings for both in one call
        mock_embedding_provider.get_embeddings.assert_called_once()
        texts = mock_embedding_provider.get_embeddings.call_args[0][0]
        assert len(texts) == 2

        mock_store.upsert_documents.assert_called_once()


class TestEntityDocument:
    """Tests for EntityDocument dataclass."""

    def test_entity_document_creation(self):
        """Test creating an EntityDocument."""
        doc = EntityDocument(
            id="light.test",
            text="Test Light in Bedroom",
            metadata={"domain": "light", "area": "bedroom"},
        )

        assert doc.id == "light.test"
        assert "Test Light" in doc.text
        assert doc.metadata["domain"] == "light"
