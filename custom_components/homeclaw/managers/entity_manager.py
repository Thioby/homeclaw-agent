"""Entity Manager for Home Assistant entities.

Extracted from the God Class to handle all entity-related operations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    """Manager for Home Assistant entity operations.

    Provides methods to query and filter entities from Home Assistant state machine.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the EntityManager.

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

    def get_entity_state(self, entity_id: str) -> dict[str, Any] | None:
        """Get the state of a specific entity.

        Args:
            entity_id: The entity ID to look up.

        Returns:
            Dictionary with entity state information, or None if not found.
        """
        if not entity_id:
            _LOGGER.debug("Empty entity_id provided")
            return None

        _LOGGER.debug("Getting entity state for: %s", entity_id)
        state = self.hass.states.get(entity_id)

        if not state:
            _LOGGER.debug("Entity not found: %s", entity_id)
            return None

        return self._state_to_dict(state)

    def get_entities_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """Get all entities for a specific domain.

        Args:
            domain: The domain to filter by (e.g., 'light', 'sensor').

        Returns:
            List of entity state dictionaries for the specified domain.
        """
        if not domain:
            _LOGGER.debug("Empty domain provided")
            return []

        _LOGGER.debug("Getting all entities for domain: %s", domain)
        prefix = f"{domain}."
        states = [
            state
            for state in self.hass.states.async_all()
            if state.entity_id.startswith(prefix)
        ]

        _LOGGER.debug("Found %d entities in domain %s", len(states), domain)
        return [self._state_to_dict(state) for state in states]

    def get_entity_ids_by_domain(self, domain: str) -> list[str]:
        """Get all entity IDs for a specific domain.

        Args:
            domain: The domain to filter by (e.g., 'light', 'sensor').

        Returns:
            List of entity IDs (strings) for the specified domain.
        """
        if not domain:
            _LOGGER.debug("Empty domain provided")
            return []

        _LOGGER.debug("Getting entity IDs for domain: %s", domain)
        prefix = f"{domain}."
        entity_ids = [
            state.entity_id
            for state in self.hass.states.async_all()
            if state.entity_id.startswith(prefix)
        ]

        _LOGGER.debug("Found %d entity IDs in domain %s", len(entity_ids), domain)
        return entity_ids

    def filter_entities(
        self,
        domain: str | None = None,
        attribute: str | None = None,
        value: Any | None = None,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        """Filter entities by various criteria.

        Args:
            domain: Optional domain to filter by.
            attribute: Optional attribute name to filter by.
            value: Optional attribute value to match (requires attribute).
            state: Optional state value to filter by.

        Returns:
            List of entity state dictionaries matching the criteria.
        """
        _LOGGER.debug(
            "Filtering entities: domain=%s, attribute=%s, value=%s, state=%s",
            domain,
            attribute,
            value,
            state,
        )

        all_states = self.hass.states.async_all()
        results = []

        for entity_state in all_states:
            # Filter by domain
            if domain and not entity_state.entity_id.startswith(f"{domain}."):
                continue

            # Filter by state value
            if state is not None and entity_state.state != state:
                continue

            # Filter by attribute and value
            if attribute is not None:
                attr_value = entity_state.attributes.get(attribute)
                if value is not None:
                    if attr_value != value:
                        continue
                elif attr_value is None:
                    continue

            results.append(self._state_to_dict(entity_state))

        _LOGGER.debug("Filter returned %d entities", len(results))
        return results

    def get_entity_by_friendly_name(self, friendly_name: str) -> dict[str, Any] | None:
        """Find an entity by its friendly name.

        Args:
            friendly_name: The friendly name to search for (case-insensitive).

        Returns:
            Entity state dictionary if found, None otherwise.
        """
        if not friendly_name:
            _LOGGER.debug("Empty friendly_name provided")
            return None

        _LOGGER.debug("Searching for entity with friendly_name: %s", friendly_name)
        search_name = friendly_name.lower()

        for state in self.hass.states.async_all():
            entity_friendly_name = state.attributes.get("friendly_name")
            if entity_friendly_name and entity_friendly_name.lower() == search_name:
                _LOGGER.debug(
                    "Found entity %s with friendly_name %s",
                    state.entity_id,
                    friendly_name,
                )
                return self._state_to_dict(state)

        _LOGGER.debug("No entity found with friendly_name: %s", friendly_name)
        return None
