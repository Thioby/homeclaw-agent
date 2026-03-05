"""Context and message building for AI agent interactions.

Assembles system prompts, conversation history, RAG context, and repairs
tool call/result pairs.  Extracted from QueryProcessor.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from .compaction import compact_messages, truncation_fallback
from .token_estimator import (
    DEFAULT_CONTEXT_WINDOW,
    compute_context_budget,
    estimate_messages_tokens,
)

if TYPE_CHECKING:
    from ..providers.registry import AIProvider

_LOGGER = logging.getLogger(__name__)


async def build_messages(
    query: str,
    history: list[dict[str, Any]],
    provider: AIProvider,
    detect_function_call_fn: Any,
    system_prompt: str | None = None,
    rag_context: str | None = None,
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], bool]:
    """Build the message list for the AI provider.

    Assembles system prompt, conversation history, and the current query
    into a flat list.  Triggers compaction when over context budget.

    Returns:
        Tuple of (messages, was_compacted_boolean).
    """
    messages: list[dict[str, Any]] = []

    # Build system prompt with RAG context if available
    final_system_prompt = system_prompt or ""

    if rag_context:
        rag_section = (
            "\n\n--- RELEVANT CONTEXT ---\n"
            f"{rag_context}\n"
            "--- END CONTEXT ---\n\n"
            "The above context may include relevant_entities, previous_conversations, "
            "and long_term_memories. Use available tools "
            "(get_entities_by_domain, get_state, etc.) to find other entities if needed."
        )
        final_system_prompt = (
            final_system_prompt + rag_section if final_system_prompt else rag_section
        )
        _LOGGER.info("RAG context added to system prompt (%d chars)", len(rag_context))
        _LOGGER.debug("RAG context FULL: %s", rag_context)
        _LOGGER.debug("Final system prompt length: %d chars", len(final_system_prompt))

    # Add system prompt first if we have one
    if final_system_prompt:
        messages.append({"role": "system", "content": final_system_prompt})

    # Add conversation history
    messages.extend(history)

    # --- Process attachments into the user message ---
    attachments = kwargs.pop("attachments", None)
    enriched_query = query
    image_attachments: list[dict[str, Any]] = []

    if attachments:
        from ..file_processor import get_image_base64

        text_parts: list[str] = []
        for att in attachments:
            if att.is_image:
                b64 = get_image_base64(att)
                if b64:
                    image_attachments.append(
                        {
                            "mime_type": att.mime_type,
                            "data": b64,
                            "filename": att.filename,
                        }
                    )
            elif att.content_text:
                text_parts.append(
                    f"--- Attached file: {att.filename} ---\n"
                    f"{att.content_text}\n"
                    f"--- End of {att.filename} ---"
                )

        if text_parts:
            enriched_query = query + "\n\n" + "\n\n".join(text_parts)
            _LOGGER.info(
                "Enriched query with %d text attachment(s), total %d chars",
                len(text_parts),
                len(enriched_query),
            )

    # Build the user message (multimodal or plain text)
    if image_attachments:
        messages.append(
            {"role": "user", "content": enriched_query, "_images": image_attachments}
        )
        _LOGGER.info(
            "Built multimodal user message with %d image(s)", len(image_attachments)
        )
    else:
        messages.append({"role": "user", "content": enriched_query})

    # --- Context window compaction ---
    context_window = kwargs.get("context_window", DEFAULT_CONTEXT_WINDOW)
    memory_flush_fn = kwargs.get("memory_flush_fn")
    user_id = kwargs.get("user_id")
    session_id = kwargs.get("session_id", "")

    provider_kwargs: dict[str, Any] = {}
    if kwargs.get("model"):
        provider_kwargs["model"] = kwargs["model"]

    pre_compaction_messages = messages

    compacted_messages = await compact_messages(
        messages,
        context_window=context_window,
        provider=provider,
        memory_flush_fn=memory_flush_fn,
        user_id=user_id,
        session_id=session_id,
        **provider_kwargs,
    )

    was_compacted = compacted_messages is not pre_compaction_messages

    from ..tools.base import ToolRegistry

    known_tools = {
        t.id for t in ToolRegistry.get_all_tools(hass=None, enabled_only=True)
    }
    final_messages = repair_tool_history(
        compacted_messages, detect_function_call_fn, allowed_tool_names=known_tools
    )

    return final_messages, was_compacted


def repair_tool_history(
    messages: list[dict[str, Any]],
    detect_function_call_fn: Any,
    allowed_tool_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Repair tool/function call history to ensure perfect pairs.

    Fixes missing tool_use_ids, drops orphan results, and injects
    synthetic results for unfinished tool calls.
    """
    sanitized: list[dict[str, Any]] = []
    pending_tool_calls: dict[str, str] = {}  # id -> name

    for msg in messages:
        role = msg.get("role")
        if role in ("system", "user"):
            sanitized.append(msg)
            continue

        if role == "assistant":
            content = msg.get("content", "")

            # Check text-encoded first
            try:
                fcs = detect_function_call_fn(content)
                if fcs:
                    for fc in fcs:
                        if allowed_tool_names is None or fc.name in allowed_tool_names:
                            pending_tool_calls[fc.id] = fc.name
                        else:
                            _LOGGER.warning("Dropped unknown tool call: %s", fc.name)
            except Exception:
                pass

            # Check standard JSON formats
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    tc_id = tc.get("id") or tc.get("function", {}).get(
                        "name", "unknown"
                    )
                    tc_name = tc.get("function", {}).get("name", "unknown")
                    if allowed_tool_names is None or tc_name in allowed_tool_names:
                        pending_tool_calls[tc_id] = tc_name
                    else:
                        _LOGGER.warning("Dropped unknown tool call: %s", tc_name)
            elif "function_call" in msg:
                fc_data = msg["function_call"]
                tc_id = msg.get("tool_use_id") or fc_data.get("name", "unknown")
                tc_name = fc_data.get("name", "unknown")
                if allowed_tool_names is None or tc_name in allowed_tool_names:
                    pending_tool_calls[tc_id] = tc_name
                else:
                    _LOGGER.warning("Dropped unknown tool call: %s", tc_name)

            sanitized.append(msg)

        elif role in ("function", "tool"):
            tc_id = msg.get("tool_use_id") or msg.get("id") or msg.get("name")
            if tc_id in pending_tool_calls:
                msg_copy = dict(msg)
                msg_copy["tool_use_id"] = tc_id
                sanitized.append(msg_copy)
                del pending_tool_calls[tc_id]
            else:
                _LOGGER.warning(
                    "Removed orphan or duplicate tool result from history (id: %s)",
                    tc_id,
                )

    # Close any pending tool calls that never got a result
    for tc_id, tc_name in pending_tool_calls.items():
        _LOGGER.warning(
            "Injected synthetic result for unmatched tool call %s (%s)", tc_name, tc_id
        )
        sanitized.append(
            {
                "role": "function",
                "name": tc_name,
                "tool_use_id": tc_id,
                "content": json.dumps(
                    {"error": "tool result missing from conversation history"}
                ),
            }
        )

    return sanitized


