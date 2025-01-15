"""Pure utility functions and data structures for the SQLite vector store.

Contains cosine similarity / distance, BM25 score normalization,
embedding blob serialization, metadata filtering, and the SearchResult dataclass.
No database dependencies -- these are pure functions.
"""

from __future__ import annotations

import json
import logging
import math
import struct
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a vector search."""

    id: str
    text: str
    metadata: dict[str, Any]
    distance: float


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine similarity score (0-1, higher is more similar).
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def bm25_rank_to_score(rank: float) -> float:
    """Convert SQLite FTS5 bm25() rank to a 0-1 score.

    SQLite's bm25() returns negative values where more-negative = better match.
    We normalize to [0, 1] using: score = 1 / (1 + abs(rank)).

    Unlike OpenClaw which clamps negative ranks to 0 (making all matches ~1.0),
    we use abs(rank) to preserve relative BM25 ordering in the score.
    This gives better differentiation in the hybrid merge.

    Args:
        rank: Raw bm25() value from SQLite FTS5 (typically negative).

    Returns:
        Normalized score in [0, 1] where 1.0 = best match.
    """
    if not math.isfinite(rank):
        return 0.001
    return 1.0 / (1.0 + abs(rank))


def cosine_distance(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine distance between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine distance (0-2, lower is more similar).
    """
    return 1.0 - cosine_similarity(vec1, vec2)


def embedding_to_blob(embedding: list[float]) -> bytes:
    """Convert embedding list to compact binary blob (float32).

    Args:
        embedding: List of float values.

    Returns:
        Binary blob (~3KB for 768-dim instead of ~6KB JSON).
    """
    return struct.pack(f"<{len(embedding)}f", *embedding)


def blob_to_embedding(blob: bytes) -> list[float]:
    """Convert binary blob back to embedding list.

    Args:
        blob: Binary blob of float32 values.

    Returns:
        List of float values.
    """
    count = len(blob) // 4  # 4 bytes per float32
    return list(struct.unpack(f"<{count}f", blob))


def read_embedding(raw: Any) -> list[float]:
    """Read an embedding from either BLOB (binary) or JSON (text) format.

    Supports both formats for backward compatibility during migration.
    BLOB is the preferred format; JSON is the legacy format.

    Args:
        raw: Raw value from SQLite -- bytes (blob) or str (JSON).

    Returns:
        List of float values.
    """
    if isinstance(raw, bytes):
        return blob_to_embedding(raw)
    if isinstance(raw, str):
        return json.loads(raw)
    # Fallback: try to interpret as something reasonable
    _LOGGER.warning(
        "Unexpected embedding type %s, attempting JSON parse", type(raw).__name__
    )
    return json.loads(str(raw))


def filter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Filter metadata to ensure JSON-serializable types.

    Args:
        metadata: Original metadata dictionary.

    Returns:
        Filtered metadata with only serializable types.
    """
    filtered = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            filtered[key] = value
        elif value is None:
            continue
        elif isinstance(value, (list, dict)):
            try:
                json.dumps(value)  # Test if serializable
                filtered[key] = value
            except (TypeError, ValueError):
                _LOGGER.debug("Skipping non-serializable metadata key: %s", key)
        else:
            filtered[key] = str(value)
    return filtered
