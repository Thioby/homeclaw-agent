"""Utilities for parsing LLM responses in RAG components."""

from __future__ import annotations

import json
import logging
import re

_LOGGER = logging.getLogger(__name__)

# Matches opening/closing markdown code fences (```json, ```, with optional whitespace)
_CODE_FENCE_RE = re.compile(r"^\s*```\w*\s*\n?", re.MULTILINE)
_CODE_FENCE_CLOSE_RE = re.compile(r"\n?\s*```\s*$", re.MULTILINE)


def parse_json_response(response: str) -> dict | list | None:
    """Safely extract and parse JSON from an LLM response.

    Handles markdown code blocks and free-form text around JSON.
    Falls back to ``raw_decode()`` if standard parsing fails.
    """
    if not response or not response.strip():
        return None

    cleaned = response.strip()

    # Strip opening code fence (handles ```json, ```JSON, ```, with leading whitespace)
    cleaned = _CODE_FENCE_RE.sub("", cleaned, count=1)

    # Strip closing code fence
    cleaned = _CODE_FENCE_CLOSE_RE.sub("", cleaned, count=1)

    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    # Fallback: search for first JSON object or array in raw text
    return _extract_first_json(cleaned)


def _extract_first_json(text: str) -> dict | list | None:
    """Extract the first JSON object or array from free-form text."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            try:
                obj, _ = decoder.raw_decode(text, i)
                return obj
            except json.JSONDecodeError:
                continue
    _LOGGER.debug("No JSON found in LLM response")
    return None
