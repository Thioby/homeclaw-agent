"""Event handlers for RAG system.

This module listens to Home Assistant entity registry events
and triggers reindexing when entities are added, updated, or removed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from homeassistant.core import Event, HomeAssistant

from .entity_indexer import EntityIndexer

_LOGGER = logging.getLogger(__name__)

# Home Assistant entity registry event type
EVENT_ENTITY_REGISTRY_UPDATED = "entity_registry_updated"

# Debouncing configuration
DEBOUNCE_DELAY = 5.0  # Wait 5 seconds before reindexing
BATCH_SIZE = 50  # Reindex up to 50 entities at once


@dataclass
class EntityRegistryEventHandler:
    """Handles entity registry events for RAG reindexing.

    Listens to entity added/removed/updated events and triggers
    appropriate reindexing operations.
    """

    hass: HomeAssistant
    indexer: EntityIndexer
    _unsub_listener: Callable[[], None] | None = field(default=None, repr=False)
    _started: bool = field(default=False, repr=False)

    async def async_start(self) -> None:
        """Start listening to entity registry events."""
        if self._started:
            _LOGGER.debug("Event handler already started")
            return

        # Subscribe to entity registry updated events
        self._unsub_listener = self.hass.bus.async_listen(
            EVENT_ENTITY_REGISTRY_UPDATED,
            self._handle_entity_registry_updated,
        )

        self._started = True
        _LOGGER.info("RAG event handlers started")

    async def async_stop(self) -> None:
        """Stop listening to events."""
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None

        self._started = False
        _LOGGER.info("RAG event handlers stopped")

    async def _handle_entity_registry_updated(self, event: Event) -> None:
        """Handle entity registry update events.

        Event data contains:
        - action: "create", "remove", or "update"
        - entity_id: The affected entity ID
        - changes: Dict of changed attributes (for updates)

        Args:
            event: The entity registry update event.
        """
        try:
            action = event.data.get("action")
            entity_id = event.data.get("entity_id")

            if not entity_id:
                _LOGGER.debug("Entity registry event missing entity_id")
                return

            _LOGGER.debug(
                "Entity registry event: action=%s, entity_id=%s",
                action,
                entity_id,
            )

            if action == "create":
                # New entity added - index it
                await self._on_entity_added(entity_id)

            elif action == "remove":
                # Entity removed - remove from index
                await self._on_entity_removed(entity_id)

            elif action == "update":
                # Entity updated - reindex it
                changes = event.data.get("changes", {})
                await self._on_entity_updated(entity_id, changes)

        except Exception as e:
            _LOGGER.error("Error handling entity registry event: %s", e)

    async def _on_entity_added(self, entity_id: str) -> None:
        """Handle entity added event.

        Args:
            entity_id: The new entity ID.
        """
        _LOGGER.debug("Entity added, indexing: %s", entity_id)
        try:
            await self.indexer.index_entity(entity_id)
        except Exception as e:
            _LOGGER.error("Failed to index new entity %s: %s", entity_id, e)

    async def _on_entity_removed(self, entity_id: str) -> None:
        """Handle entity removed event.

        Args:
            entity_id: The removed entity ID.
        """
        _LOGGER.debug("Entity removed, removing from index: %s", entity_id)
        try:
            await self.indexer.remove_entity(entity_id)
        except Exception as e:
            _LOGGER.error("Failed to remove entity %s from index: %s", entity_id, e)

    async def _on_entity_updated(
        self,
        entity_id: str,
        changes: dict[str, Any],
    ) -> None:
        """Handle entity updated event.

        Reindexes if relevant attributes changed (name, area, device_class, entity_id).

        Args:
            entity_id: The updated entity ID.
            changes: Dictionary of changed attributes.
        """
        # Only reindex if searchable attributes changed
        relevant_changes = {
            "name",
            "area_id",
            "device_class",
            "original_device_class",
            "original_name",
            "entity_id",  # Track entity_id renames
        }

        # If entity_id changed, we need to remove the old one
        if "entity_id" in changes:
            old_entity_id = changes.get("entity_id", {}).get("old_value")
            if old_entity_id:
                _LOGGER.info(
                    "Entity ID changed from %s to %s, removing old from index",
                    old_entity_id,
                    entity_id,
                )
                try:
                    await self.indexer.remove_entity(old_entity_id)
                except Exception as e:
                    _LOGGER.error(
                        "Failed to remove old entity %s: %s", old_entity_id, e
                    )

        if changes and not relevant_changes.intersection(changes.keys()):
            _LOGGER.debug(
                "Entity %s updated but no relevant changes, skipping reindex",
                entity_id,
            )
            return

        _LOGGER.debug("Entity updated, reindexing: %s", entity_id)
        try:
            await self.indexer.index_entity(entity_id)
        except Exception as e:
            _LOGGER.error("Failed to reindex updated entity %s: %s", entity_id, e)


@dataclass
class StateChangeHandler:
    """Handler for state change events with debouncing.

    Now enabled by default because state is included in searchable text.
    Uses debouncing to prevent API explosion from frequent sensor updates.
    """

    hass: HomeAssistant
    indexer: EntityIndexer
    enabled: bool = True  # Enabled by default now
    _unsub_listener: Callable[[], None] | None = field(default=None, repr=False)
    _pending_updates: dict[str, float] = field(default_factory=dict, repr=False)
    _update_task: asyncio.Task | None = field(default=None, repr=False)
    _update_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def async_start(self) -> None:
        """Start listening to state change events."""
        if not self.enabled:
            _LOGGER.debug("State change handler disabled, skipping")
            return

        from homeassistant.const import EVENT_STATE_CHANGED

        self._unsub_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            self._handle_state_changed,
        )
        _LOGGER.info("RAG state change handler started (with debouncing)")

    async def async_stop(self) -> None:
        """Stop listening to state changes and process remaining updates."""
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None

        # Cancel debounce task
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        # Process any remaining updates immediately (no debouncing on shutdown)
        if self._pending_updates:
            _LOGGER.info(
                "Processing %d pending updates before shutdown",
                len(self._pending_updates),
            )
            for entity_id in list(self._pending_updates.keys()):
                try:
                    await self.indexer.index_entity(entity_id)
                except Exception as e:
                    _LOGGER.error("Failed to reindex %s: %s", entity_id, e)

        _LOGGER.info("RAG state change handler stopped")

    async def _handle_state_changed(self, event: Event) -> None:
        """Handle state change events with debouncing.

        Args:
            event: The state changed event.
        """
        entity_id = event.data.get("entity_id")
        if not entity_id:
            return

        # Only track state changes for actionable entities
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        if domain not in ("light", "switch", "cover", "lock", "fan", "climate"):
            # For other entities, only reindex if friendly_name changed
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")

            if old_state and new_state:
                old_name = old_state.attributes.get("friendly_name")
                new_name = new_state.attributes.get("friendly_name")

                if old_name != new_name:
                    _LOGGER.debug(
                        "Entity %s friendly_name changed, marking for reindex",
                        entity_id,
                    )
                    async with self._update_lock:
                        self._pending_updates[entity_id] = time.time()
                        await self._start_debounce_task()
            return

        # For actionable entities, track state changes
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if old_state and new_state:
            # Only reindex if state actually changed
            if old_state.state != new_state.state:
                _LOGGER.debug(
                    "Entity %s state changed (%s -> %s), marking for reindex",
                    entity_id,
                    old_state.state,
                    new_state.state,
                )
                async with self._update_lock:
                    self._pending_updates[entity_id] = time.time()
                    await self._start_debounce_task()

    async def _start_debounce_task(self) -> None:
        """Start debounce task if not already running."""
        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(self._process_pending_updates())

    async def _process_pending_updates(self) -> None:
        """Process pending updates after debounce delay."""
        while True:
            await asyncio.sleep(DEBOUNCE_DELAY)

            async with self._update_lock:
                if not self._pending_updates:
                    # No more pending updates, exit
                    break

                # Get entities that haven't been updated recently
                now = time.time()
                entities_to_update = []
                remaining = {}

                for entity_id, last_update in self._pending_updates.items():
                    if now - last_update >= DEBOUNCE_DELAY:
                        entities_to_update.append(entity_id)
                    else:
                        remaining[entity_id] = last_update

                self._pending_updates = remaining

            # Reindex entities in batches using batch API
            if entities_to_update:
                _LOGGER.debug(
                    "Debounced reindex: processing %d entities", len(entities_to_update)
                )

                for i in range(0, len(entities_to_update), BATCH_SIZE):
                    batch = entities_to_update[i : i + BATCH_SIZE]

                    # Reindex batch using batch API (CRITICAL: Single API call for all entities!)
                    try:
                        await self.indexer.index_entities_batch(batch)
                        _LOGGER.debug(
                            "Batch reindex successful: %d entities", len(batch)
                        )
                    except Exception as e:
                        _LOGGER.error(
                            "Failed to reindex batch of %d entities: %s", len(batch), e
                        )
                        # Fallback: Try individual indexing if batch fails
                        for entity_id in batch:
                            try:
                                await self.indexer.index_entity(entity_id)
                            except Exception as e2:
                                _LOGGER.error(
                                    "Failed to reindex %s individually: %s",
                                    entity_id,
                                    e2,
                                )

                    # Small delay between batches to avoid rate limits
                    if i + BATCH_SIZE < len(entities_to_update):
                        await asyncio.sleep(0.5)
