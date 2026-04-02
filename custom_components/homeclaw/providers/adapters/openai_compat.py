"""OpenAI-compatible adapter for format conversion.

Handles OpenAI, Groq, OpenRouter, z.ai, Xiaomi, and Llama providers
that all speak the OpenAI chat-completions wire format.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...core.tool_call_codec import extract_tool_calls_from_assistant_content
from .base import ProviderAdapter

_LOGGER = logging.getLogger(__name__)


class OpenAICompatAdapter(ProviderAdapter):
    """Adapter for the OpenAI chat-completions wire format.

    Tools are already in OpenAI format so most transforms are trivial.
    The main work is:
    - Converting user _images to multimodal content blocks.
    - Converting canonical assistant tool-call JSON to OpenAI tool_calls.
    - Parsing tool_calls from non-streaming and streaming responses.
    """

    # ------------------------------------------------------------------
    # transform_tools
    # ------------------------------------------------------------------

    def transform_tools(self, openai_tools: list[dict[str, Any]]) -> Any:
        """Passthrough — tools are already in OpenAI format."""
        return openai_tools

    # ------------------------------------------------------------------
    # transform_messages
    # ------------------------------------------------------------------

    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert canonical messages to OpenAI wire format.

        - User messages with _images → multimodal content blocks.
        - Assistant messages with canonical tool-call JSON → tool_calls field.
        - Strip _images from all messages.
        - Return (converted, None) — OpenAI keeps system messages inline.
        """
        converted: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            images: list[dict[str, Any]] = msg.get("_images", [])

            # Build a clean copy without _images
            new_msg: dict[str, Any] = {k: v for k, v in msg.items() if k != "_images"}

            if role == "user" and images:
                # Convert to multimodal content blocks
                blocks: list[dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for img in images:
                    mime = img.get("mime_type", "image/jpeg")
                    data = img.get("data", "")
                    blocks.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{data}",
                                "detail": "auto",
                            },
                        }
                    )
                new_msg["content"] = blocks

            elif role == "assistant" and isinstance(content, str):
                # Try to parse canonical tool-call JSON
                tool_calls = _extract_openai_tool_calls(content)
                if tool_calls is not None:
                    new_msg["tool_calls"] = tool_calls
                    # Preserve any plain-text portion (not present in canonical JSON)
                    new_msg["content"] = None

            elif role == "function":
                # Convert canonical tool result to OpenAI tool format
                new_msg = {
                    "role": "tool",
                    "content": content,
                    "tool_call_id": msg.get("tool_use_id") or msg.get("name", "unknown"),
                }

            converted.append(new_msg)

        return converted, None

    # ------------------------------------------------------------------
    # extract_response
    # ------------------------------------------------------------------

    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        """Parse a non-streaming OpenAI API response.

        Returns:
            {"type": "text", "content": str, "finish_reason": str}
            or {"type": "tool_calls", "tool_calls": [...], "text": str | None, "finish_reason": "tool_calls"}
        """
        choices = raw_response.get("choices", [])
        if not choices:
            return {"type": "text", "content": "", "finish_reason": ""}

        choice = choices[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "") or ""
        content: str = message.get("content") or ""
        raw_tool_calls: list[dict[str, Any]] | None = message.get("tool_calls")

        if raw_tool_calls:
            tool_calls: list[dict[str, Any]] = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                raw_args = func.get("arguments", "{}")
                try:
                    args = (
                        json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    )
                except (json.JSONDecodeError, TypeError):
                    args = {}

                tool_calls.append(
                    {
                        "id": str(tc.get("id", "") or ""),
                        "name": func.get("name", ""),
                        "args": args if isinstance(args, dict) else {},
                    }
                )

            return {
                "type": "tool_calls",
                "tool_calls": tool_calls,
                "text": content or None,
                "finish_reason": "tool_calls",
            }

        return {"type": "text", "content": content, "finish_reason": finish_reason}

    # ------------------------------------------------------------------
    # extract_stream_events
    # ------------------------------------------------------------------

    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: Any
    ) -> list[dict[str, Any]]:
        """Normalize a single SSE event into canonical chunks.

        Args:
            event_data: Parsed JSON from one SSE event.
            tool_acc: ToolAccumulator for collecting partial tool calls.

        Returns:
            List of {"type": "text", "content": str}
            or {"type": "tool_call", "id": str, "name": str, "args": dict}
        """
        choices = event_data.get("choices", [])
        if not choices:
            return []

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        chunks: list[dict[str, Any]] = []

        # Text delta
        text_content = delta.get("content")
        if text_content:
            chunks.append({"type": "text", "content": text_content})

        # Tool call fragments
        delta_tool_calls: list[dict[str, Any]] | None = delta.get("tool_calls")
        if delta_tool_calls:
            for fragment in delta_tool_calls:
                index: int = fragment.get("index", 0)
                tc_id: str | None = fragment.get("id")
                func = fragment.get("function", {})
                name: str | None = func.get("name")
                args_delta: str = func.get("arguments", "")
                tool_acc.add_fragment(index, tc_id, name, args_delta)

        # Flush on finish
        if finish_reason is not None and tool_acc.has_pending:
            for tc in tool_acc.flush_all():
                chunks.append(
                    {
                        "type": "tool_call",
                        "id": tc["id"],
                        "name": tc["name"],
                        "args": tc["args"],
                    }
                )

        return chunks


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_openai_tool_calls(content: str) -> list[dict[str, Any]] | None:
    """Try to extract OpenAI tool_calls from canonical assistant JSON content.

    Returns a list of OpenAI-format tool_call dicts, or None if content
    is not a canonical tool-call payload.
    """
    if not content or not content.strip().startswith("{"):
        return None

    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(parsed, dict):
        return None

    calls = extract_tool_calls_from_assistant_content(parsed)
    if not calls:
        return None

    return [
        {
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["name"],
                "arguments": json.dumps(tc["args"]),
            },
        }
        for tc in calls
    ]
