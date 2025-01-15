"""Auto-capture mechanism for Long-Term Memory.

Handles ONLY explicit user commands like "remember", "zapamiętaj", "zapisz".
All other memory capture is handled by the LLM via the memory_store tool
(proactive capture during conversation) and AI-powered flush (pre-compaction).

This module is the safety net for when the user explicitly asks to remember
something — we detect the intent and store it even if the LLM forgets to
call memory_store.
"""

from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Maximum captures per conversation turn
MAX_CAPTURES_PER_TURN = 3

# Message length constraints for capture candidates
MIN_CAPTURE_LENGTH = 10
MAX_CAPTURE_LENGTH = 500

# Only explicit "remember this" commands — everything else is LLM-driven
EXPLICIT_COMMAND_PATTERN = re.compile(
    r"\b(remember|zapamiętaj|zapisz|save this|note that|zanotuj)\b",
    re.IGNORECASE,
)

# Patterns that indicate the text is NOT worth capturing
ANTI_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<relevant-memories>", re.IGNORECASE),
    re.compile(r"--- SUGGESTED ENTITIES ---", re.IGNORECASE),
    re.compile(r"^(yes|no|ok|sure|thanks|dzięki|tak|nie|dobra)$", re.IGNORECASE),
    re.compile(r"^\d+$"),
]


def is_explicit_command(text: str) -> bool:
    """Check if a message is an explicit "remember this" command.

    Args:
        text: Message text to evaluate.

    Returns:
        True if the text contains an explicit memory command.
    """
    if len(text) < MIN_CAPTURE_LENGTH or len(text) > MAX_CAPTURE_LENGTH:
        return False

    for pattern in ANTI_PATTERNS:
        if pattern.search(text):
            return False

    return bool(EXPLICIT_COMMAND_PATTERN.search(text))


def detect_category(text: str) -> str:
    """Detect the memory category from explicit command text.

    Args:
        text: Memory text to categorize.

    Returns:
        Category string.
    """
    text_lower = text.lower()

    if any(
        w in text_lower for w in ["prefer", "like", "love", "hate", "wolę", "lubię"]
    ):
        return "preference"

    if any(
        w in text_lower
        for w in ["decided", "agreed", "from now on", "od teraz", "zdecydował"]
    ):
        return "decision"

    if re.search(r"\S+@\S+\.\S+", text) or re.search(r"\+?\d{9,}", text):
        return "entity"

    if any(
        w in text_lower
        for w in [
            "today",
            "dzisiaj",
            "yesterday",
            "wczoraj",
            "tonight",
            "feeling",
            "czuję",
            "mood",
            "sleep",
            "spać",
        ]
    ):
        return "observation"

    return "fact"


def extract_explicit_commands(
    messages: list[dict[str, str]],
    max_captures: int = MAX_CAPTURES_PER_TURN,
) -> list[dict[str, Any]]:
    """Extract explicit "remember this" commands from messages.

    Only captures messages where the user explicitly asks to remember something.
    All other memory capture is delegated to the LLM via memory_store tool.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        max_captures: Maximum number of candidates to return.

    Returns:
        List of candidate dicts with 'text', 'category', 'importance', 'role'.
    """
    candidates = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role != "user":
            continue

        if not is_explicit_command(content):
            continue

        category = detect_category(content)
        # Explicit commands always get high importance
        importance = 0.9

        candidates.append(
            {
                "text": content,
                "category": category,
                "importance": importance,
                "role": role,
            }
        )

    return candidates[:max_captures]


# Backward compatibility — old name used by manager.py
extract_capture_candidates = extract_explicit_commands
