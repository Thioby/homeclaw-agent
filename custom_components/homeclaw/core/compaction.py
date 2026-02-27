"""Context window compaction for conversation history.

Implements AI-powered summarization of old messages when the conversation
history approaches the model's context window limit.  Inspired by OpenClaw's
adaptive compaction strategy.

Flow:
    1. Estimate tokens in the built message list.
    2. If within budget -> pass through unchanged.
    3. If over budget -> split into [old] + [recent].
    4. Memory flush: capture memorable facts from [old] messages.
    5. AI summarize [old] into a compact narrative.
    6. Return: [system] + [summary_as_system] + [recent] + [user_query].
    7. If still over budget -> truncation fallback.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from .token_estimator import (
    compute_context_budget,
    estimate_messages_tokens,
    estimate_tokens,
)

if TYPE_CHECKING:
    from ..providers.registry import AIProvider

_LOGGER = logging.getLogger(__name__)

# --- Configuration ---

# Trigger compaction when history exceeds this fraction of available budget
COMPACTION_TRIGGER_RATIO = 0.80

# Hard cap on effective context window (even for 1M+ models).
# Prevents "lost in the middle" effect where models lose attention to
# system prompt and tool instructions in very long contexts.
EFFECTIVE_MAX_CONTEXT = 128_000

# Maximum conversation turns before forced compaction.
# A "turn" = one user message (tool_use/tool_result don't count).
# Prevents context growth even when token budget isn't exceeded.
MAX_HISTORY_TURNS = 12

# Minimum recent messages to preserve (4 full turns with tool calls:
# each turn = user + assistant/tool + function + assistant/text = 4 messages)
MIN_RECENT_MESSAGES = 16

# Maximum compaction retry attempts (per query)
MAX_COMPACTION_ATTEMPTS = 3

# Max captures during memory flush (higher than normal turn capture)
MAX_FLUSH_CAPTURES = 10

# Summarization prompt — instructs the LLM to condense old conversation
COMPACTION_SYSTEM_PROMPT = (
    "You are a conversation summarizer. Condense the following conversation "
    "history into a concise narrative summary.\n\n"
    "RULES:\n"
    "1. LANGUAGE PRESERVATION: Output in the SAME language as the input. "
    "Never translate.\n"
    "2. PRESERVE all actionable information:\n"
    "   - Entity IDs (e.g. light.bedroom, sensor.temperature_living_room)\n"
    "   - Automation names and configurations\n"
    "   - User preferences and decisions\n"
    "   - Tool call results and outcomes\n"
    "   - Errors encountered and their resolutions\n"
    "   - Pending tasks or open questions\n"
    "3. DISCARD: greetings, filler, redundant confirmations, repeated context.\n"
    "4. Format: Dense but readable narrative. Max 500 words.\n"
    "5. Do NOT add commentary, headers, or meta-text. Just the summary."
)


async def compact_messages(
    messages: list[dict[str, Any]],
    *,
    context_window: int,
    provider: AIProvider,
    memory_flush_fn: Any | None = None,
    user_id: str | None = None,
    session_id: str = "",
    **provider_kwargs: Any,
) -> list[dict[str, Any]]:
    """Compact conversation history to fit within the context budget.

    If the messages already fit, returns them unchanged. Otherwise:
    1. Runs memory flush on messages about to be compacted.
    2. Summarizes old messages via the AI provider.
    3. Returns a trimmed message list with a summary injected.

    Args:
        messages: Full message list ([system] + history + [user_query]).
        context_window: Model's context window in tokens.
        provider: AI provider for summarization calls.
        memory_flush_fn: Optional async callable(messages, user_id, session_id)
            that captures facts from messages before they are discarded.
        user_id: User ID for memory flush scoping.
        session_id: Session ID for memory flush context.
        **provider_kwargs: Extra kwargs forwarded to the provider (e.g. model).

    Returns:
        Compacted message list that fits within the context budget.
    """
    # Apply effective context cap to prevent "lost in the middle" for large-window models
    effective_window = min(context_window, EFFECTIVE_MAX_CONTEXT)
    budget = compute_context_budget(effective_window)
    available = budget["available_for_input"]
    estimated = estimate_messages_tokens(messages)

    # Check turn-based trigger (count user messages in history, excluding system and current query)
    user_turn_count = sum(1 for m in messages if m.get("role") == "user")
    turn_triggered = user_turn_count > MAX_HISTORY_TURNS

    if not turn_triggered and estimated <= int(available * COMPACTION_TRIGGER_RATIO):
        return messages

    trigger_reason = "turn limit" if turn_triggered else "token budget"

    _LOGGER.info(
        "Context compaction triggered (%s): %d estimated tokens, budget %d (%.0f%% used), %d user turns",
        trigger_reason,
        estimated,
        available,
        (estimated / available * 100) if available else 100,
        user_turn_count,
    )

    # --- Split messages into segments ---
    # Extract system message (always first if present) and user query (always last).
    # Remaining messages form the history that may be compacted.
    system_msg = None
    user_query = None
    history: list[dict[str, Any]] = []

    if messages and messages[0].get("role") == "system":
        system_msg = messages[0]
        remaining = messages[1:]
    else:
        remaining = list(messages)

    if remaining and remaining[-1].get("role") == "user":
        user_query = remaining[-1]
        history = remaining[:-1]
    else:
        history = list(remaining)

    if len(history) <= MIN_RECENT_MESSAGES + 2:
        # Not enough history to meaningfully split into old + recent segments.
        # Need at least 2 "old" messages to justify an AI summarization call.
        _LOGGER.warning(
            "History too short for compaction (%d messages, need >%d), using truncation fallback",
            len(history),
            MIN_RECENT_MESSAGES + 2,
        )
        return truncation_fallback(messages, available)

    # Keep the most recent messages intact.
    # Find a safe split point (must start with a user message to not break tool sequences)
    split_point = max(0, len(history) - MIN_RECENT_MESSAGES)
    while split_point > 0 and history[split_point].get("role") != "user":
        split_point -= 1

    old_messages = history[:split_point]
    recent_messages = history[split_point:]

    # --- Phase 1: AI-powered memory flush ---
    if memory_flush_fn and user_id:
        try:
            captured = await memory_flush_fn(
                old_messages, user_id, session_id, provider=provider
            )
            if captured:
                _LOGGER.info(
                    "Memory flush captured %d memories before compaction", captured
                )
        except Exception as e:
            _LOGGER.debug("Memory flush failed (non-fatal): %s", e)

    # --- Phase 2: AI summarization ---
    summary_text = await _summarize_messages(old_messages, provider, **provider_kwargs)

    if not summary_text:
        _LOGGER.warning("Summarization failed, using truncation fallback")
        return truncation_fallback(messages, available)

    # --- Phase 3: Rebuild message list ---
    compacted: list[dict[str, Any]] = []

    if system_msg:
        compacted.append(system_msg)

    # Inject summary as a system-level context message.
    # Using "system" role so it does NOT count as a user turn for
    # turn-based compaction triggers (MAX_HISTORY_TURNS).
    compacted.append(
        {
            "role": "system",
            "content": f"[Previous conversation summary]\n{summary_text}",
        }
    )
    compacted.append(
        {
            "role": "assistant",
            "content": (
                "Understood. I have the summary of our earlier conversation.\n"
                "IMPORTANT: For all new requests, I MUST use my tools "
                "(call_service, get_entity_state, etc.) to interact with "
                "Home Assistant. I will NOT confirm actions without calling tools first."
            ),
        }
    )

    from ..tools.base import ToolRegistry

    registered_tool_names = sorted(
        tid for tid, tc in ToolRegistry._tools.items() if tc.enabled
    )
    if registered_tool_names:
        compacted.append(
            {
                "role": "system",
                "content": (
                    "[Post-compaction context refresh]\n"
                    f"Available tools: {', '.join(registered_tool_names)}"
                ),
            }
        )

    compacted.extend(recent_messages)

    if user_query:
        compacted.append(user_query)

    # --- Phase 4: Verify it fits ---
    new_estimated = estimate_messages_tokens(compacted)
    if new_estimated > available:
        _LOGGER.warning(
            "Compacted messages still over budget (%d > %d), applying truncation",
            new_estimated,
            available,
        )
        return truncation_fallback(compacted, available)

    _LOGGER.info(
        "Compaction complete: %d -> %d messages, %d -> %d estimated tokens",
        len(messages),
        len(compacted),
        estimated,
        new_estimated,
    )
    return compacted


async def _summarize_messages(
    messages: list[dict[str, Any]],
    provider: AIProvider,
    **provider_kwargs: Any,
) -> str | None:
    """Summarize a batch of messages using the AI provider.

    Args:
        messages: Messages to summarize.
        provider: AI provider to use.
        **provider_kwargs: Extra kwargs (e.g. model override).

    Returns:
        Summary text, or None on failure.
    """
    # Format messages for the summarization prompt
    formatted_lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # Truncate very long tool results
        if len(content) > 2000:
            content = content[:1800] + "\n... [truncated]"
        formatted_lines.append(f"[{role}]: {content}")

    conversation_text = "\n\n".join(formatted_lines)

    # Limit input to avoid blowing up the summarization call itself
    max_summary_input = 40_000  # chars (~10k tokens)
    if len(conversation_text) > max_summary_input:
        conversation_text = (
            conversation_text[:max_summary_input] + "\n\n... [truncated]"
        )

    summarize_messages = [
        {"role": "system", "content": COMPACTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Summarize this conversation ({len(messages)} messages):\n\n"
                f"{conversation_text}"
            ),
        },
    ]

    try:
        # Strip tools from kwargs — summarization doesn't need them
        clean_kwargs = {
            k: v for k, v in provider_kwargs.items() if k not in ("tools", "hass")
        }
        summary = await provider.get_response(summarize_messages, **clean_kwargs)
        if summary and len(summary.strip()) > 20:
            _LOGGER.debug("Summarization produced %d chars", len(summary))
            return summary.strip()
        _LOGGER.warning("Summarization returned empty or too short response")
        return None
    except Exception as e:
        _LOGGER.error("Summarization failed: %s", e)
        return None


def truncation_fallback(
    messages: list[dict[str, Any]],
    budget_tokens: int,
) -> list[dict[str, Any]]:
    """Last-resort truncation: keep system + recent messages within budget.

    Drops oldest non-system messages until the list fits.

    Args:
        messages: Message list to truncate.
        budget_tokens: Maximum token budget.

    Returns:
        Truncated message list.
    """
    if not messages:
        return messages

    # Always keep system message (first) and user query (last)
    system_msg = messages[0] if messages[0].get("role") == "system" else None
    user_query = messages[-1] if messages[-1].get("role") == "user" else None

    # Middle messages (history)
    start = 1 if system_msg else 0
    end = len(messages) - 1 if user_query else len(messages)
    history = list(messages[start:end])

    # Build from the end (keep most recent)
    result: list[dict[str, Any]] = []
    if system_msg:
        result.append(system_msg)

    # Calculate fixed token usage
    fixed_tokens = 0
    if system_msg:
        fixed_tokens += estimate_tokens(system_msg.get("content", "")) + 4
    if user_query:
        fixed_tokens += estimate_tokens(user_query.get("content", "")) + 4

    remaining_budget = budget_tokens - fixed_tokens
    kept: list[dict[str, Any]] = []

    # Iterate from most recent to oldest
    for msg in reversed(history):
        msg_tokens = estimate_tokens(msg.get("content", "")) + 4
        if remaining_budget - msg_tokens >= 0:
            kept.append(msg)
            remaining_budget -= msg_tokens
        else:
            break

    # Fix orphaned tool results/calls
    # kept[-1] is the oldest kept message (because it's populated from recent to oldest).
    # If it's a function/tool result, it means we dropped its accompanying assistant call.
    # We must drop the result too to preserve conversational logic.
    while kept and kept[-1].get("role") in ("function", "tool"):
        dropped = kept.pop()
        _LOGGER.debug(
            "Dropped orphaned tool result during truncation: %s",
            dropped.get("name", "unknown"),
        )

    kept.reverse()
    result.extend(kept)

    if user_query:
        result.append(user_query)

    _LOGGER.info(
        "Truncation fallback: kept %d of %d history messages",
        len(kept),
        len(history),
    )
    return result