async def recompact_if_needed(
    messages: list[dict[str, Any]],
    *,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
) -> list[dict[str, Any]]:
    """Trim messages if tool results pushed us over the context budget.

    Only truncates long tool result contents to avoid discarding
    tool call/result pairs that the model needs.
    """
    budget = compute_context_budget(context_window)
    available = budget["available_for_input"]
    estimated = estimate_messages_tokens(messages)

    if estimated <= available:
        return messages

    _LOGGER.warning(
        "Tool loop re-compaction: %d tokens > %d budget, truncating tool results",
        estimated,
        available,
    )

    MAX_TOOL_RESULT_CHARS = 2000
    MIN_TOOL_RESULT_CHARS = 200

    result = list(messages)
    limit = MAX_TOOL_RESULT_CHARS

    while limit >= MIN_TOOL_RESULT_CHARS:
        for msg in result:
            role = msg.get("role", "")
            if role in ("tool", "function"):
                content = msg.get("content", "")
                if len(content) > limit:
                    half = limit // 2
                    msg["content"] = (
                        content[:half]
                        + "\n\n... [truncated — showing first and last portion] ...\n\n"
                        + content[-half:]
                    )
        estimated = estimate_messages_tokens(result)
        if estimated <= available:
            _LOGGER.info(
                "Tool result truncation brought tokens to %d (budget %d, limit %d chars)",
                estimated,
                available,
                limit,
            )
            return result
        limit //= 2

    _LOGGER.warning(
        "Tool result truncation insufficient (%d > %d), falling back to message trimming",
        estimated,
        available,
    )
    return truncation_fallback(result, available)
