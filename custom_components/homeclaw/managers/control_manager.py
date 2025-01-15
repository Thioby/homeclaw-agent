"""Control Manager for Home Assistant service calls.

Extracted from the God Class to handle all control operations
including service calls and entity state changes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TOGGLE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ControlManager:
    """Manager for Home Assistant control operations.

    Provides methods to call services and control entities.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the ControlManager.

        Args:
            hass: Home Assistant instance.

        Raises:
            ValueError: If hass is None.
        """
        if hass is None:
            raise ValueError("hass is required")
        self.hass = hass

    async def call_service(
        self,
        domain: str,
        service: str,
        target: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a Home Assistant service.

        Args:
            domain: The service domain (e.g., 'light', 'switch').
            service: The service name (e.g., 'turn_on', 'turn_off').
            target: Optional target specification (entity_id, area_id, etc.).
            data: Optional additional service data.

        Returns:
            Dictionary with success status and optional error message.
        """
        _LOGGER.debug(
            "Calling service %s.%s with target=%s, data=%s",
            domain,
            service,
            target,
            data,
        )

        # Check if service exists
        if not self.hass.services.has_service(domain, service):
            error_msg = f"Service {domain}.{service} not found"
            _LOGGER.warning(error_msg)
            return {"success": False, "error": error_msg}

        try:
            # Prepare service call data
            service_data: dict[str, Any] = {}

            # Add target entity_id if provided
            if target:
                service_data.update(target)

            # Add additional service data if provided
            if data:
                service_data.update(data)

            await self.hass.services.async_call(domain, service, service_data)

            return {"success": True}

        except Exception as e:
            error_msg = f"Error calling service {domain}.{service}: {e}"
            _LOGGER.exception(error_msg)
            return {"success": False, "error": error_msg}

    async def turn_on(self, entity_id: str, **kwargs: Any) -> dict[str, Any]:
        """Turn on an entity.

        Args:
            entity_id: The entity ID to turn on.
            **kwargs: Additional service data (e.g., brightness for lights).

        Returns:
            Dictionary with success status and optional error message.
        """
        domain = entity_id.split(".")[0]
        return await self.call_service(
            domain,
            SERVICE_TURN_ON,
            target={"entity_id": entity_id},
            data=kwargs if kwargs else None,
        )

    async def turn_off(self, entity_id: str, **kwargs: Any) -> dict[str, Any]:
        """Turn off an entity.

        Args:
            entity_id: The entity ID to turn off.
            **kwargs: Additional service data (e.g., transition time).

        Returns:
            Dictionary with success status and optional error message.
        """
        domain = entity_id.split(".")[0]
        return await self.call_service(
            domain,
            SERVICE_TURN_OFF,
            target={"entity_id": entity_id},
            data=kwargs if kwargs else None,
        )

    async def toggle(self, entity_id: str, **kwargs: Any) -> dict[str, Any]:
        """Toggle an entity.

        Args:
            entity_id: The entity ID to toggle.
            **kwargs: Additional service data.

        Returns:
            Dictionary with success status and optional error message.
        """
        domain = entity_id.split(".")[0]
        return await self.call_service(
            domain,
            SERVICE_TOGGLE,
            target={"entity_id": entity_id},
            data=kwargs if kwargs else None,
        )

    async def set_value(self, entity_id: str, value: Any) -> dict[str, Any]:
        """Set a value for an input entity.

        Handles input_number, input_text, input_boolean, and input_select entities.

        Args:
            entity_id: The entity ID to set value for.
            value: The value to set.

        Returns:
            Dictionary with success status and optional error message.
        """
        domain = entity_id.split(".")[0]

        if domain == "input_number":
            return await self.call_service(
                "input_number",
                "set_value",
                target={"entity_id": entity_id},
                data={"value": value},
            )

        elif domain == "input_boolean":
            # Turn on if truthy, turn off otherwise
            service = SERVICE_TURN_ON if value else SERVICE_TURN_OFF
            return await self.call_service(
                "input_boolean",
                service,
                target={"entity_id": entity_id},
            )

        elif domain == "input_select":
            return await self.call_service(
                "input_select",
                "select_option",
                target={"entity_id": entity_id},
                data={"option": value},
            )

        elif domain == "input_text":
            return await self.call_service(
                "input_text",
                "set_value",
                target={"entity_id": entity_id},
                data={"value": value},
            )

        else:
            error_msg = f"Unsupported domain for set_value: {domain}"
            _LOGGER.warning(error_msg)
            return {"success": False, "error": error_msg}
