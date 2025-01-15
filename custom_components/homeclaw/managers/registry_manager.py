"""Registry Manager for Home Assistant registry operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class RegistryManager:
    """Manager for Home Assistant registry operations.

    Provides unified access to entity, device, and area registries
    with methods that return dict representations suitable for serialization.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the RegistryManager.

        Args:
            hass: Home Assistant instance.
        """
        self.hass = hass
        self._entity_registry = er.async_get(hass)
        self._device_registry = dr.async_get(hass)
        self._area_registry = ar.async_get(hass)

    def get_entity_entry(self, entity_id: str) -> dict | None:
        """Get entity registry entry by entity_id.

        Args:
            entity_id: The entity ID to look up (e.g., "light.living_room").

        Returns:
            Dict with entity info or None if not found.
            Dict contains: entity_id, area_id, device_id, platform, original_name.
        """
        entry = self._entity_registry.entities.get(entity_id)
        if entry is None:
            return None

        return {
            "entity_id": entry.entity_id,
            "area_id": entry.area_id,
            "device_id": entry.device_id,
            "platform": entry.platform,
            "original_name": entry.original_name,
        }

    def get_device(self, device_id: str) -> dict | None:
        """Get device registry entry by device_id.

        Args:
            device_id: The device ID to look up.

        Returns:
            Dict with device info or None if not found.
            Dict contains: id, name, manufacturer, model, area_id.
        """
        device = self._device_registry.async_get(device_id)
        if device is None:
            return None

        return {
            "id": device.id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "area_id": device.area_id,
        }

    def get_area(self, area_id: str) -> dict | None:
        """Get area registry entry by area_id.

        Args:
            area_id: The area ID to look up.

        Returns:
            Dict with area info or None if not found.
            Dict contains: id, name.
        """
        area = self._area_registry.async_get_area(area_id)
        if area is None:
            return None

        return {
            "id": area.id,
            "name": area.name,
        }

    def get_all_areas(self) -> list[dict]:
        """Get all areas from the area registry.

        Returns:
            List of dicts, each containing: id, name.
        """
        areas = []
        for area in self._area_registry.areas.values():
            areas.append({
                "id": area.id,
                "name": area.name,
            })
        return areas

    def get_entities_by_area(self, area_id: str) -> list[dict]:
        """Get all entities in a specific area.

        Args:
            area_id: The area ID to filter by.

        Returns:
            List of dicts with entity info for entities in the specified area.
        """
        entities = []
        for entry in self._entity_registry.entities.values():
            if entry.area_id == area_id:
                entities.append({
                    "entity_id": entry.entity_id,
                    "area_id": entry.area_id,
                    "device_id": entry.device_id,
                    "platform": entry.platform,
                    "original_name": entry.original_name,
                })
        return entities

    def get_devices_by_area(self, area_id: str) -> list[dict]:
        """Get all devices in a specific area.

        Args:
            area_id: The area ID to filter by.

        Returns:
            List of dicts with device info for devices in the specified area.
        """
        devices = []
        for device in self._device_registry.devices.values():
            if device.area_id == area_id:
                devices.append({
                    "id": device.id,
                    "name": device.name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area_id": device.area_id,
                })
        return devices

    def get_entities_by_device(self, device_id: str) -> list[dict]:
        """Get all entities associated with a specific device.

        Args:
            device_id: The device ID to filter by.

        Returns:
            List of dicts with entity info for entities belonging to the device.
        """
        entities = []
        for entry in self._entity_registry.entities.values():
            if entry.device_id == device_id:
                entities.append({
                    "entity_id": entry.entity_id,
                    "area_id": entry.area_id,
                    "device_id": entry.device_id,
                    "platform": entry.platform,
                    "original_name": entry.original_name,
                })
        return entities
