"""Tests for EntityManager.

Tests entity operations extracted from the God Class.
Uses TDD approach - tests written first.
"""

import pytest
from datetime import datetime, timezone

from custom_components.homeclaw.managers.entity_manager import EntityManager


@pytest.fixture
def entity_manager(hass):
    """Create an EntityManager with real hass."""
    return EntityManager(hass)


@pytest.fixture
def sample_states(hass):
    """Create sample entity states for testing using real hass."""
    hass.states.async_set("light.living_room", "on", {
        "friendly_name": "Living Room Light",
        "brightness": 255
    })
    hass.states.async_set("light.bedroom", "off", {
        "friendly_name": "Bedroom Light",
        "brightness": 0
    })
    hass.states.async_set("sensor.temperature", "22.5", {
        "friendly_name": "Temperature Sensor",
        "unit_of_measurement": "C",
        "device_class": "temperature"
    })
    hass.states.async_set("sensor.humidity", "45", {
        "friendly_name": "Humidity Sensor",
        "unit_of_measurement": "%",
        "device_class": "humidity"
    })
    hass.states.async_set("switch.fan", "on", {
        "friendly_name": "Fan Switch"
    })
    return hass


class TestGetEntityState:
    """Tests for get_entity_state method."""

    def test_get_entity_state_returns_entity_dict(self, entity_manager, hass):
        """Test that get_entity_state returns a proper entity state dict."""
        hass.states.async_set("light.living_room", "on", {
            "friendly_name": "Living Room Light",
            "brightness": 255
        })

        result = entity_manager.get_entity_state("light.living_room")

        assert result is not None
        assert result["entity_id"] == "light.living_room"
        assert result["state"] == "on"
        assert result["attributes"]["friendly_name"] == "Living Room Light"
        assert result["attributes"]["brightness"] == 255
        assert "last_changed" in result

    def test_get_entity_state_not_found_returns_none(self, entity_manager, hass):
        """Test that get_entity_state returns None when entity not found."""
        result = entity_manager.get_entity_state("nonexistent.entity")

        assert result is None

    def test_get_entity_state_with_empty_entity_id(self, entity_manager, hass):
        """Test that get_entity_state handles empty entity_id."""
        result = entity_manager.get_entity_state("")

        assert result is None

    def test_get_entity_state_includes_last_changed(self, entity_manager, hass):
        """Test that get_entity_state includes last_changed timestamp."""
        hass.states.async_set("light.test", "on", {})

        result = entity_manager.get_entity_state("light.test")

        assert "last_changed" in result
        # Verify it's a valid ISO format timestamp
        assert isinstance(result["last_changed"], str)


class TestGetEntitiesByDomain:
    """Tests for get_entities_by_domain method."""

    def test_get_entities_by_domain_returns_list(
        self, entity_manager, sample_states
    ):
        """Test that get_entities_by_domain returns list of entities."""
        result = entity_manager.get_entities_by_domain("light")

        assert isinstance(result, list)
        assert len(result) == 2
        entity_ids = [e["entity_id"] for e in result]
        assert "light.living_room" in entity_ids
        assert "light.bedroom" in entity_ids

    def test_get_entities_by_domain_empty_result(
        self, entity_manager, sample_states
    ):
        """Test that get_entities_by_domain returns empty list for non-existent domain."""
        result = entity_manager.get_entities_by_domain("camera")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_entities_by_domain_sensor(
        self, entity_manager, sample_states
    ):
        """Test that get_entities_by_domain correctly filters sensor domain."""
        result = entity_manager.get_entities_by_domain("sensor")

        assert len(result) == 2
        entity_ids = [e["entity_id"] for e in result]
        assert "sensor.temperature" in entity_ids
        assert "sensor.humidity" in entity_ids


