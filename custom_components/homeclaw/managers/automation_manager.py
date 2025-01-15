"""Automation Manager for Home Assistant automations.

Extracted from the God Class to handle all automation-related operations.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

AUTOMATION_DOMAIN = "automation"


class AutomationManager:
    """Manager for Home Assistant automation operations.

    Provides methods to validate, create, list, and toggle automations.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the AutomationManager.

        Args:
            hass: Home Assistant instance.

        Raises:
            ValueError: If hass is None.
        """
        if hass is None:
            raise ValueError("hass is required")
        self.hass = hass

    def _state_to_dict(self, state) -> dict[str, Any]:
        """Convert a Home Assistant state object to a dictionary.

        Args:
            state: Home Assistant state object.

        Returns:
            Dictionary with entity_id, state, attributes, and last_changed.
        """
        return {
            "entity_id": state.entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": (
                state.last_changed.isoformat() if state.last_changed else None
            ),
        }

    def validate_automation(self, config: dict) -> dict:
        """Validate automation configuration.

        Checks that the configuration has required trigger and action fields.
        Each action must have either a 'service' or 'action' field.

        Args:
            config: Automation configuration dictionary.

        Returns:
            Dict with 'valid' boolean and optional 'error' string.
        """
        errors: list[str] = []

        # Validate triggers - must exist and not be empty
        triggers = config.get("trigger")
        if triggers is None:
            errors.append("At least one trigger is required")
        elif isinstance(triggers, list):
            if len(triggers) == 0:
                errors.append("At least one trigger is required")
        elif not isinstance(triggers, dict):
            errors.append("Trigger must be a list or dictionary")

        # Validate actions - must exist and not be empty
        actions = config.get("action")
        if actions is None:
            errors.append("At least one action is required")
        elif isinstance(actions, list):
            if len(actions) == 0:
                errors.append("At least one action is required")
            else:
                # Validate each action has service or action field
                for i, action in enumerate(actions):
                    if isinstance(action, dict):
                        if "service" not in action and "action" not in action:
                            errors.append(
                                f"Action {i} must have 'service' or 'action' field"
                            )
        elif isinstance(actions, dict):
            # Single action - validate it has service or action field
            if "service" not in actions and "action" not in actions:
                errors.append("Action must have 'service' or 'action' field")
        else:
            errors.append("Action must be a list or dictionary")

        if errors:
            return {"valid": False, "error": "; ".join(errors)}

        return {"valid": True}

    async def create_automation(self, config: dict) -> dict:
        """Create a new automation.

        Generates an ID if not provided and calls the reload service.

        Args:
            config: Automation configuration dictionary.

        Returns:
            Dict with 'success' boolean and 'id' of the created automation.
        """
        # Generate ID if not provided
        automation_id = config.get("id")
        if not automation_id:
            automation_id = str(uuid.uuid4())
            config["id"] = automation_id

        _LOGGER.debug("Creating automation with id: %s", automation_id)

        try:
            # Call the automation reload service to pick up new automations
            await self.hass.services.async_call(
                AUTOMATION_DOMAIN,
                "reload",
                {},
            )

            return {"success": True, "id": automation_id}
        except Exception as e:
            _LOGGER.exception("Error creating automation: %s", str(e))
            return {"success": False, "error": str(e), "id": automation_id}

    def get_automations(self) -> list[dict[str, Any]]:
        """Get all automation entities.

        Returns:
            List of automation entity state dictionaries.
        """
        _LOGGER.debug("Getting all automations")
        prefix = f"{AUTOMATION_DOMAIN}."
        states = [
            state
            for state in self.hass.states.async_all()
            if state.entity_id.startswith(prefix)
        ]

        _LOGGER.debug("Found %d automations", len(states))
        return [self._state_to_dict(state) for state in states]

    async def toggle_automation(self, entity_id: str, enable: bool) -> dict:
        """Turn an automation on or off.

        Args:
            entity_id: The automation entity ID.
            enable: True to turn on, False to turn off.

        Returns:
            Dict with 'success' boolean and 'entity_id'.
        """
        service = "turn_on" if enable else "turn_off"
        _LOGGER.debug("Toggling automation %s to %s", entity_id, service)

        try:
            await self.hass.services.async_call(
                AUTOMATION_DOMAIN,
                service,
                {"entity_id": entity_id},
            )

            return {"success": True, "entity_id": entity_id}
        except Exception as e:
            _LOGGER.exception("Error toggling automation %s: %s", entity_id, str(e))
            return {"success": False, "entity_id": entity_id, "error": str(e)}
