"""Temporal hint detection for RAG query expansion.

Provides a cheap regex pre-filter to avoid unnecessary LLM calls
for time-range expansion when a query has no temporal cues.
"""

from __future__ import annotations

import re

# Cheap regex pre-filter — skip LLM time-range expansion when query has no temporal cues.
# NOTE: Polish "po" is intentionally NOT a standalone token here (too many false positives
# like "po prostu", "po co"). Instead we use specific temporal collocations.
_TEMPORAL_PATTERN = re.compile(
    r"\b("
    r"yesterday|today|tonight|tomorrow|last\s+(?:week|month|year|night|time|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|this\s+(?:week|month|year|morning|evening)"
    r"|ago|recent(?:ly)?|earlier|before|after|since|until"
    r"|wczoraj|dzisiaj|dzi[sś]|jutro|zesz[łl](?:y|ego|ej|ym)"
    r"|ostatni(?:o|ch|m|ego|ej)?|temu|niedawno|rano|wieczorem|przed"
    r"|po\s+(?:godzinie|dniu|tygodniu|miesi[aą]cu|roku|po[lł]udniu)"
    r"|od\s+kiedy|od\s+(?:wczoraj|rana|tygodnia|miesi[aą]ca)"
    r"|\d{4}[-/]\d{2}(?:[-/]\d{2})?"
    r")\b",
    re.IGNORECASE,
)


def has_temporal_hint(query: str) -> bool:
    """Check if a query contains temporal keywords worth expanding via LLM.

    Args:
        query: The user's query text.

    Returns:
        True if the query contains temporal cues.
    """
    return bool(_TEMPORAL_PATTERN.search(query))
