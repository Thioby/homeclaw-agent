"""Shared utilities for grouping flat messages into conversation rounds."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def group_messages_into_rounds(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Convert flat message list into user/assistant rounds.

    Groups consecutive user messages together, pairing them with the next
    assistant response to form a single round.

    Args:
        messages: Flat list of message dicts with 'role', 'content', and
                  optional 'timestamp' keys.

    Returns:
        List of round dicts with keys: 'timestamp', 'user', 'assistant'.
    """
    rounds: list[dict[str, str]] = []
    current_user_msgs: list[str] = []
    current_timestamp = ""

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if not content or role not in ("user", "assistant"):
            continue

        if role == "user":
            current_user_msgs.append(content)
            if not current_timestamp:
                current_timestamp = msg.get("timestamp") or ""
        elif role == "assistant" and current_user_msgs:
            rounds.append(
                {
                    "timestamp": current_timestamp or msg.get("timestamp") or "",
                    "user": "\n".join(current_user_msgs),
                    "assistant": content,
                }
            )
            current_user_msgs = []
            current_timestamp = ""

    # Warn about trailing user messages without an assistant response
    if current_user_msgs:
        _LOGGER.debug(
            "Dropping %d trailing user message(s) without assistant response",
            len(current_user_msgs),
        )

    return rounds
