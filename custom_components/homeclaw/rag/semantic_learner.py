"""Semantic learner for RAG system.

This module detects category corrections from conversations and persists
them for improved entity categorization.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .entity_indexer import EntityIndexer

_LOGGER = logging.getLogger(__name__)


# Patterns for detecting semantic corrections in conversation
# Each pattern has named groups: entity (partial match) and category
CORRECTION_PATTERNS = [
    # "switch.lamp is actually a light"
    re.compile(
        r"(?P<entity>[\w.]+)\s+is\s+(?:actually\s+)?(?:a|an)\s+(?P<category>\w+)",
        re.IGNORECASE,
    ),
    # "treat switch.lamp as a light"
    re.compile(
        r"treat\s+(?P<entity>[\w.]+)\s+as\s+(?:a\s+|an\s+)?(?P<category>\w+)",
        re.IGNORECASE,
    ),
    # "switch.lamp controls the light" / "switch.lamp controls lights"
    re.compile(
        r"(?P<entity>[\w.]+)\s+controls?\s+(?:the\s+)?(?P<category>\w+)s?",
        re.IGNORECASE,
    ),
    # "the bedroom switch is a light switch"
    re.compile(
        r"(?:the\s+)?(?P<entity>[\w\s]+)\s+is\s+a\s+(?P<category>\w+)\s+switch",
        re.IGNORECASE,
    ),
    # "consider switch.lamp a light"
    re.compile(
        r"consider\s+(?P<entity>[\w.]+)\s+(?:as\s+)?(?:a|an\s+)?(?P<category>\w+)",
        re.IGNORECASE,
    ),
    # "switch.lamp should be categorized as light"
    re.compile(
        r"(?P<entity>[\w.]+)\s+should\s+be\s+(?:categorized|classified|treated)\s+as\s+(?:a|an\s+)?(?P<category>\w+)",
        re.IGNORECASE,
    ),
]

# Valid categories that make sense for entity classification
VALID_CATEGORIES = {
    "light",
    "lamp",
    "switch",
    "outlet",
    "sensor",
    "temperature",
    "humidity",
    "motion",
    "door",
    "window",
    "lock",
    "cover",
    "blind",
    "curtain",
    "fan",
    "climate",
    "thermostat",
    "media",
    "speaker",
    "tv",
    "camera",
    "security",
    "alarm",
    "water",
    "power",
    "energy",
    "battery",
    "vacuum",
    "appliance",
    "device",
}


@dataclass
class CategoryCorrection:
    """Represents a learned category correction."""

    entity_id: str
    category: str
    source: str  # "user" or "inferred"
    confidence: float = 1.0


@dataclass
class SemanticLearner:
    """Learns semantic categories from conversation patterns.

    Detects when users correct entity categorizations and persists
    these corrections for improved search relevance.
    """

    hass: HomeAssistant
    indexer: EntityIndexer
    storage_path: str
    categories: dict[str, str] = field(default_factory=dict)
    _dirty: bool = field(default=False, repr=False)

    async def async_load(self) -> None:
        """Load persisted categories from storage."""
        if not os.path.exists(self.storage_path):
            _LOGGER.debug("No persisted categories found at %s", self.storage_path)
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self.categories = data.get("categories", {})

            # Update indexer with loaded categories
            self.indexer.set_learned_categories(self.categories)

            _LOGGER.info(
                "Loaded %d learned categories from storage", len(self.categories)
            )

        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse categories file: %s", e)
        except Exception as e:
            _LOGGER.error("Failed to load categories: %s", e)

    async def async_save(self) -> None:
        """Save categories to persistent storage."""
        if not self._dirty:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            with open(self.storage_path, "w") as f:
                json.dump({"categories": self.categories}, f, indent=2)

            self._dirty = False
            _LOGGER.debug("Saved %d learned categories", len(self.categories))

        except Exception as e:
            _LOGGER.error("Failed to save categories: %s", e)

    def detect_corrections(
        self,
        text: str,
    ) -> list[CategoryCorrection]:
        """Detect category corrections in text.

        Args:
            text: Text to analyze (user message or assistant response).

        Returns:
            List of detected corrections.
        """
        corrections = []

        for pattern in CORRECTION_PATTERNS:
            for match in pattern.finditer(text):
                entity_hint = match.group("entity")
                category = match.group("category").lower()

                # Validate category
                if category not in VALID_CATEGORIES:
                    _LOGGER.debug(
                        "Ignoring invalid category '%s' for entity hint '%s'",
                        category,
                        entity_hint,
                    )
                    continue

                # Try to resolve entity hint to actual entity_id
                entity_id = self._resolve_entity_hint(entity_hint)
                if not entity_id:
                    _LOGGER.debug(
                        "Could not resolve entity hint '%s' to entity_id",
                        entity_hint,
                    )
                    continue

                corrections.append(
                    CategoryCorrection(
                        entity_id=entity_id,
                        category=category,
                        source="user",
                        confidence=0.9,
                    )
                )
                _LOGGER.debug(
                    "Detected category correction: %s -> %s",
                    entity_id,
                    category,
                )

        return corrections

    def _resolve_entity_hint(self, hint: str) -> str | None:
        """Try to resolve a text hint to an actual entity_id.

        Args:
            hint: Text that might be or refer to an entity.

        Returns:
            Resolved entity_id or None.
        """
        hint_lower = hint.lower().strip()

        # Direct entity_id match
        if "." in hint_lower:
            state = self.hass.states.get(hint_lower)
            if state:
                return hint_lower

        # Search by friendly name
        for state in self.hass.states.async_all():
            entity_id = state.entity_id
            friendly_name = state.attributes.get("friendly_name", "").lower()

            # Exact match
            if hint_lower == friendly_name or hint_lower == entity_id:
                return entity_id

            # Partial match (entity_id contains hint)
            if hint_lower in entity_id:
                return entity_id

            # Partial match (friendly name contains hint)
            if hint_lower in friendly_name:
                return entity_id

        return None

    async def persist_correction(
        self,
        entity_id: str,
        category: str,
    ) -> None:
        """Persist a category correction.

        Args:
            entity_id: The entity ID to update.
            category: The new category.
        """
        if entity_id in self.categories and self.categories[entity_id] == category:
            return  # Already learned

        self.categories[entity_id] = category
        self._dirty = True

        # Update indexer
        self.indexer.set_learned_categories(self.categories)

        # Reindex the affected entity
        await self.indexer.index_entity(entity_id)

        _LOGGER.info(
            "Learned category for %s: %s",
            entity_id,
            category,
        )

        # Save to disk
        await self.async_save()

    async def detect_and_persist(
        self,
        user_message: str,
        assistant_message: str,
    ) -> list[CategoryCorrection]:
        """Detect corrections in conversation and persist them.

        Analyzes both user and assistant messages for category corrections.

        Args:
            user_message: The user's message.
            assistant_message: The assistant's response.

        Returns:
            List of corrections that were detected and persisted.
        """
        all_corrections = []

        # Check user message (higher confidence)
        user_corrections = self.detect_corrections(user_message)
        all_corrections.extend(user_corrections)

        # Check assistant message (might acknowledge a correction)
        assistant_corrections = self.detect_corrections(assistant_message)
        for corr in assistant_corrections:
            corr.source = "inferred"
            corr.confidence = 0.7
        all_corrections.extend(assistant_corrections)

        # Persist unique corrections
        seen = set()
        for correction in all_corrections:
            key = (correction.entity_id, correction.category)
            if key not in seen:
                seen.add(key)
                await self.persist_correction(
                    correction.entity_id,
                    correction.category,
                )

        return all_corrections

    def get_category(self, entity_id: str) -> str | None:
        """Get learned category for an entity.

        Args:
            entity_id: The entity ID to look up.

        Returns:
            Learned category or None.
        """
        return self.categories.get(entity_id)

    def remove_category(self, entity_id: str) -> bool:
        """Remove a learned category.

        Args:
            entity_id: The entity ID to remove.

        Returns:
            True if removed, False if not found.
        """
        if entity_id in self.categories:
            del self.categories[entity_id]
            self._dirty = True
            self.indexer.set_learned_categories(self.categories)
            return True
        return False

    def get_all_categories(self) -> dict[str, str]:
        """Get all learned categories.

        Returns:
            Copy of the categories dictionary.
        """
        return dict(self.categories)
