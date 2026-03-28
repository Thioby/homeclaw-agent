"""Gemini adapter: converts between canonical (OpenAI) format and Gemini API format."""

from __future__ import annotations

import logging
from typing import Any

from .._gemini_convert import convert_messages, convert_tools, process_gemini_chunk
from .base import ProviderAdapter

_LOGGER = logging.getLogger(__name__)


class GeminiAdapter(ProviderAdapter):
    """Provider adapter for the Gemini API (shared by API-key and OAuth providers)."""

    def transform_tools(
        self, openai_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool schemas to Gemini functionDeclarations format."""
        return convert_tools(openai_tools)

    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert canonical messages to Gemini contents + system instruction."""
        return convert_messages(messages)

    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        """Parse a complete Gemini API response into canonical format.

        Handles:
        - text parts -> concatenated text response
        - functionCall parts -> tool_calls response
        - thought parts (thought: True) -> skipped
        - thoughtSignature and _raw_function_call -> preserved on tool calls
        - empty candidates -> empty text response
        """
        candidates = raw_response.get("candidates", [])
        if not candidates:
            return {"type": "text", "content": "", "finish_reason": "stop"}

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for part in parts:
            # Skip thinking parts emitted by Gemini thinking models
            if part.get("thought"):
                _LOGGER.debug("extract_response: skipping thought part")
                continue

            if "functionCall" in part:
                func_call = part["functionCall"]
                name = func_call.get("name", "unknown")
                tc: dict[str, Any] = {
                    "id": f"gemini_{name}",
                    "name": name,
                    "args": func_call.get("args", {}),
                    "_raw_function_call": part,
                }
                thought_sig = part.get("thoughtSignature")
                if thought_sig is not None:
                    tc["thought_signature"] = thought_sig
                tool_calls.append(tc)
            elif "text" in part:
                text_parts.append(part["text"])

        accumulated_text = "".join(text_parts) if text_parts else None

        if tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": tool_calls,
                "text": accumulated_text,
                "finish_reason": "tool_calls",
            }

        return {
            "type": "text",
            "content": accumulated_text or "",
            "finish_reason": "stop",
        }

    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: Any
    ) -> list[dict[str, Any]]:
        """Parse a single Gemini stream chunk into normalized events.

        Delegates to process_gemini_chunk(). Gemini sends complete tool calls
        in single chunks, so tool_acc is accepted for interface consistency
        but is not used.
        """
        return process_gemini_chunk(event_data)
