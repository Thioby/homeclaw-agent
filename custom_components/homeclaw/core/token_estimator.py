"""Token estimation and context budget utilities.

Provides heuristic-based token counting (chars/4) and context window
budget calculations for managing conversation history size.

No external dependencies — uses character-based approximation with a
configurable safety margin to avoid context overflow.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Default context window (tokens) when model config is unavailable
DEFAULT_CONTEXT_WINDOW = 128_000

# Reserve for LLM output generation
DEFAULT_OUTPUT_RESERVE = 8_192

# Safety margin to account for estimation inaccuracy (20%)
DEFAULT_SAFETY_MARGIN = 0.20

# Approximate characters per token (conservative for multilingual content)
CHARS_PER_TOKEN = 4

# Per-message overhead: role tag, separators, special tokens
MESSAGE_OVERHEAD_TOKENS = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using character heuristic.

    Uses ~4 characters per token, which is conservative enough for
    multilingual content (English averages ~4, Polish/CJK may be higher).

    Args:
        text: Input text to estimate.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate total tokens across a list of messages.

    Accounts for per-message overhead (role tags, separators).

    Args:
        messages: List of message dicts with at least a 'content' key.

    Returns:
        Estimated total token count.
    """
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        total += estimate_tokens(content) + MESSAGE_OVERHEAD_TOKENS
    return total


def compute_context_budget(
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    output_reserve: int = DEFAULT_OUTPUT_RESERVE,
    safety_margin: float = DEFAULT_SAFETY_MARGIN,
) -> dict[str, int]:
    """Compute how many tokens are available for input (history + system prompt).

    Args:
        context_window: Total context window of the model in tokens.
        output_reserve: Tokens reserved for LLM response generation.
        safety_margin: Fraction of context window kept as safety buffer.

    Returns:
        Dict with:
            - total: Full context window.
            - available_for_input: Tokens usable for system prompt + history + query.
            - output_reserve: Tokens reserved for output.
            - safety_buffer: Tokens held back as safety margin.
    """
    safety_buffer = int(context_window * safety_margin)
    available = context_window - output_reserve - safety_buffer
    # Ensure we never go negative
    available = max(available, 0)

    return {
        "total": context_window,
        "available_for_input": available,
        "output_reserve": output_reserve,
        "safety_buffer": safety_buffer,
    }
