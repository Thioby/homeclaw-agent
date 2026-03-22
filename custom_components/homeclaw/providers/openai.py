"""OpenAI provider implementation."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from ..core.tool_call_codec import extract_tool_calls_from_assistant_content
from .base_client import BaseHTTPClient
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@ProviderRegistry.register("openai")
class OpenAIProvider(BaseHTTPClient):
    """OpenAI API provider.

    This provider implements the OpenAI chat completions API with support
    for tool/function calling.
    """

    API_URL = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the OpenAI provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration dictionary. Expected keys:
                - token: OpenAI API key (required)
                - model: Model name (optional, defaults to gpt-4o)
        """
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._token = config.get("token", "")

    @property
    def api_url(self) -> str:
        """Return the OpenAI API endpoint URL.

        Returns:
            The OpenAI chat completions endpoint URL.
        """
        return self.API_URL

    @property
    def supports_tools(self) -> bool:
        """Return whether this provider supports tool/function calling.

        Returns:
            True, as OpenAI supports tool calling.
        """
        return True

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for OpenAI API requests.

        Returns:
            Dictionary with Authorization and Content-Type headers.
        """
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _convert_multimodal_messages(
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert messages with _images to OpenAI multimodal content blocks.

        Transforms our internal format into OpenAI's vision API format:
        content: [{"type":"text","text":"..."}, {"type":"image_url","image_url":{"url":"data:..."}}]
        """
        converted = []
        for msg in messages:
            images = msg.get("_images")
            if images and msg.get("role") == "user":
                content_blocks: list[dict[str, Any]] = [
                    {"type": "text", "text": msg.get("content", "")},
                ]
                for img in images:
                    data_url = f"data:{img['mime_type']};base64,{img['data']}"
                    content_blocks.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "auto"},
                        }
                    )
                converted.append({"role": "user", "content": content_blocks})
            else:
                # Strip _images key from non-image messages
                clean = {k: v for k, v in msg.items() if k != "_images"}

                # Convert canonical assistant tool-call JSON into OpenAI tool_calls.
                if (
                    clean.get("role") == "assistant"
                    and isinstance(clean.get("content"), str)
                    and clean.get("content")
                ):
                    try:
                        parsed_content = json.loads(clean["content"])
                        if isinstance(parsed_content, dict):
                            calls = extract_tool_calls_from_assistant_content(
                                parsed_content
                            )
                            if calls:
                                clean = {
                                    "role": "assistant",
                                    "content": parsed_content.get("text", ""),
                                    "tool_calls": [
                                        {
                                            "id": call.get("id", ""),
                                            "type": "function",
                                            "function": {
                                                "name": call.get("name", ""),
                                                "arguments": json.dumps(
                                                    call.get("args", {})
                                                ),
                                            },
                                        }
                                        for call in calls
                                    ],
                                }
                    except (TypeError, ValueError, json.JSONDecodeError):
                        pass

                converted.append(clean)
        return converted

    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Build the request payload for OpenAI API.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments. Supports:
                - tools: List of tool definitions for function calling.

        Returns:
            The request payload dictionary.
        """
        # Convert multimodal messages to OpenAI format
        converted_messages = self._convert_multimodal_messages(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": converted_messages,
        }

        # Add tools if provided
        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = tools

        return payload

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from OpenAI API response.

        Handles both regular text responses and tool call responses.

        Args:
            response_data: The parsed JSON response from the OpenAI API.

        Returns:
            The extracted response text, or a JSON string with tool calls
            if the response contains tool_calls.
        """
        choices = response_data.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message", {})

        # Check for tool calls
        tool_calls = message.get("tool_calls")
        if tool_calls:
            return json.dumps({"tool_calls": tool_calls})

        # Return regular content
        content = message.get("content")
        return content if content is not None else ""

    @staticmethod
    def _extract_openai_stream_chunks(
        event_data: dict[str, Any],
        pending_tools: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert one OpenAI SSE event into normalized chunks.

        Args:
            event_data: Parsed JSON from one SSE data line.
            pending_tools: Mutable dict accumulating partial tool calls by index.

        Returns:
            List of normalized chunks (text/tool_call).
        """
        output: list[dict[str, Any]] = []
        choices = event_data.get("choices", [])
        if not choices:
            return output

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        # Text delta
        content = delta.get("content")
        if content:
            output.append({"type": "text", "content": content})

        # Tool call deltas – accumulate fragments
        tool_calls = delta.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                index = tc.get("index", 0)
                if index not in pending_tools:
                    pending_tools[index] = {
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": "",
                    }
                else:
                    # Merge incremental data
                    if tc.get("id"):
                        pending_tools[index]["id"] = tc["id"]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        pending_tools[index]["name"] = fn["name"]

                args_fragment = tc.get("function", {}).get("arguments", "")
                if args_fragment:
                    pending_tools[index]["arguments"] += args_fragment

        # Flush pending tools on any terminal finish_reason (tool_calls, stop, length, content_filter)
        if finish_reason is not None and pending_tools:
            for idx in sorted(pending_tools):
                tool = pending_tools[idx]
                try:
                    args = json.loads(tool["arguments"]) if tool["arguments"] else {}
                except (json.JSONDecodeError, TypeError, ValueError):
                    _LOGGER.warning(
                        "Failed to parse tool call arguments for %s", tool["name"]
                    )
                    args = {}
                output.append({
                    "type": "tool_call",
                    "name": tool["name"],
                    "args": args,
                    "id": tool["id"],
                })
            pending_tools.clear()

        return output

    async def get_response_stream(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response chunks from OpenAI-compatible chat completions API.

        Yields normalized chunks consumed by stream_loop:
        - {"type": "text", "content": "..."}
        - {"type": "tool_call", "name": str, "args": dict, "id": str}
        - {"type": "error", "message": str}
        """
        headers = self._build_headers()
        payload = self._build_payload(messages, **kwargs)
        payload["stream"] = True

        pending_tools: dict[int, dict[str, Any]] = {}
        buffer = ""

        try:
            async with self.session.post(
                self.api_url,
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "OpenAI streaming request failed: status=%d body=%s",
                        response.status,
                        error_text[:500],
                    )
                    yield {
                        "type": "error",
                        "message": f"OpenAI API error {response.status}: {error_text[:200]}",
                    }
                    return

                done = False
                async for raw_chunk in response.content.iter_any():
                    if done:
                        break
                    if not raw_chunk:
                        continue

                    buffer += raw_chunk.decode("utf-8", errors="ignore")

                    while "\n\n" in buffer:
                        raw_event, buffer = buffer.split("\n\n", 1)
                        if not raw_event.strip():
                            continue

                        data_lines: list[str] = []
                        for line in raw_event.splitlines():
                            if line.startswith("data:"):
                                data_lines.append(line[5:].strip())

                        if not data_lines:
                            continue

                        data_text = "\n".join(data_lines)
                        if data_text == "[DONE]":
                            done = True
                            break

                        try:
                            event_data = json.loads(data_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            _LOGGER.debug(
                                "Skipping unparsable OpenAI stream event: %s",
                                data_text[:200],
                            )
                            continue

                        for out_chunk in self._extract_openai_stream_chunks(
                            event_data, pending_tools
                        ):
                            yield out_chunk

                # Flush remaining buffer at stream end
                if buffer.strip():
                    for raw_event in buffer.strip().split("\n\n"):
                        data_lines = [
                            line[5:].strip()
                            for line in raw_event.splitlines()
                            if line.startswith("data:")
                        ]
                        if not data_lines:
                            continue
                        data_text = "\n".join(data_lines)
                        if data_text == "[DONE]":
                            break
                        try:
                            event_data = json.loads(data_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            continue
                        for out_chunk in self._extract_openai_stream_chunks(
                            event_data, pending_tools
                        ):
                            yield out_chunk

                # Safety flush: emit any remaining pending tool calls (no finish_reason received)
                if pending_tools:
                    _LOGGER.warning(
                        "Safety flush: emitting %d pending tool calls without finish_reason",
                        len(pending_tools),
                    )
                    for idx in sorted(pending_tools):
                        tool = pending_tools[idx]
                        try:
                            args = json.loads(tool["arguments"]) if tool["arguments"] else {}
                        except (json.JSONDecodeError, TypeError, ValueError):
                            args = {}
                        yield {
                            "type": "tool_call",
                            "name": tool["name"],
                            "args": args,
                            "id": tool["id"],
                        }
                    pending_tools.clear()

        except Exception:
            _LOGGER.exception("Error during OpenAI streaming")
            yield {"type": "error", "message": "OpenAI streaming connection error"}
