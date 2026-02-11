"""Entity Manager for Home Assistant entities.

Extracted from the God Class to handle all entity-related operations.
Uses a per-domain cache invalidated via EVENT_STATE_CHANGED for performance.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from homeassistant.core import Event, HomeAssistant, State

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    """Manager for Home Assistant entity operations.

    Provides methods to query and filter entities from Home Assistant state machine.
    Maintains an in-memory per-domain cache that is invalidated on state_changed events,
    avoiding repeated full scans of ``hass.states.async_all()`` on large instances.
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

        # Per-domain cache: domain -> {entity_id -> State} for O(1) updates
        self._domain_cache: dict[str, dict[str, State]] = {}
        # Tracks whether the cache has been fully populated at least once
        self._cache_built: bool = False
        # Unsubscribe callback for EVENT_STATE_CHANGED listener
        self._unsub_state_changed: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def async_setup(self) -> None:
        """Set up the state_changed listener for cache invalidation.

        Call this after construction to enable automatic cache invalidation.
        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._unsub_state_changed is not None:
            return

        from homeassistant.const import EVENT_STATE_CHANGED

        self._unsub_state_changed = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            self._handle_state_changed,
        )
        _LOGGER.debug("EntityManager: state_changed listener registered")

    def async_teardown(self) -> None:
        """Tear down the state_changed listener and clear cache."""
        if self._unsub_state_changed is not None:
            self._unsub_state_changed()
            self._unsub_state_changed = None
        self._domain_cache.clear()
        self._cache_built = False
        _LOGGER.debug("EntityManager: listener removed, cache cleared")

    # ------------------------------------------------------------------
    # Cache internals
    # ------------------------------------------------------------------

    @staticmethod
    def _get_domain(entity_id: str) -> str:
        """Extract domain from an entity_id string.

        Args:
            entity_id: e.g. 'light.living_room'.

        Returns:
            Domain string (e.g. 'light'), or '' if malformed.
        """
        return entity_id.split(".", 1)[0] if "." in entity_id else ""

    def _build_cache(self) -> None:
        """Populate the full per-domain cache from hass.states.async_all().

        Called lazily on the first query method invocation.
        """
        self._domain_cache.clear()
        for state in self.hass.states.async_all():
            domain = self._get_domain(state.entity_id)
            self._domain_cache.setdefault(domain, {})[state.entity_id] = state
        self._cache_built = True
        total = sum(len(v) for v in self._domain_cache.values())
        _LOGGER.debug(
            "EntityManager: cache built with %d entities across %d domains",
            total,
            len(self._domain_cache),
        )

    def _ensure_cache(self) -> None:
        """Ensure the cache has been built at least once."""
        if not self._cache_built:
            self._build_cache()

    async def _handle_state_changed(self, event: Event) -> None:
        """Invalidate cache entries on state changes.

        Handles entity additions, removals, and state/attribute changes
        via O(1) dict operations on the affected domain bucket.

        Args:
            event: The state_changed event from Home Assistant.
        """
        entity_id: str | None = event.data.get("entity_id")
        if not entity_id:
            return

        if not self._cache_built:
            # Cache hasn't been used yet — nothing to invalidate.
            return

        domain = self._get_domain(entity_id)
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if new_state is None and old_state is not None:
            # Entity was removed — O(1) pop
            if domain in self._domain_cache:
                self._domain_cache[domain].pop(entity_id, None)
                if not self._domain_cache[domain]:
                    del self._domain_cache[domain]
        elif new_state is not None:
            # Entity was added or updated — O(1) insert/replace
            self._domain_cache.setdefault(domain, {})[entity_id] = new_state

    # ------------------------------------------------------------------
    # Convenience: iterate states, optionally filtered by domain
    # ------------------------------------------------------------------

    def _iter_states(self, domain: str | None = None) -> Iterator[State]:
        """Yield State objects, optionally filtered by domain.

        Uses the per-domain cache for O(1) domain look-ups instead of
        scanning the entire state machine.

        Args:
            domain: Optional domain filter (e.g. 'light').

        Yields:
            State objects matching the filter.
        """
        self._ensure_cache()
        if domain:
            yield from self._domain_cache.get(domain, {}).values()
        else:
            for entities in self._domain_cache.values():
                yield from entities.values()

    # ------------------------------------------------------------------
    # Public API (unchanged signatures)
    # ------------------------------------------------------------------

    def _state_to_dict(self, state: State) -> dict[str, Any]:
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

        Uses ``hass.states.get()`` directly — O(1) hash look-up.

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
        results = list(self._iter_states(domain))
        _LOGGER.debug("Found %d entities in domain %s", len(results), domain)
        return [self._state_to_dict(state) for state in results]

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
        entity_ids = [s.entity_id for s in self._iter_states(domain)]
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

        Uses the per-domain cache so that a domain filter avoids scanning
        all entities.

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

        results = []

        for entity_state in self._iter_states(domain):
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

        for state in self._iter_states():
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
