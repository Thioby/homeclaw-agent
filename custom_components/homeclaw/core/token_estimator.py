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

# Approximate characters per token.
# 3 is conservative enough for multilingual content (Polish/CJK ~2.5-3.5,
# English ~3.5-4). Previous value of 4 underestimated for non-English text.
CHARS_PER_TOKEN = 3

# Per-message overhead: role tag, separators, special tokens
MESSAGE_OVERHEAD_TOKENS = 4

# Estimated overhead for tool schemas (function declarations) in the context.
# Each tool definition ≈ 200-500 tokens. With 12-20 tools loaded, this is
# 2,400-10,000 tokens that are NOT counted by estimate_messages_tokens().
# This reserve is subtracted from available budget as a conservative estimate.
TOOL_SCHEMA_RESERVE_TOKENS = 5_000


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using character heuristic.

    Uses ~3 characters per token, which is conservative for multilingual
    content (Polish/CJK ~2.5-3.5, English ~3.5-4).

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


def estimate_total_tokens(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> int:
    """Estimate total tokens including messages AND tool schemas.

    Tool definitions consume context window tokens but were previously
    not counted, leading to underestimation of 2,400-6,000 tokens.

    Args:
        messages: List of message dicts.
        tools: Optional list of tool definitions in OpenAI format.

    Returns:
        Estimated total token count for messages + tool schemas.
    """
    import json

    msg_tokens = estimate_messages_tokens(messages)
    tool_tokens = 0
    if tools:
        for tool in tools:
            tool_json = json.dumps(tool, ensure_ascii=False)
            tool_tokens += estimate_tokens(tool_json)
    return msg_tokens + tool_tokens


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
    available = context_window - output_reserve - safety_buffer - TOOL_SCHEMA_RESERVE_TOKENS
    # Ensure we never go negative
    available = max(available, 0)

    return {
        "total": context_window,
        "available_for_input": available,
        "output_reserve": output_reserve,
        "safety_buffer": safety_buffer,
    }
