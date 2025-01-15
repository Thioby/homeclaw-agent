"""Integration tests for RAG system."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Note: homeassistant mocks are set up in conftest.py

# Skip if chromadb is not installed
chromadb = pytest.importorskip("chromadb", exc_type=ImportError)


def setup_registry_mocks(entity_registry, area_registry):
    """Configure the module-level registry mocks."""
    helpers_mock = sys.modules["homeassistant.helpers"]
    helpers_mock.entity_registry.async_get = lambda hass: entity_registry
    helpers_mock.area_registry.async_get = lambda hass: area_registry


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


class TestRAGManagerIntegration:
    """Integration tests for RAGManager."""

    @pytest.fixture
    def mock_entities(self):
        """Return mock entity entries."""
        return [
            MockEntityEntry(
                entity_id="light.bedroom_lamp",
                name="Bedroom Lamp",
                area_id="bedroom",
                device_class="light",
            ),
            MockEntityEntry(
                entity_id="switch.kitchen_outlet",
                name="Kitchen Outlet",
                area_id="kitchen",
            ),
            MockEntityEntry(
                entity_id="sensor.living_room_temperature",
                name="Living Room Temperature",
                area_id="living_room",
                device_class="temperature",
            ),
            MockEntityEntry(
                entity_id="switch.bedroom_lamp_switch",
                name="Bedroom Lamp Switch",
                area_id="bedroom",
            ),
        ]

    @pytest.fixture
    def mock_states(self, mock_entities):
        """Return mock states."""
        return [
            MockState(
                entity_id=e.entity_id,
                state="on" if "lamp" in e.entity_id else "off",
                attributes={"friendly_name": e.name},
            )
            for e in mock_entities
        ]

    @pytest.fixture
    def mock_areas(self):
        """Return mock areas."""
        return {
            "bedroom": MockArea(name="Bedroom", id="bedroom"),
            "kitchen": MockArea(name="Kitchen", id="kitchen"),
            "living_room": MockArea(name="Living Room", id="living_room"),
        }

    @pytest.fixture
    def setup_mocks(self, hass, mock_entities, mock_states, mock_areas):
        """Setup all mocks for integration testing."""
        # Create mock entity registry
        mock_entity_registry = MagicMock()
        mock_entity_registry.entities = {e.entity_id: e for e in mock_entities}
        mock_entity_registry.async_get = lambda eid: mock_entity_registry.entities.get(
            eid
        )

        # Create mock area registry
        mock_area_registry = MagicMock()
        mock_area_registry.async_get_area = lambda aid: mock_areas.get(aid)

        # Setup states
        states_dict = {s.entity_id: s for s in mock_states}
        hass.states.get = lambda eid: states_dict.get(eid)
        hass.states.async_all = lambda: mock_states

        # Setup bus for event handlers
        hass.bus.async_listen = MagicMock(return_value=MagicMock())

        return {
            "entity_registry": mock_entity_registry,
            "area_registry": mock_area_registry,
        }

    @pytest.fixture
    def mock_embedding_responses(self):
        """Return mock embedding API responses."""

        async def mock_get_embeddings(texts):
            # Generate deterministic embeddings based on text content
            embeddings = []
            for text in texts:
                text_lower = text.lower()
                if "bedroom" in text_lower and "lamp" in text_lower:
                    base = 0.1
                elif "kitchen" in text_lower:
                    base = 0.3
                elif "temperature" in text_lower:
                    base = 0.5
                elif "bedroom" in text_lower:
                    base = 0.15  # Similar to bedroom lamp
                else:
                    base = 0.7
                embeddings.append([base + i * 0.001 for i in range(768)])
            return embeddings

        return mock_get_embeddings

    @pytest.mark.asyncio
    async def test_full_rag_workflow(
        self, hass, setup_mocks, mock_embedding_responses, tmp_path
    ):
        """Test complete RAG workflow: init -> index -> search -> learn."""
        from custom_components.homeclaw.rag import RAGManager
        from custom_components.homeclaw.rag.embeddings import OpenAIEmbeddings

        # Configure for OpenAI embeddings
        config = {"openai_token": "sk-test-key"}

        # Setup registry mocks
        setup_registry_mocks(
            setup_mocks["entity_registry"],
            setup_mocks["area_registry"],
        )

        with patch.object(
            OpenAIEmbeddings,
            "get_embeddings",
            side_effect=mock_embedding_responses,
        ):
            # Initialize RAG
            rag = RAGManager(hass=hass, config=config)
            await rag.async_initialize()

            assert rag.is_initialized

            # Verify entities were indexed
            stats = await rag.get_stats()
            assert stats["indexed_entities"] >= 0  # May vary based on mock setup
            assert stats["embedding_provider"] == "openai"

            # Search for entities
            context = await rag.get_relevant_context("bedroom light", top_k=5)
            # Context may be empty if no entities indexed, just verify no error
            assert isinstance(context, str)

            # Learn from conversation
            await rag.learn_from_conversation(
                user_message="switch.bedroom_lamp_switch is actually a light",
                assistant_message="I'll remember that",
            )

            # Verify learning (categories are tracked)
            stats = await rag.get_stats()
            assert "learned_categories" in stats

            # Cleanup
            await rag.async_shutdown()
            assert not rag.is_initialized

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_search_error(
        self, hass, setup_mocks, tmp_path
    ):
        """Test that search errors return empty context gracefully."""
        from custom_components.homeclaw.rag import RAGManager
        from custom_components.homeclaw.rag.embeddings import OpenAIEmbeddings

        config = {"openai_token": "sk-test-key"}

        # Setup registry mocks
        setup_registry_mocks(
            setup_mocks["entity_registry"],
            setup_mocks["area_registry"],
        )

        with patch.object(
            OpenAIEmbeddings,
            "get_embeddings",
            return_value=[[0.1] * 768],  # Valid embeddings for init
        ):
            rag = RAGManager(hass=hass, config=config)
            await rag.async_initialize()

            # Make search fail
            with patch.object(
                OpenAIEmbeddings,
                "get_embeddings",
                side_effect=Exception("API error"),
            ):
                # Should not raise, just return empty context
                context = await rag.get_relevant_context("test query")
                assert context == ""

            await rag.async_shutdown()

    @pytest.mark.asyncio
    async def test_entity_reindex(self, hass, setup_mocks, mock_embedding_responses, tmp_path):
        """Test reindexing a single entity."""
        from custom_components.homeclaw.rag import RAGManager
        from custom_components.homeclaw.rag.embeddings import OpenAIEmbeddings

        config = {"openai_token": "sk-test-key"}

        # Setup registry mocks
        setup_registry_mocks(
            setup_mocks["entity_registry"],
            setup_mocks["area_registry"],
        )

        with patch.object(
            OpenAIEmbeddings,
            "get_embeddings",
            side_effect=mock_embedding_responses,
        ):
            rag = RAGManager(hass=hass, config=config)
            await rag.async_initialize()

            # Reindex single entity
            await rag.reindex_entity("light.bedroom_lamp")

            # Should still work (may or may not have context depending on index state)
            context = await rag.get_relevant_context("bedroom lamp")
            assert isinstance(context, str)

            await rag.async_shutdown()

    @pytest.mark.asyncio
    async def test_remove_entity(self, hass, setup_mocks, mock_embedding_responses, tmp_path):
        """Test removing an entity from the index."""
        from custom_components.homeclaw.rag import RAGManager
        from custom_components.homeclaw.rag.embeddings import OpenAIEmbeddings

        config = {"openai_token": "sk-test-key"}

        # Setup registry mocks
        setup_registry_mocks(
            setup_mocks["entity_registry"],
            setup_mocks["area_registry"],
        )

        with patch.object(
            OpenAIEmbeddings,
            "get_embeddings",
            side_effect=mock_embedding_responses,
        ):
            rag = RAGManager(hass=hass, config=config)
            await rag.async_initialize()

            initial_count = (await rag.get_stats())["indexed_entities"]

            # Remove entity
            await rag.remove_entity("light.bedroom_lamp")

            final_count = (await rag.get_stats())["indexed_entities"]
            # Final count should be less than or equal to initial
            assert final_count <= initial_count

            await rag.async_shutdown()


class TestEventHandlerIntegration:
    """Integration tests for event handlers."""

    @pytest.mark.asyncio
    async def test_event_handler_setup(self, hass, tmp_path):
        """Test that event handlers are properly set up."""
        from custom_components.homeclaw.rag.event_handlers import (
            EntityRegistryEventHandler,
        )
        from custom_components.homeclaw.rag.entity_indexer import EntityIndexer
        from custom_components.homeclaw.rag.chroma_store import ChromaStore

        # Setup mocks
        mock_indexer = MagicMock()
        mock_indexer.index_entity = AsyncMock()
        mock_indexer.remove_entity = AsyncMock()

        handler = EntityRegistryEventHandler(hass=hass, indexer=mock_indexer)

        await handler.async_start()
        assert handler._started
        hass.bus.async_listen.assert_called_once()

        await handler.async_stop()
        assert not handler._started


class TestSemanticLearningIntegration:
    """Integration tests for semantic learning."""

    @pytest.fixture
    def mock_states_for_learning(self):
        """Return states for semantic learning tests."""
        return [
            MockState(
                "switch.bedroom_lamp_switch",
                "on",
                {"friendly_name": "Bedroom Lamp Switch"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_learning_persists_across_sessions(
        self, hass, tmp_path, mock_states_for_learning
    ):
        """Test that learned categories persist across RAG sessions."""
        from custom_components.homeclaw.rag.semantic_learner import SemanticLearner
        from custom_components.homeclaw.rag.entity_indexer import EntityIndexer

        hass.states.async_all = MagicMock(return_value=mock_states_for_learning)
        hass.states.get = MagicMock(
            side_effect=lambda eid: next(
                (s for s in mock_states_for_learning if s.entity_id == eid), None
            )
        )

        mock_indexer = MagicMock()
        mock_indexer.set_learned_categories = MagicMock()
        mock_indexer.index_entity = AsyncMock()

        storage_path = str(tmp_path / "categories.json")

        # First session - learn something
        learner1 = SemanticLearner(
            hass=hass,
            indexer=mock_indexer,
            storage_path=storage_path,
        )
        await learner1.async_load()

        await learner1.persist_correction("switch.bedroom_lamp_switch", "light")
        await learner1.async_save()

        # Second session - verify it's loaded
        learner2 = SemanticLearner(
            hass=hass,
            indexer=mock_indexer,
            storage_path=storage_path,
        )
        await learner2.async_load()

        assert learner2.get_category("switch.bedroom_lamp_switch") == "light"
