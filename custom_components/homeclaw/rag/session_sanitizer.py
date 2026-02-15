"""Session sanitizer — removes ephemeral state data from sessions before RAG indexing.

Uses an LLM to intelligently extract only durable, valuable context from
conversation history (preferences, decisions, actions performed) while
stripping out all ephemeral entity state data (sensor readings, on/off
status reports, current temperatures, etc.).

Triggered when a user creates a new session — the previous session is
sanitized and then indexed into the RAG session store.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# System prompt for LLM-based session sanitization
SESSION_SANITIZE_PROMPT = """\
You are a session memory curator for a Home Assistant AI assistant.

Your task: Given a conversation between User and Assistant, produce a CLEANED
version that preserves ONLY durable, reusable context. Remove all ephemeral
state information that changes over time.

CRITICAL RULE — LANGUAGE PRESERVATION:
Write the output in the SAME LANGUAGE as the input. If Polish, output Polish.
If English, output English. NEVER translate.

KEEP (durable context):
- User preferences and intentions ("I like warm light", "set bedroom to 22")
- Decisions made ("let's use automation X for this")
- Actions performed and their outcomes ("I created automation Y", "renamed entity Z")
- Entity names, IDs, locations, and relationships
- Configuration changes and setup instructions
- User corrections and feedback about the assistant's behavior
- Anything the user explicitly asked to remember

REMOVE (ephemeral state — changes constantly):
- All sensor readings: temperatures, humidity, power, energy, lux, etc.
- All entity state reports: "the light is on", "door is open", "22.5 C"
- Status check answers: "currently X shows Y", "temperature is Z"
- Lists of entity states or device statuses
- Real-time data that will be outdated within minutes

OUTPUT FORMAT:
- Produce a cleaned conversation in the same User:/Assistant: format
- If an entire Assistant turn is purely a state report, replace it with
  a brief note: "Assistant: [provided status information]"
- If a turn mixes durable info with state data, keep only the durable parts
- Keep User turns mostly intact (they show intent)
- Output ONLY the cleaned conversation, no commentary or headers"""

# Maximum characters to send per LLM call
MAX_INPUT_CHARS = 12_000


async def sanitize_session_messages(
    messages: list[dict[str, str]],
    provider: Any,
    model: str | None = None,
) -> list[dict[str, str]]:
    """Sanitize session messages using LLM to remove ephemeral state data.

    Takes raw conversation messages and produces a cleaned version where
    sensor readings, entity states, and other ephemeral data are stripped,
    preserving only user preferences, decisions, and durable context.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
            Only 'user' and 'assistant' roles are processed.
        provider: AI provider instance with get_response() method.
        model: Optional model override. Uses provider default if None.

    Returns:
        Cleaned message list in the same format, suitable for session indexing.
        On failure, returns the original messages unchanged.
    """
    # Filter to user/assistant only
    relevant = [
        m
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
    ]

    if len(relevant) < 2:
        _LOGGER.debug(
            "Too few messages (%d) to sanitize, returning as-is", len(relevant)
        )
        return relevant

    # Format conversation for LLM
    conversation_text = _format_conversation(relevant)

    # Truncate if too long — process only the most recent portion
    if len(conversation_text) > MAX_INPUT_CHARS:
        _LOGGER.debug(
            "Conversation too long (%d chars), truncating to last %d chars",
            len(conversation_text),
            MAX_INPUT_CHARS,
        )
        conversation_text = conversation_text[-MAX_INPUT_CHARS:]

    # Call LLM for sanitization
    try:
        llm_messages = [
            {"role": "system", "content": SESSION_SANITIZE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Clean this conversation by removing all ephemeral state data:\n\n"
                    f"{conversation_text}"
                ),
            },
        ]

        kwargs: dict[str, Any] = {}
        if model:
            kwargs["model"] = model

        response = await provider.get_response(llm_messages, **kwargs)

        if not response or not response.strip():
            _LOGGER.warning("Empty response from sanitization LLM, returning originals")
            return relevant

        # Parse LLM output back into message dicts
        sanitized = _parse_sanitized_response(response)

        if not sanitized:
            _LOGGER.warning("Failed to parse sanitized response, returning originals")
            return relevant

        _LOGGER.info(
            "Session sanitized: %d messages -> %d cleaned messages (%d -> %d chars)",
            len(relevant),
            len(sanitized),
            len(conversation_text),
            sum(len(m.get("content", "")) for m in sanitized),
        )

        return sanitized

    except Exception as e:
        _LOGGER.warning("Session sanitization failed, returning originals: %s", e)
        return relevant


def _format_conversation(messages: list[dict[str, str]]) -> str:
    """Format messages into User:/Assistant: text block.

    Args:
        messages: List of message dicts with 'role' and 'content'.

    Returns:
        Formatted conversation string.
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "").strip()
        if not content:
            continue
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


def _parse_sanitized_response(response: str) -> list[dict[str, str]]:
    """Parse LLM sanitized output back into message dicts.

    Expects lines starting with "User:" or "Assistant:".
    Handles multi-line content by accumulating until the next role marker.

    Args:
        response: Raw LLM response text.

    Returns:
        List of message dicts with 'role' and 'content', or empty on failure.
    """
    messages: list[dict[str, str]] = []
    current_role: str | None = None
    current_lines: list[str] = []

    for line in response.strip().split("\n"):
        stripped = line.strip()

        # Detect role markers
        if stripped.startswith("User:"):
            # Flush previous
            if current_role and current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
            current_role = "user"
            current_lines = [stripped[5:].strip()]

        elif stripped.startswith("Assistant:"):
            # Flush previous
            if current_role and current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
            current_role = "assistant"
            current_lines = [stripped[10:].strip()]

        elif current_role:
            # Continuation of current message
            current_lines.append(line)

    # Flush last message
    if current_role and current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})

    return messages
