"""Tests for RegistryManager."""

import pytest
from unittest.mock import MagicMock, patch


class TestRegistryManager:
    """Test cases for RegistryManager."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        return hass

    @pytest.fixture
    def mock_entity_entry(self):
        """Create mock entity registry entry."""
        entry = MagicMock()
        entry.entity_id = "light.living_room"
        entry.area_id = "area_living_room"
        entry.device_id = "device_123"
        entry.platform = "hue"
        entry.original_name = "Living Room Light"
        entry.disabled = False
        return entry

    @pytest.fixture
    def mock_device_entry(self):
        """Create mock device registry entry."""
        device = MagicMock()
        device.id = "device_123"
        device.name = "Hue Light"
        device.manufacturer = "Philips"
        device.model = "LCT001"
        device.area_id = "area_living_room"
        device.disabled_by = None
        return device

    @pytest.fixture
    def mock_area_entry(self):
        """Create mock area registry entry."""
        area = MagicMock()
        area.id = "area_living_room"
        area.name = "Living Room"
        return area

    @pytest.fixture
    def mock_registries(self, mock_entity_entry, mock_device_entry, mock_area_entry):
        """Create mock registries."""
        entity_registry = MagicMock()
        entity_registry.async_get.return_value = mock_entity_entry
        entity_registry.entities = {
            "light.living_room": mock_entity_entry,
        }

        device_registry = MagicMock()
        device_registry.async_get.return_value = mock_device_entry
        device_registry.devices = {
            "device_123": mock_device_entry,
        }

        area_registry = MagicMock()
        area_registry.async_get_area.return_value = mock_area_entry
        area_registry.areas = {
            "area_living_room": mock_area_entry,
        }

        return {
            "entity": entity_registry,
            "device": device_registry,
            "area": area_registry,
        }

    @pytest.fixture
    def registry_manager(self, mock_hass, mock_registries):
        """Create RegistryManager with mocked registries."""
        with patch(
            "custom_components.homeclaw.managers.registry_manager.er.async_get"
        ) as mock_er, patch(
            "custom_components.homeclaw.managers.registry_manager.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.homeclaw.managers.registry_manager.ar.async_get"
        ) as mock_ar:
            mock_er.return_value = mock_registries["entity"]
            mock_dr.return_value = mock_registries["device"]
            mock_ar.return_value = mock_registries["area"]

            from custom_components.homeclaw.managers.registry_manager import (
                RegistryManager,
            )

            manager = RegistryManager(mock_hass)
            return manager

    def test_get_entity_entry(self, registry_manager, mock_entity_entry):
        """Test get_entity_entry returns entity registry entry as dict."""
        result = registry_manager.get_entity_entry("light.living_room")

        assert result is not None
        assert result["entity_id"] == "light.living_room"
        assert result["area_id"] == "area_living_room"
        assert result["device_id"] == "device_123"
        assert result["platform"] == "hue"
        assert result["original_name"] == "Living Room Light"

    def test_get_entity_entry_not_found(self, registry_manager):
        """Test get_entity_entry returns None for non-existent entity."""
        result = registry_manager.get_entity_entry("light.nonexistent")

        assert result is None

    def test_get_device(self, registry_manager, mock_device_entry):
        """Test get_device returns device info as dict."""
        result = registry_manager.get_device("device_123")

        assert result is not None
        assert result["id"] == "device_123"
        assert result["name"] == "Hue Light"
        assert result["manufacturer"] == "Philips"
        assert result["model"] == "LCT001"
        assert result["area_id"] == "area_living_room"

    def test_get_device_not_found(self, registry_manager, mock_registries):
        """Test get_device returns None for non-existent device."""
        mock_registries["device"].async_get.return_value = None
        result = registry_manager.get_device("nonexistent_device")

        assert result is None

    def test_get_area(self, registry_manager, mock_area_entry):
        """Test get_area returns area info as dict."""
        result = registry_manager.get_area("area_living_room")

        assert result is not None
        assert result["id"] == "area_living_room"
        assert result["name"] == "Living Room"

    def test_get_area_not_found(self, registry_manager, mock_registries):
        """Test get_area returns None for non-existent area."""
        mock_registries["area"].async_get_area.return_value = None
        result = registry_manager.get_area("nonexistent_area")

        assert result is None

    def test_get_all_areas(self, registry_manager, mock_area_entry):
        """Test get_all_areas returns list of areas."""
        result = registry_manager.get_all_areas()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "area_living_room"
        assert result[0]["name"] == "Living Room"

    def test_get_all_areas_empty(self, mock_hass):
        """Test get_all_areas returns empty list when no areas."""
        with patch(
            "custom_components.homeclaw.managers.registry_manager.er.async_get"
        ) as mock_er, patch(
            "custom_components.homeclaw.managers.registry_manager.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.homeclaw.managers.registry_manager.ar.async_get"
        ) as mock_ar:
            mock_er.return_value = MagicMock(entities={})
            mock_dr.return_value = MagicMock(devices={})
            empty_area_registry = MagicMock()
            empty_area_registry.areas = {}
            mock_ar.return_value = empty_area_registry

            from custom_components.homeclaw.managers.registry_manager import (
                RegistryManager,
            )

            manager = RegistryManager(mock_hass)
            result = manager.get_all_areas()

            assert isinstance(result, list)
            assert len(result) == 0

    def test_get_entities_by_area(self, registry_manager, mock_entity_entry):
        """Test get_entities_by_area returns entities in specified area."""
        result = registry_manager.get_entities_by_area("area_living_room")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["entity_id"] == "light.living_room"
        assert result[0]["area_id"] == "area_living_room"

    def test_get_entities_by_area_empty(self, registry_manager):
        """Test get_entities_by_area returns empty list for area with no entities."""
        result = registry_manager.get_entities_by_area("nonexistent_area")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_devices_by_area(self, registry_manager, mock_device_entry):
        """Test get_devices_by_area returns devices in specified area."""
        result = registry_manager.get_devices_by_area("area_living_room")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "device_123"
        assert result[0]["area_id"] == "area_living_room"

    def test_get_devices_by_area_empty(self, registry_manager):
        """Test get_devices_by_area returns empty list for area with no devices."""
        result = registry_manager.get_devices_by_area("nonexistent_area")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_entities_by_device(self, registry_manager, mock_entity_entry):
        """Test get_entities_by_device returns entities for specified device."""
        result = registry_manager.get_entities_by_device("device_123")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["entity_id"] == "light.living_room"
        assert result[0]["device_id"] == "device_123"

    def test_get_entities_by_device_empty(self, registry_manager):
        """Test get_entities_by_device returns empty list for device with no entities."""
        result = registry_manager.get_entities_by_device("nonexistent_device")

        assert isinstance(result, list)
        assert len(result) == 0


class TestRegistryManagerWithMultipleEntries:
    """Test RegistryManager with multiple entries in registries."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        return MagicMock()

    @pytest.fixture
    def multiple_entities(self):
        """Create multiple mock entity entries."""
        entities = {}
        for i in range(3):
            entry = MagicMock()
            entry.entity_id = f"light.room_{i}"
            entry.area_id = "area_1" if i < 2 else "area_2"
            entry.device_id = f"device_{i}"
            entry.platform = "hue"
            entry.original_name = f"Room {i} Light"
            entry.disabled = False
            entities[entry.entity_id] = entry
        return entities

    @pytest.fixture
    def multiple_devices(self):
        """Create multiple mock device entries."""
        devices = {}
        for i in range(3):
            device = MagicMock()
            device.id = f"device_{i}"
            device.name = f"Device {i}"
            device.manufacturer = "Philips"
            device.model = f"Model {i}"
            device.area_id = "area_1" if i < 2 else "area_2"
            device.disabled_by = None
            devices[device.id] = device
        return devices

    @pytest.fixture
    def multiple_areas(self):
        """Create multiple mock area entries."""
        areas = {}
        for i in range(2):
            area = MagicMock()
            area.id = f"area_{i + 1}"
            area.name = f"Area {i + 1}"
            areas[area.id] = area
        return areas

    @pytest.fixture
    def registry_manager_multiple(
        self, mock_hass, multiple_entities, multiple_devices, multiple_areas
    ):
        """Create RegistryManager with multiple entries."""
        entity_registry = MagicMock()
        entity_registry.entities = multiple_entities
        entity_registry.async_get.side_effect = lambda eid: multiple_entities.get(eid)

        device_registry = MagicMock()
        device_registry.devices = multiple_devices
        device_registry.async_get.side_effect = lambda did: multiple_devices.get(did)

        area_registry = MagicMock()
        area_registry.areas = multiple_areas
        area_registry.async_get_area.side_effect = lambda aid: multiple_areas.get(aid)

        with patch(
            "custom_components.homeclaw.managers.registry_manager.er.async_get"
        ) as mock_er, patch(
            "custom_components.homeclaw.managers.registry_manager.dr.async_get"
        ) as mock_dr, patch(
            "custom_components.homeclaw.managers.registry_manager.ar.async_get"
        ) as mock_ar:
            mock_er.return_value = entity_registry
            mock_dr.return_value = device_registry
            mock_ar.return_value = area_registry

            from custom_components.homeclaw.managers.registry_manager import (
                RegistryManager,
            )

            manager = RegistryManager(mock_hass)
            return manager

    def test_get_all_areas_multiple(self, registry_manager_multiple):
        """Test get_all_areas with multiple areas."""
        result = registry_manager_multiple.get_all_areas()

        assert isinstance(result, list)
        assert len(result) == 2
        area_ids = [a["id"] for a in result]
        assert "area_1" in area_ids
        assert "area_2" in area_ids

    def test_get_entities_by_area_multiple(self, registry_manager_multiple):
        """Test get_entities_by_area filters correctly."""
        result = registry_manager_multiple.get_entities_by_area("area_1")

        assert isinstance(result, list)
        assert len(result) == 2
        entity_ids = [e["entity_id"] for e in result]
        assert "light.room_0" in entity_ids
        assert "light.room_1" in entity_ids
        assert "light.room_2" not in entity_ids

    def test_get_devices_by_area_multiple(self, registry_manager_multiple):
        """Test get_devices_by_area filters correctly."""
        result = registry_manager_multiple.get_devices_by_area("area_1")

        assert isinstance(result, list)
        assert len(result) == 2
        device_ids = [d["id"] for d in result]
        assert "device_0" in device_ids
        assert "device_1" in device_ids
        assert "device_2" not in device_ids
