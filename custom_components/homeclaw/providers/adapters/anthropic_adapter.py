"""Anthropic format adapter shared by API-key and OAuth Anthropic providers."""

from __future__ import annotations

import json
import logging
from typing import Any

from ...core.tool_call_codec import extract_tool_calls_from_assistant_content
from .base import ProviderAdapter
from .stream_utils import ToolAccumulator

_LOGGER = logging.getLogger(__name__)


class AnthropicAdapter(ProviderAdapter):
    """Converts between canonical (OpenAI) message format and Anthropic API format.

    Shared by AnthropicProvider (API key) and AnthropicOAuthProvider.
    """

    # ------------------------------------------------------------------
    # transform_tools
    # ------------------------------------------------------------------

    def transform_tools(
        self, openai_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool schemas to Anthropic input_schema format.

        OpenAI:  {"type":"function","function":{"name":...,"description":...,"parameters":{...}}}
        Anthropic: {"name":...,"description":...,"input_schema":{...}}
        """
        if not openai_tools:
            return []

        result: list[dict[str, Any]] = []
        for tool in openai_tools:
            if tool.get("type") != "function":
                continue
            fn = tool.get("function", {})
            result.append(
                {
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {}),
                }
            )
        return result

    # ------------------------------------------------------------------
    # transform_messages
    # ------------------------------------------------------------------

    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert canonical messages to Anthropic format and extract system content.

        Returns:
            (anthropic_messages, system_content)
        """
        system_content: str | None = None
        converted: list[dict[str, Any]] = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "system":
                system_content = content or None
                continue

            if role == "function":
                # Tool result — must be wrapped in tool_result block inside user message.
                tool_use_id = message.get("tool_use_id")
                if not tool_use_id:
                    _LOGGER.warning(
                        "Skipping function message without tool_use_id for tool '%s'",
                        message.get("name", "unknown"),
                    )
                    continue
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": content,
                            }
                        ],
                    }
                )
                continue

            if role == "assistant":
                if not content:
                    # Drop empty assistant messages.
                    continue
                # Try to parse as tool-call JSON.
                try:
                    parsed = json.loads(content)
                    tool_blocks = self._build_tool_use_blocks(parsed)
                    if tool_blocks:
                        converted.append({"role": "assistant", "content": tool_blocks})
                        continue
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
                converted.append({"role": "assistant", "content": content})
                continue

            if role == "user":
                images = message.get("_images")
                if images:
                    blocks: list[dict[str, Any]] = [{"type": "text", "text": content}]
                    for img in images:
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img["mime_type"],
                                    "data": img["data"],
                                },
                            }
                        )
                    converted.append({"role": "user", "content": blocks})
                    continue
                if not content:
                    continue
                converted.append({"role": "user", "content": content})
                continue

            # Any other role — pass through if non-empty.
            if content:
                converted.append({"role": role, "content": content})

        return converted, system_content

    @staticmethod
    def _build_tool_use_blocks(parsed: dict[str, Any]) -> list[dict[str, Any]]:
        """Return Anthropic tool_use content blocks from a parsed assistant payload."""
        calls = extract_tool_calls_from_assistant_content(parsed)
        if not calls:
            return []
        return [
            {
                "type": "tool_use",
                "id": call["id"],
                "name": call["name"],
                "input": call["args"],
            }
            for call in calls
        ]

    @staticmethod
    def format_response_as_legacy_string(parsed: dict[str, Any]) -> str:
        """Convert canonical extract_response() output to legacy JSON string.

        Providers return str from get_response(). This converts the adapter's
        canonical dict back to the JSON format that FunctionCallParser expects.
        """
        if parsed["type"] == "tool_calls":
            tool_calls = parsed["tool_calls"]
            result: dict[str, Any] = {
                "tool_use": {
                    "id": tool_calls[0]["id"],
                    "name": tool_calls[0]["name"],
                    "input": tool_calls[0]["args"],
                }
            }
            if parsed.get("text"):
                result["text"] = parsed["text"]
            if len(tool_calls) > 1:
                result["additional_tool_calls"] = [
                    {"id": tc["id"], "name": tc["name"], "input": tc["args"]}
                    for tc in tool_calls[1:]
                ]
            return json.dumps(result)
        return parsed.get("content", "")

    # ------------------------------------------------------------------
    # extract_response
    # ------------------------------------------------------------------

    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        """Parse an Anthropic response into canonical format.

        Returns:
            {"type":"text","content":str,"finish_reason":"stop"}
            or {"type":"tool_calls","tool_calls":[...],"text":str|None,"finish_reason":"tool_calls"}
        """
        content_blocks: list[dict[str, Any]] = raw_response.get("content", [])

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in content_blocks:
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "args": block.get("input", {}),
                    }
                )

        if tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": tool_calls,
                "text": "".join(text_parts) if text_parts else None,
                "finish_reason": "tool_calls",
            }

        return {
            "type": "text",
            "content": "".join(text_parts),
            "finish_reason": "stop",
        }

    # ------------------------------------------------------------------
    # extract_stream_events
    # ------------------------------------------------------------------

    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: ToolAccumulator
    ) -> list[dict[str, Any]]:
        """Normalize a single Anthropic stream event into canonical chunks.

        Args:
            event_data: Parsed JSON from one SSE event.
            tool_acc: ToolAccumulator for collecting partial tool call fragments.

        Returns:
            List of normalized chunks:
            - {"type": "text", "content": str}
            - {"type": "tool_call", "id": str, "name": str, "args": dict}
        """
        event_type = event_data.get("type", "")

        if event_type == "content_block_start":
            block = event_data.get("content_block", {})
            if block.get("type") == "tool_use":
                index = int(event_data.get("index", 0))
                # Register with empty args_delta — DO NOT serialize {} from start input,
                # as that would break JSON concatenation when input_json_delta arrives.
                tool_acc.add_fragment(
                    index, block.get("id", ""), block.get("name", ""), ""
                )
            return []

        if event_type == "content_block_delta":
            delta = event_data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    return [{"type": "text", "content": text}]
                return []

            if delta_type == "input_json_delta":
                index = int(event_data.get("index", 0))
                partial = delta.get("partial_json", "")
                tool_acc.add_fragment(index, None, None, partial)
                return []

            return []

        if event_type in {"message_delta", "message_stop"}:
            if not tool_acc.has_pending:
                return []
            flushed = tool_acc.flush_all()
            return [
                {
                    "type": "tool_call",
                    "id": tc["id"],
                    "name": tc["name"],
                    "args": tc["args"],
                }
                for tc in flushed
            ]

        return []
