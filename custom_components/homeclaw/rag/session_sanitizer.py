"""Session sanitizer — removes ephemeral state data from sessions before RAG indexing.

Uses an LLM to intelligently extract durable context (preferences, decisions, actions)
and user facts, while stripping out ephemeral entity state data.
Formats the output as rounds with extracted facts for Key Expansion.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

SESSION_SANITIZE_PROMPT = """\
You are a session memory curator for a Home Assistant AI assistant.

Your task: Given a conversation between User and Assistant, parse it into discrete conversational rounds (one user message + one assistant response).
For each round:
1. Produce a CLEANED version of the text that preserves ONLY durable, reusable context. Remove ephemeral state (sensor readings, "light is on", etc.).
2. Extract USER FACTS: any personal information, life events, experience, and preferences related to the user mentioned in this round.

CRITICAL RULE — LANGUAGE PRESERVATION:
Write the output in the SAME LANGUAGE as the input. If Polish, output Polish. If English, output English. NEVER translate.

KEEP (durable context):
- User preferences ("I like warm light")
- Decisions made and actions performed ("I created automation Y")
- Entity names, locations, relationships

REMOVE (ephemeral state):
- Sensor readings (temperatures, humidity, etc.)
- Entity state reports ("door is open", "22.5 C")
- Status check answers

OUTPUT FORMAT:
You MUST output ONLY a valid JSON list of objects, with no markdown formatting blocks (like ```json), no headers, and no commentary.
Each object must have exactly these fields:
- "user_message": Cleaned user message string.
- "assistant_message": Cleaned assistant message string (or a brief note like "[provided status information]" if it was purely a state report).
- "user_facts": A single string containing all extracted facts for this round, separated by semicolons. If no facts, use an empty string.

Example Output:
[
  {
    "user_message": "Zapal światło w salonie na niebiesko, lubię ten kolor.",
    "assistant_message": "Jasne, włączyłem niebieskie światło.",
    "user_facts": "Lubi niebieski kolor światła w salonie"
  }
]
"""

MAX_INPUT_CHARS = 12_000

# Hard cap on characters per round in fallback mode.
# Must match session_indexer.MAX_ROUND_CHARS to prevent embedding failures.
MAX_ROUND_CHARS = 2000


async def sanitize_session_messages(
    messages: list[dict[str, Any]],
    provider: Any,
    model: str | None = None,
) -> list[dict[str, Any]]:
    """Sanitize session messages and extract user facts using LLM.

    Takes raw conversation messages and produces a list of cleaned rounds with facts.

    Args:
        messages: List of message dicts with 'role', 'content', and optionally 'timestamp'.
        provider: AI provider instance.
        model: Optional model override.

    Returns:
        List of dicts representing rounds, e.g.:
        [
            {
                "timestamp": "2024-03-10T12:00:00Z",
                "user_message": "...",
                "assistant_message": "...",
                "user_facts": "..."
            }
        ]
        On failure, returns empty list.
    """
    # Group into rounds first to preserve timestamps
    from ._round_utils import group_messages_into_rounds

    rounds = group_messages_into_rounds(messages)

    if not rounds:
        _LOGGER.debug("No complete rounds found to sanitize")
        return []

    def _fallback() -> list[dict[str, Any]]:
        # Fallback converts raw rounds to the expected indexer format without fact extraction.
        # Truncate messages to MAX_ROUND_CHARS to prevent downstream embedding failures.
        result = []
        for r in rounds:
            user_msg = r["user"]
            asst_msg = r["assistant"]
            total = len(user_msg) + len(asst_msg)
            if total > MAX_ROUND_CHARS:
                half = MAX_ROUND_CHARS // 2
                user_msg = user_msg[:half]
                asst_msg = asst_msg[:half]
            result.append(
                {
                    "timestamp": r["timestamp"],
                    "user_message": user_msg,
                    "assistant_message": asst_msg,
                    "user_facts": "",
                }
            )
        return result

    # Truncate by dropping older rounds
    if len(rounds) > 50:
        rounds = rounds[-50:]

    # Format for LLM
    lines = []
    for r in rounds:
        lines.append(f"User: {r['user']}\nAssistant: {r['assistant']}")

    conversation_text = "\n\n".join(lines)

    # Final length check just to be absolutely safe
    if len(conversation_text) > MAX_INPUT_CHARS:
        _LOGGER.debug("Conversation still too long, using fallback")
        return _fallback()

    try:
        llm_messages = [
            {"role": "system", "content": SESSION_SANITIZE_PROMPT},
            {
                "role": "user",
                "content": f"Clean this conversation and extract facts:\n\n{conversation_text}",
            },
        ]

        kwargs: dict[str, Any] = {}
        if model:
            kwargs["model"] = model

        response = await provider.get_response(llm_messages, **kwargs)

        if not response or not response.strip():
            _LOGGER.warning("Empty response from sanitization LLM")
            return _fallback()

        from ._llm_utils import parse_json_response

        parsed = parse_json_response(response)

        if not isinstance(parsed, list) or not parsed:
            _LOGGER.warning("Sanitization LLM did not return a valid non-empty list")
            return _fallback()

        if len(parsed) != len(rounds):
            _LOGGER.warning(
                "Sanitization LLM returned %d rounds, expected %d",
                len(parsed),
                len(rounds),
            )
            return _fallback()

        # Drop rounds where LLM returned empty messages (no durable content)
        parsed = [
            p
            for p in parsed
            if isinstance(p, dict)
            and (
                str(p.get("user_message") or "").strip()
                or str(p.get("assistant_message") or "").strip()
            )
        ]
        if not parsed:
            _LOGGER.debug("All sanitized rounds are empty, using fallback")
            return _fallback()

        # Align with timestamps (working backwards)
        result = []
        parsed_idx = len(parsed) - 1
        round_idx = len(rounds) - 1

        while parsed_idx >= 0 and round_idx >= 0:
            p = parsed[parsed_idx]
            r = rounds[round_idx]
            if not isinstance(p, dict):
                p = {}
            user_msg = p.get("user_message", "")
            user_msg = str(user_msg) if user_msg is not None else ""

            asst_msg = p.get("assistant_message", "")
            asst_msg = str(asst_msg) if asst_msg is not None else ""

            facts = p.get("user_facts", "")
            facts = str(facts) if facts is not None else ""

            result.insert(
                0,
                {
                    "timestamp": r["timestamp"],
                    "user_message": user_msg,
                    "assistant_message": asst_msg,
                    "user_facts": facts,
                },
            )
            parsed_idx -= 1
            round_idx -= 1

        # Drop rounds where LLM returned empty messages (no durable content)
        result = [
            r
            for r in result
            if r.get("user_message", "").strip()
            or r.get("assistant_message", "").strip()
        ]

        _LOGGER.info(
            "Session sanitized: %d rounds -> %d cleaned rounds with facts",
            len(rounds),
            len(result),
        )

        return result if result else _fallback()

    except Exception as e:
        _LOGGER.warning("Session sanitization failed: %s", e)
        return _fallback()