class TestGetEntityIdsByDomain:
    """Tests for get_entity_ids_by_domain method."""

    def test_get_entity_ids_by_domain_returns_list_of_ids(
        self, entity_manager, sample_states
    ):
        """Test that get_entity_ids_by_domain returns only entity IDs."""
        result = entity_manager.get_entity_ids_by_domain("light")

        assert isinstance(result, list)
        assert len(result) == 2
        assert "light.living_room" in result
        assert "light.bedroom" in result
        # Ensure we only get strings (IDs), not dicts
        assert all(isinstance(id, str) for id in result)

    def test_get_entity_ids_by_domain_empty_result(
        self, entity_manager, sample_states
    ):
        """Test that get_entity_ids_by_domain returns empty list for non-existent domain."""
        result = entity_manager.get_entity_ids_by_domain("vacuum")

        assert isinstance(result, list)
        assert len(result) == 0


class TestFilterEntities:
    """Tests for filter_entities method."""

    def test_filter_entities_by_domain(
        self, entity_manager, sample_states
    ):
        """Test filtering entities by domain only."""
        result = entity_manager.filter_entities(domain="sensor")

        assert len(result) == 2
        for entity in result:
            assert entity["entity_id"].startswith("sensor.")

    def test_filter_entities_by_state(
        self, entity_manager, sample_states
    ):
        """Test filtering entities by state value."""
        result = entity_manager.filter_entities(state="on")

        assert len(result) == 2  # light.living_room and switch.fan
        for entity in result:
            assert entity["state"] == "on"

    def test_filter_entities_by_attribute(
        self, entity_manager, sample_states
    ):
        """Test filtering entities by attribute existence and value."""
        result = entity_manager.filter_entities(
            attribute="device_class", value="temperature"
        )

        assert len(result) == 1
        assert result[0]["entity_id"] == "sensor.temperature"

    def test_filter_entities_by_domain_and_state(
        self, entity_manager, sample_states
    ):
        """Test filtering entities by both domain and state."""
        result = entity_manager.filter_entities(domain="light", state="on")

        assert len(result) == 1
        assert result[0]["entity_id"] == "light.living_room"

    def test_filter_entities_no_filters_returns_all(
        self, entity_manager, sample_states
    ):
        """Test that no filters returns all entities."""
        result = entity_manager.filter_entities()

        assert len(result) == 5  # All sample states


class TestGetEntityByFriendlyName:
    """Tests for get_entity_by_friendly_name method."""

    def test_get_entity_by_friendly_name_found(
        self, entity_manager, sample_states
    ):
        """Test finding entity by friendly name."""
        result = entity_manager.get_entity_by_friendly_name("Living Room Light")

        assert result is not None
        assert result["entity_id"] == "light.living_room"

    def test_get_entity_by_friendly_name_not_found(
        self, entity_manager, sample_states
    ):
        """Test that non-existent friendly name returns None."""
        result = entity_manager.get_entity_by_friendly_name("Non-existent Entity")

        assert result is None

    def test_get_entity_by_friendly_name_case_insensitive(
        self, entity_manager, sample_states
    ):
        """Test that friendly name search is case-insensitive."""
        result = entity_manager.get_entity_by_friendly_name("living room light")

        assert result is not None
        assert result["entity_id"] == "light.living_room"

    def test_get_entity_by_friendly_name_partial_match(
        self, entity_manager, sample_states
    ):
        """Test that partial matches do not return results (exact match only)."""
        # "Living Room" is only part of "Living Room Light"
        result = entity_manager.get_entity_by_friendly_name("Living Room")

        assert result is None


class TestEntityManagerInitialization:
    """Tests for EntityManager initialization."""

    def test_init_stores_hass(self, hass):
        """Test that EntityManager stores hass reference."""
        manager = EntityManager(hass)

        assert manager.hass is hass

    def test_init_with_none_hass_raises(self):
        """Test that EntityManager raises error with None hass."""
        with pytest.raises(ValueError, match="hass is required"):
            EntityManager(None)
