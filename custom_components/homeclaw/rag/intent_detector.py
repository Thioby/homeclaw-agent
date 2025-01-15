"""Semantic intent detection using cached embeddings.

This module detects user intent (domain, device_class, area) from queries
using semantic similarity with prototype queries, eliminating the need
for hardcoded keyword lists.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from .embeddings import EmbeddingProvider, get_embedding_for_query

_LOGGER = logging.getLogger(__name__)

# Minimum similarity score to consider a match
INTENT_THRESHOLD = 0.65

# Prototype queries for each intent type
# Format: "intent_type:value" -> list of example queries
INTENT_PROTOTYPES: dict[str, list[str]] = {
    # Device classes
    "device_class:temperature": [
        "what is the temperature",
        "how warm is it",
        "how cold is it",
        "jaka jest temperatura",
        "ile stopni",
        "temperatura w domu",
        "czy jest ciepło",
        "czy jest zimno",
        "temperature reading",
        "weather forecast",
        "prognoza pogody",
        "jaka będzie pogoda",
        "sprawdź pogodę",
    ],
    "device_class:humidity": [
        "what is the humidity",
        "how humid is it",
        "jaka jest wilgotność",
        "wilgotność powietrza",
        "humidity level",
    ],
    "device_class:motion": [
        "is there motion",
        "any movement detected",
        "czy jest ruch",
        "wykryto ruch",
        "motion sensor",
    ],
    "device_class:door": [
        "is the door open",
        "door status",
        "czy drzwi są otwarte",
        "stan drzwi",
    ],
    "device_class:window": [
        "is the window open",
        "window status",
        "czy okno jest otwarte",
        "stan okna",
    ],
    "device_class:battery": [
        "battery level",
        "how much battery",
        "poziom baterii",
        "stan baterii",
    ],
    "device_class:power": [
        "power consumption",
        "energy usage",
        "zużycie prądu",
        "ile prądu",
        "moc",
    ],
    # Domains
    "domain:light": [
        "turn on the light",
        "turn off the light",
        "switch the lights",
        "włącz światło",
        "wyłącz światło",
        "wylacz swiatlo",
        "zapal lampę",
        "zgaś światło",
        "light status",
        "stan świateł",
    ],
    "domain:switch": [
        "toggle the switch",
        "turn on the outlet",
        "turn off the outlet",
        "włącz przełącznik",
        "wyłącz przełącznik",
        "gniazdko",
    ],
    "domain:cover": [
        "open the blinds",
        "close the curtains",
        "open the gate",
        "otwórz bramę",
        "zamknij roletę",
        "żaluzje",
    ],
    "domain:climate": [
        "set the thermostat",
        "adjust temperature",
        "air conditioning",
        "heating",
        "heater",
        "fireplace",
        "ustaw klimatyzację",
        "ogrzewanie",
        "piecyk",
        "zapalić w piecyku",
        "włącz ogrzewanie",
        "wyłącz ogrzewanie",
    ],
    "domain:lock": [
        "lock the door",
        "unlock",
        "zamknij zamek",
        "otwórz zamek",
    ],
    "domain:fan": [
        "turn on the fan",
        "fan speed",
        "włącz wentylator",
    ],
    "domain:media_player": [
        "play music",
        "pause the tv",
        "turn on the tv",
        "turn off the tv",
        "włącz telewizor",
        "wyłącz telewizor",
        "odtwórz muzykę",
        "głośność",
        "telewizor",
        "tv history",
    ],
    "domain:camera": [
        "show camera",
        "camera feed",
        "pokaż kamerę",
        "obraz z kamery",
    ],
    # Common areas/rooms
    "area:bedroom": [
        "in the bedroom",
        "bedroom lights",
        "w sypialni",
        "sypialnia",
    ],
    "area:living_room": [
        "in the living room",
        "living room",
        "w salonie",
        "salon",
        "pokój dzienny",
    ],
    "area:kitchen": [
        "in the kitchen",
        "kitchen lights",
        "w kuchni",
        "kuchnia",
    ],
    "area:bathroom": [
        "in the bathroom",
        "bathroom",
        "w łazience",
        "łazienka",
    ],
    "area:office": [
        "in the office",
        "office",
        "w biurze",
        "gabinet",
    ],
    "area:garage": [
        "in the garage",
        "garage door",
        "w garażu",
        "garaż",
        "brama garażowa",
    ],
    "area:hallway": [
        "in the hallway",
        "corridor",
        "w korytarzu",
        "przedpokój",
        "wiatrołap",
    ],
    "area:garden": [
        "in the garden",
        "outdoor",
        "w ogrodzie",
        "ogród",
        "na zewnątrz",
    ],
}


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


@dataclass
class IntentDetector:
    """Detects user intent using semantic similarity with cached prototypes."""

    embedding_provider: EmbeddingProvider
    _prototype_cache: dict[str, list[float]] = field(default_factory=dict)
    _initialized: bool = field(default=False)

    async def async_initialize(self) -> None:
        """Pre-compute and cache embeddings for all prototype queries."""
        if self._initialized:
            return

        _LOGGER.info("Initializing semantic intent detector...")
        total_prototypes = sum(len(protos) for protos in INTENT_PROTOTYPES.values())
        cached = 0

        for intent_key, prototypes in INTENT_PROTOTYPES.items():
            for proto_query in prototypes:
                try:
                    embedding = await get_embedding_for_query(
                        self.embedding_provider, proto_query
                    )
                    cache_key = f"{intent_key}:{proto_query}"
                    self._prototype_cache[cache_key] = embedding
                    cached += 1
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to cache embedding for '%s': %s", proto_query, e
                    )

        self._initialized = True
        _LOGGER.info(
            "Intent detector initialized: %d/%d prototypes cached",
            cached,
            total_prototypes,
        )

    async def detect_intent(self, query: str) -> dict[str, Any]:
        """Detect intent from query using semantic similarity.

        Args:
            query: The user's query text.

        Returns:
            Dictionary with detected intent filters:
            - domain: Optional domain filter (e.g., "light")
            - device_class: Optional device class filter (e.g., "temperature")
            - area: Optional area filter (e.g., "bedroom")
        """
        if not self._initialized:
            _LOGGER.warning("Intent detector not initialized, returning empty intent")
            return {}

        try:
            # Get embedding for the query
            query_embedding = await get_embedding_for_query(
                self.embedding_provider, query
            )
        except Exception as e:
            _LOGGER.warning("Failed to get query embedding for intent: %s", e)
            return {}

        # Find best matching intents for each type
        intent: dict[str, Any] = {}
        best_scores: dict[str, tuple[str, float]] = {}  # type -> (value, score)

        for cache_key, proto_embedding in self._prototype_cache.items():
            # Parse cache key: "intent_type:value:proto_query"
            parts = cache_key.split(":", 2)
            if len(parts) < 3:
                continue

            intent_type = parts[0]  # "domain", "device_class", "area"
            intent_value = parts[1]  # e.g., "temperature", "light", "bedroom"

            score = cosine_similarity(query_embedding, proto_embedding)

            if score >= INTENT_THRESHOLD:
                current_best = best_scores.get(intent_type)
                if current_best is None or score > current_best[1]:
                    best_scores[intent_type] = (intent_value, score)

        # Build result from best matches
        for intent_type, (value, score) in best_scores.items():
            intent[intent_type] = value
            _LOGGER.debug(
                "Detected intent %s=%s (score: %.3f)", intent_type, value, score
            )

        if intent:
            _LOGGER.info("Semantic intent detected: %s", intent)
        else:
            _LOGGER.debug("No semantic intent detected for query: %s", query[:50])

        return intent

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about the prototype cache."""
        return {
            "initialized": self._initialized,
            "cached_prototypes": len(self._prototype_cache),
            "intent_types": list(INTENT_PROTOTYPES.keys()),
        }
