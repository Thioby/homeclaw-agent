"""Tests for RAG event handlers."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import Event

from custom_components.homeclaw.rag.event_handlers import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EntityRegistryEventHandler,
    StateChangeHandler,
)


@pytest.fixture
def mock_indexer():
    """Mock entity indexer."""
    indexer = AsyncMock()
    indexer.index_entity = AsyncMock()
    indexer.remove_entity = AsyncMock()
    return indexer


@pytest.fixture
def mock_hass():
    """Mock Home Assistant object."""
    hass = Mock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock(return_value=Mock())
    return hass


class TestEntityRegistryEventHandler:
    """Tests for EntityRegistryEventHandler."""

    @pytest.mark.asyncio
    async def test_async_start(self, mock_hass, mock_indexer):
        """Test starting the handler."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)

        await handler.async_start()

        assert handler._started is True
        mock_hass.bus.async_listen.assert_called_once_with(
            EVENT_ENTITY_REGISTRY_UPDATED,
            handler._handle_entity_registry_updated,
        )

    @pytest.mark.asyncio
    async def test_async_start_already_started(self, mock_hass, mock_indexer):
        """Test starting when already started."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        handler._started = True

        await handler.async_start()

        mock_hass.bus.async_listen.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_stop(self, mock_hass, mock_indexer):
        """Test stopping the handler."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        unsub = Mock()
        handler._unsub_listener = unsub
        handler._started = True

        await handler.async_stop()

        assert handler._started is False
        assert handler._unsub_listener is None
        unsub.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_entity_registry_updated_create(self, mock_hass, mock_indexer):
        """Test handling create event."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        event = Event(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "create", "entity_id": "light.new"},
        )

        with patch.object(
            handler, "_on_entity_added", new_callable=AsyncMock
        ) as mock_added:
            await handler._handle_entity_registry_updated(event)
            mock_added.assert_called_once_with("light.new")

    @pytest.mark.asyncio
    async def test_handle_entity_registry_updated_remove(self, mock_hass, mock_indexer):
        """Test handling remove event."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        event = Event(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "remove", "entity_id": "light.old"},
        )

        with patch.object(
            handler, "_on_entity_removed", new_callable=AsyncMock
        ) as mock_removed:
            await handler._handle_entity_registry_updated(event)
            mock_removed.assert_called_once_with("light.old")

    @pytest.mark.asyncio
    async def test_handle_entity_registry_updated_update(self, mock_hass, mock_indexer):
        """Test handling update event."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        changes = {"name": "New Name"}
        event = Event(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "update", "entity_id": "light.updated", "changes": changes},
        )

        with patch.object(
            handler, "_on_entity_updated", new_callable=AsyncMock
        ) as mock_updated:
            await handler._handle_entity_registry_updated(event)
            mock_updated.assert_called_once_with("light.updated", changes)

    @pytest.mark.asyncio
    async def test_handle_entity_registry_updated_no_entity_id(
        self, mock_hass, mock_indexer
    ):
        """Test handling event without entity_id."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        event = Event(
            EVENT_ENTITY_REGISTRY_UPDATED,
            {"action": "create"},  # Missing entity_id
        )

        await handler._handle_entity_registry_updated(event)
        # Should return early without error
        mock_indexer.index_entity.assert_not_called()
        mock_indexer.remove_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_entity_added(self, mock_hass, mock_indexer):
        """Test entity added logic."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)

        await handler._on_entity_added("light.test")

        mock_indexer.index_entity.assert_called_once_with("light.test")

    @pytest.mark.asyncio
    async def test_on_entity_added_exception(self, mock_hass, mock_indexer):
        """Test entity added logic handles exceptions."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        mock_indexer.index_entity.side_effect = Exception("Indexing failed")

        # Should log error but not raise
        await handler._on_entity_added("light.test")

        mock_indexer.index_entity.assert_called_once_with("light.test")

    @pytest.mark.asyncio
    async def test_on_entity_removed(self, mock_hass, mock_indexer):
        """Test entity removed logic."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)

        await handler._on_entity_removed("light.test")

        mock_indexer.remove_entity.assert_called_once_with("light.test")

    @pytest.mark.asyncio
    async def test_on_entity_updated_relevant_changes(self, mock_hass, mock_indexer):
        """Test entity updated with relevant changes."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        changes = {"name": "New Name"}

        await handler._on_entity_updated("light.test", changes)

        mock_indexer.index_entity.assert_called_once_with("light.test")

    @pytest.mark.asyncio
    async def test_on_entity_updated_no_relevant_changes(self, mock_hass, mock_indexer):
        """Test entity updated without relevant changes."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        changes = {"icon": "mdi:home"}

        await handler._on_entity_updated("light.test", changes)

        mock_indexer.index_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_entity_updated_entity_id_change(self, mock_hass, mock_indexer):
        """Test entity updated with entity_id change."""
        handler = EntityRegistryEventHandler(mock_hass, mock_indexer)
        changes = {
            "entity_id": {"old_value": "light.old", "new_value": "light.new"},
            "name": "Some Name",
        }

        await handler._on_entity_updated("light.new", changes)

        mock_indexer.remove_entity.assert_called_once_with("light.old")
        mock_indexer.index_entity.assert_called_once_with("light.new")


class TestStateChangeHandler:
    """Tests for StateChangeHandler."""

    @pytest.mark.asyncio
    async def test_async_start_disabled(self, mock_hass, mock_indexer):
        """Test starting when disabled."""
        handler = StateChangeHandler(mock_hass, mock_indexer, enabled=False)

        await handler.async_start()

        mock_hass.bus.async_listen.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_start_enabled(self, mock_hass, mock_indexer):
        """Test starting when enabled."""
        handler = StateChangeHandler(mock_hass, mock_indexer, enabled=True)
        from homeassistant.const import EVENT_STATE_CHANGED

        await handler.async_start()

        mock_hass.bus.async_listen.assert_called_once_with(
            EVENT_STATE_CHANGED,
            handler._handle_state_changed,
        )

    @pytest.mark.asyncio
    async def test_async_stop(self, mock_hass, mock_indexer):
        """Test stopping the handler."""
        handler = StateChangeHandler(mock_hass, mock_indexer)
        unsub = Mock()
        handler._unsub_listener = unsub

        await handler.async_stop()

        assert handler._unsub_listener is None
        unsub.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_state_changed_no_entity_id(self, mock_hass, mock_indexer):
        """Test handling state change without entity_id."""
        handler = StateChangeHandler(mock_hass, mock_indexer)
        event = Event("state_changed", {})

        await handler._handle_state_changed(event)

        mock_indexer.index_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_state_changed_friendly_name_changed(
        self, mock_hass, mock_indexer
    ):
        """Test handling state change where friendly_name changed marks entity for reindex.

        Note: friendly_name change detection only applies to non-actionable entities
        (sensors, etc.). Actionable entities (light, switch, etc.) only track state changes.
        """
        handler = StateChangeHandler(mock_hass, mock_indexer)

        old_state = Mock()
        old_state.attributes = {"friendly_name": "Old Name"}
        new_state = Mock()
        new_state.attributes = {"friendly_name": "New Name"}

        event = Event(
            "state_changed",
            {
                "entity_id": "sensor.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await handler._handle_state_changed(event)

        # With debouncing, entity is added to pending updates (not immediately indexed)
        assert "sensor.test" in handler._pending_updates

    @pytest.mark.asyncio
    async def test_handle_state_changed_friendly_name_unchanged(
        self, mock_hass, mock_indexer
    ):
        """Test handling state change where friendly_name did not change."""
        handler = StateChangeHandler(mock_hass, mock_indexer)

        old_state = Mock()
        old_state.attributes = {"friendly_name": "Same Name", "brightness": 100}
        new_state = Mock()
        new_state.attributes = {"friendly_name": "Same Name", "brightness": 200}

        event = Event(
            "state_changed",
            {
                "entity_id": "light.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await handler._handle_state_changed(event)

        mock_indexer.index_entity.assert_not_called()
