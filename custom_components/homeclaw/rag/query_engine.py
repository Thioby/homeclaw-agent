"""Query engine for RAG system.

This module handles semantic search, keyword search (FTS5), hybrid merge,
and context compression for providing relevant entity information to the LLM.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from .sqlite_store import SqliteStore, SearchResult
from .embeddings import EmbeddingProvider, get_embedding_for_query

_LOGGER = logging.getLogger(__name__)

# Maximum context length to avoid token overflow
MAX_CONTEXT_LENGTH = 2000

# Hybrid search weights (must sum to 1.0)
HYBRID_VECTOR_WEIGHT = 0.7
HYBRID_TEXT_WEIGHT = 0.3

# Candidate multiplier: fetch N * multiplier from each subsystem, then merge to N
HYBRID_CANDIDATE_MULTIPLIER = 4


def build_fts_query(raw: str) -> str | None:
    """Build an FTS5 MATCH query from a raw user query string.

    Tokenizes the input, quotes each token for exact matching,
    and joins with AND so all tokens must be present.

    Handles entity_id-like patterns (e.g., "light.bedroom_lamp") by
    splitting on dots to produce both the full token and sub-tokens.

    Args:
        raw: Raw user query text.

    Returns:
        FTS5 query string (e.g., '"bedroom" AND "light"'), or None if no valid tokens.
    """
    # Extract alphanumeric + underscore tokens (same as OpenClaw)
    tokens = re.findall(r"[A-Za-z0-9_]+", raw)
    if not tokens:
        return None

    # Quote each token for exact-term matching, strip inner quotes for safety
    quoted = [f'"{t.replace(chr(34), "")}"' for t in tokens if t.strip()]
    if not quoted:
        return None

    return " AND ".join(quoted)


def merge_hybrid_results(
    vector_results: list[SearchResult],
    keyword_results: list[SearchResult],
    vector_weight: float = HYBRID_VECTOR_WEIGHT,
    text_weight: float = HYBRID_TEXT_WEIGHT,
) -> list[SearchResult]:
    """Merge vector search and keyword search results with weighted scoring.

    For each unique result, computes:
        final_score = vector_weight * vector_similarity + text_weight * text_score

    Where vector_similarity = 1 - distance and text_score = 1 - distance.
    Results appearing in only one set get 0 for the missing component.

    Args:
        vector_results: Results from vector (embedding) search.
        keyword_results: Results from FTS5 keyword search.
        vector_weight: Weight for vector similarity (default 0.7).
        text_weight: Weight for keyword/BM25 score (default 0.3).

    Returns:
        Merged, deduplicated results sorted by final score descending (best first).
        Distance field is set to (1 - final_score) for compatibility.
    """
    # Normalize weights to sum to 1.0
    total = vector_weight + text_weight
    if total > 0:
        vector_weight = vector_weight / total
        text_weight = text_weight / total

    # Build lookup by ID
    by_id: dict[str, dict[str, Any]] = {}

    # Add vector results
    for r in vector_results:
        vector_score = max(0.0, 1.0 - r.distance)
        by_id[r.id] = {
            "id": r.id,
            "text": r.text,
            "metadata": r.metadata,
            "vector_score": vector_score,
            "text_score": 0.0,
        }

    # Merge keyword results
    for r in keyword_results:
        text_score = max(0.0, 1.0 - r.distance)
        if r.id in by_id:
            by_id[r.id]["text_score"] = text_score
        else:
            by_id[r.id] = {
                "id": r.id,
                "text": r.text,
                "metadata": r.metadata,
                "vector_score": 0.0,
                "text_score": text_score,
            }

    # Compute final scores and build SearchResult objects
    merged = []
    for entry in by_id.values():
        final_score = (
            vector_weight * entry["vector_score"] + text_weight * entry["text_score"]
        )
        merged.append(
            SearchResult(
                id=entry["id"],
                text=entry["text"],
                metadata=entry["metadata"],
                distance=1.0 - final_score,  # Lower distance = better
            )
        )

    # Sort by distance ascending (best first)
    merged.sort(key=lambda x: x.distance)
    return merged


@dataclass
class QueryEngine:
    """Handles semantic search and context formatting.

    Searches for relevant entities and builds a compressed context
    string suitable for injection into the LLM prompt.
    """

    store: SqliteStore
    embedding_provider: EmbeddingProvider

    async def search_entities(
        self,
        query: str,
        top_k: int = 10,
        domain_filter: str | None = None,
        min_similarity: float | None = None,
    ) -> list[SearchResult]:
        """Search for entities semantically similar to the query.

        Args:
            query: The user's query text.
            top_k: Maximum number of results to return.
            domain_filter: Optional domain to filter by (e.g., "light").
            min_similarity: Minimum cosine similarity (0-1) for results.

        Returns:
            List of SearchResult objects sorted by relevance.
        """
        try:
            # Generate embedding for the query
            query_embedding = await get_embedding_for_query(
                self.embedding_provider, query
            )

            # Build filter if domain specified
            where_filter = None
            if domain_filter:
                where_filter = {"domain": domain_filter}

            # Search the vector store
            results = await self.store.search(
                query_embedding=query_embedding,
                n_results=top_k,
                where=where_filter,
                min_similarity=min_similarity,
            )

            _LOGGER.debug(
                "Search for '%s' returned %d results", query[:50], len(results)
            )
            if results:
                # Log found entity IDs for debugging
                entity_ids = [r.id for r in results[:5]]  # First 5
                _LOGGER.info(
                    "RAG search found entities: %s%s",
                    entity_ids,
                    f" (+{len(results) - 5} more)" if len(results) > 5 else "",
                )
            return results

        except Exception as e:
            _LOGGER.error("Entity search failed: %s", e)
            return []

    def build_compressed_context(
        self,
        results: list[SearchResult],
        max_length: int = MAX_CONTEXT_LENGTH,
    ) -> str:
        """Build a compressed context string from search results.

        Formats results into a compact representation that provides
        relevant entity information without wasting tokens.

        Args:
            results: Search results to format.
            max_length: Maximum character length for the context.

        Returns:
            Formatted context string.
        """
        if not results:
            return ""

        lines = []
        current_length = 0

        # Header - suggest entities but don't restrict LLM
        header = "Potentially relevant entities (use tools to find others if needed):"
        lines.append(header)
        current_length += len(header)

        for result in results:
            # Format each entity compactly
            line = self._format_entity(result)

            # Check if adding this line would exceed max length
            if current_length + len(line) + 1 > max_length:
                break

            lines.append(line)
            current_length += len(line) + 1  # +1 for newline

        return "\n".join(lines)

    def _format_entity(self, result: SearchResult) -> str:
        """Format a single entity result compactly.

        Args:
            result: The search result to format.

        Returns:
            Compact string representation.
        """
        metadata = result.metadata
        entity_id = result.id

        # Build compact representation
        parts = [f"- {entity_id}"]

        # Add friendly name if different from entity_id
        friendly_name = metadata.get("friendly_name")
        if friendly_name and friendly_name.lower() not in entity_id.lower():
            parts.append(f'"{friendly_name}"')

        # Add domain if not obvious from entity_id
        domain = metadata.get("domain")
        if domain:
            parts.append(f"({domain})")

        # Add area if available
        area_name = metadata.get("area_name")
        if area_name:
            parts.append(f"in {area_name}")

        # Add device class if useful
        device_class = metadata.get("device_class")
        if device_class and device_class != domain:
            parts.append(f"[{device_class}]")

        # Add learned category if available
        learned_cat = metadata.get("learned_category")
        if learned_cat:
            parts.append(f"<{learned_cat}>")

        # Add current state for actionable entities
        state = metadata.get("state")
        if state and domain in ("light", "switch", "cover", "lock", "fan"):
            parts.append(f"state:{state}")

        return " ".join(parts)

    async def search_and_format(
        self,
        query: str,
        top_k: int = 10,
        max_context_length: int = MAX_CONTEXT_LENGTH,
    ) -> str:
        """Search for entities and return formatted context.

        Convenience method that combines search and formatting.

        Args:
            query: The user's query text.
            top_k: Maximum number of results.
            max_context_length: Maximum context length.

        Returns:
            Formatted context string, or empty string if no results.
        """
        results = await self.search_entities(query, top_k)
        return self.build_compressed_context(results, max_context_length)

    async def search_by_criteria(
        self,
        query: str,
        domain: str | None = None,
        area: str | None = None,
        device_class: str | None = None,
        top_k: int = 10,
        min_similarity: float | None = None,
    ) -> list[SearchResult]:
        """Search with additional filter criteria.

        Args:
            query: The semantic query text.
            domain: Filter by domain (e.g., "light", "sensor").
            area: Filter by area name.
            device_class: Filter by device class.
            top_k: Maximum number of results.
            min_similarity: Minimum cosine similarity (0-1) for results.

        Returns:
            Filtered search results.
        """
        # Build the where filter
        where_filter: dict[str, Any] = {}

        if domain:
            where_filter["domain"] = domain
        if area:
            where_filter["area_name"] = area
        if device_class:
            where_filter["device_class"] = device_class

        try:
            query_embedding = await get_embedding_for_query(
                self.embedding_provider, query
            )

            return await self.store.search(
                query_embedding=query_embedding,
                n_results=top_k,
                where=where_filter if where_filter else None,
                min_similarity=min_similarity,
            )

        except Exception as e:
            _LOGGER.error("Filtered search failed: %s", e)
            return []

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        where: dict[str, Any] | None = None,
        min_similarity: float | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector similarity and FTS5 keyword search.

        Runs both searches in parallel, merges results with weighted scoring
        (0.7 vector + 0.3 keyword by default), deduplicates, and returns top_k.

        Falls back to vector-only search if FTS5 is not available or keyword
        search fails.

        Args:
            query: The user's query text.
            top_k: Maximum number of results to return.
            where: Optional metadata filter for vector search (simple equality).
            min_similarity: Minimum final score (0-1) for results.

        Returns:
            Merged, ranked list of SearchResult objects.
        """
        try:
            # Fetch more candidates than needed, then merge and trim
            candidates = min(200, max(1, top_k * HYBRID_CANDIDATE_MULTIPLIER))

            # 1. Vector search
            query_embedding = await get_embedding_for_query(
                self.embedding_provider, query
            )
            vector_results = await self.store.search(
                query_embedding=query_embedding,
                n_results=candidates,
                where=where,
            )

            # 2. Keyword search (FTS5) — graceful fallback on failure
            keyword_results: list[SearchResult] = []
            if self.store.fts_available:
                fts_query = build_fts_query(query)
                if fts_query:
                    keyword_results = await self.store.keyword_search(
                        fts_query=fts_query,
                        n_results=candidates,
                    )

            # 3. If no keyword results, return vector-only (apply min_similarity)
            if not keyword_results:
                if min_similarity is not None:
                    vector_results = [
                        r
                        for r in vector_results
                        if (1.0 - r.distance) >= min_similarity
                    ]
                _LOGGER.debug(
                    "Hybrid search (vector-only fallback): %d results for '%s'",
                    len(vector_results[:top_k]),
                    query[:50],
                )
                return vector_results[:top_k]

            # 4. Merge results
            merged = merge_hybrid_results(vector_results, keyword_results)

            # 5. Apply min_similarity threshold on merged scores
            if min_similarity is not None:
                merged = [r for r in merged if (1.0 - r.distance) >= min_similarity]

            result = merged[:top_k]

            _LOGGER.debug(
                "Hybrid search: %d vector + %d keyword -> %d merged for '%s'",
                len(vector_results),
                len(keyword_results),
                len(result),
                query[:50],
            )
            return result

        except Exception as e:
            _LOGGER.error("Hybrid search failed: %s", e)
            return []

    def extract_query_intent(self, query: str) -> dict[str, Any]:
        """Extract intent and filters from a natural language query.

        Simple rule-based extraction of common patterns like:
        - "lights in bedroom" → domain=light, area=bedroom
        - "temperature sensors" → domain=sensor, device_class=temperature

        Args:
            query: The user's query.

        Returns:
            Dictionary with extracted filters.
        """
        query_lower = query.lower()
        intent: dict[str, Any] = {}

        # Domain extraction (English + Polish)
        domain_keywords = {
            "light": [
                "light",
                "lamp",
                "bulb",
                "światło",
                "światła",
                "lampa",
                "lampy",
                "żarówka",
            ],
            "switch": [
                "switch",
                "outlet",
                "plug",
                "przełącznik",
                "gniazdko",
                "wtyczka",
            ],
            "sensor": [
                "sensor",
                "temperature",
                "humidity",
                "motion",
                "czujnik",
                "temperatura",
                "wilgotność",
                "ruch",
            ],
            "cover": [
                "cover",
                "blind",
                "curtain",
                "shade",
                "roleta",
                "zasłona",
                "żaluzja",
                "brama",
            ],
            "climate": [
                "climate",
                "thermostat",
                "hvac",
                "ac",
                "heating",
                "klimatyzacja",
                "termostat",
                "ogrzewanie",
            ],
            "lock": ["lock", "door lock", "zamek"],
            "fan": ["fan", "wentylator"],
            "media_player": [
                "media",
                "speaker",
                "tv",
                "television",
                "głośnik",
                "telewizor",
            ],
            "camera": ["camera", "kamera"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                intent["domain"] = domain
                break

        # Device class extraction (English + Polish)
        device_class_keywords = {
            "temperature": [
                "temperature",
                "temp",
                "temperatura",
                "temperatur",
                "stopni",
                "ciepło",
                "zimno",
            ],
            "humidity": ["humidity", "wilgotność", "wilgoć"],
            "motion": ["motion", "movement", "ruch", "ruchu"],
            "door": ["door", "drzwi"],
            "window": ["window", "okno", "okna"],
            "battery": ["battery", "bateria", "akumulator"],
            "power": ["power", "energy", "watt", "moc", "energia", "prąd", "zużycie"],
        }

        for device_class, keywords in device_class_keywords.items():
            if any(kw in query_lower for kw in keywords):
                intent["device_class"] = device_class
                break

        # Common room/area names (English + Polish)
        area_keywords = [
            "bedroom",
            "sypialnia",
            "living room",
            "salon",
            "pokój dzienny",
            "kitchen",
            "kuchnia",
            "bathroom",
            "łazienka",
            "office",
            "biuro",
            "gabinet",
            "garage",
            "garaż",
            "basement",
            "piwnica",
            "attic",
            "strych",
            "poddasze",
            "hallway",
            "korytarz",
            "przedpokój",
            "wiatrołap",
            "dining room",
            "jadalnia",
            "garden",
            "ogród",
            "patio",
            "taras",
            "backyard",
            "podwórko",
            "front yard",
            "pokój",
            "room",
        ]

        for area in area_keywords:
            if area in query_lower:
                intent["area"] = area
                break

        return intent
