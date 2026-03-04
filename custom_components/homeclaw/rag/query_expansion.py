"""Time-aware Query Expansion for RAG retrieval."""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

_LOGGER = logging.getLogger(__name__)

# LRU cache for temporal expansion results — avoids redundant LLM calls
# for repeated/similar queries within the same day.
_EXPANSION_CACHE: OrderedDict[str, tuple[str | None, str | None]] = OrderedDict()
_EXPANSION_CACHE_MAX = 64


def _cache_key(query: str) -> str:
    """Build a date-scoped cache key for a query."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return hashlib.blake2s(f"{today}:{query.strip().lower()}".encode()).hexdigest()


QUERY_EXPANSION_PROMPT = """\
You will be given a question from a human user asking about some previous events, as well as the current date.
Infer a potential time range such that the events happening in this range is likely to help to answer the question (a start date and an end date).
Write a JSON dict with two fields: "start" and "end".
Write the date in the form YYYY-MM-DD.
If the question does not have any temporal references, do not attempt to guess a time range. Instead, return {"start": "N/A", "end": "N/A"}.

Examples:

Current Date: 2023-05-28
Question: How long had I been taking guitar lessons when I bought the new guitar amp?
Response:
{
  "start": "N/A",
  "end": "N/A"
}

Current Date: 2023-04-27
Question: Which airline did I fly with the most in March and April?
Response:
{
  "start": "2023-03-01",
  "end": "2023-04-30"
}

Current Date: 2023-06-28
Question: How many days before the 'Rack Fest' did I participate in the 'Turbocharged Tuesdays' event?
Response:
{
  "start": "N/A",
  "end": "N/A"
}
"""


def _validate_date(date_str: str | None) -> str | None:
    """Validate date format is YYYY-MM-DD."""
    if date_str is None or date_str == "N/A":
        return None
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        return None


async def expand_query_time_range(
    query: str,
    provider: Any,
    model: str | None = None,
) -> tuple[str | None, str | None]:
    """Extract a time range from a user query using an LLM.

    IMPORTANT: This feature works best with strong models (e.g. GPT-4o,
    Claude 3.5 Sonnet).  Smaller models tend to hallucinate time ranges.

    Args:
        query: The user's query text.
        provider: AI provider instance.
        model: Optional model override (should be a strong model).

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format,
        or (None, None) if not applicable.  Partial ranges are valid
        (e.g. start without end means "from that date onward").
    """
    ck = _cache_key(query)
    if ck in _EXPANSION_CACHE:
        _EXPANSION_CACHE.move_to_end(ck)
        _LOGGER.debug("Query expansion cache hit for: %s", query[:50])
        return _EXPANSION_CACHE[ck]

    try:
        result = await _call_expander_llm(query, provider, model)

        # Cache valid results only — null results are NOT cached so the
        # same query can be retried immediately.
        if result != (None, None):
            _EXPANSION_CACHE[ck] = result
            if len(_EXPANSION_CACHE) > _EXPANSION_CACHE_MAX:
                _EXPANSION_CACHE.popitem(last=False)

        return result

    except Exception as e:
        _LOGGER.debug(
            "Time-aware query expansion failed (falling back to open search): %s", e
        )
        return None, None


async def _call_expander_llm(
    query: str,
    provider: Any,
    model: str | None,
) -> tuple[str | None, str | None]:
    """Send the expansion prompt to the LLM and parse the response."""
    now = datetime.now(timezone.utc)
    current_date_str = now.strftime("%Y-%m-%d")

    llm_messages = [
        {"role": "system", "content": QUERY_EXPANSION_PROMPT},
        {
            "role": "user",
            "content": f"Current Date: {current_date_str}\nQuestion: {query}",
        },
    ]

    kwargs: dict[str, Any] = {}
    if model:
        kwargs["model"] = model

    response = await provider.get_response(llm_messages, **kwargs)

    if not response or not response.strip():
        return None, None

    return _parse_expansion_result(response)


def _parse_expansion_result(response: str) -> tuple[str | None, str | None]:
    """Parse the LLM JSON response into a validated date-range tuple."""
    from ._llm_utils import parse_json_response

    parsed = parse_json_response(response)
    if not isinstance(parsed, dict):
        return None, None

    start = _validate_date(parsed.get("start"))
    end = _validate_date(parsed.get("end"))

    # Reject inverted ranges
    if start and end and start > end:
        _LOGGER.debug(
            "Query expansion returned inverted date range: %s to %s", start, end
        )
        return None, None

    # Accept partial ranges (start-only or end-only)
    if start or end:
        return start, end

    return None, None
