"""Anthropic AI provider implementation."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from .base_client import BaseHTTPClient
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@ProviderRegistry.register("anthropic")
class AnthropicProvider(BaseHTTPClient):
    """Anthropic Claude AI provider.

    This provider implements the Anthropic Messages API for Claude models.
    It handles the conversion between OpenAI-style messages and Anthropic's
    format, including system message extraction and tool format conversion.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the Anthropic provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration dictionary containing:
                - api_key: Anthropic API key
                - model: Model name (optional, defaults to claude-sonnet-4-20250514)
                - max_tokens: Maximum tokens in response (optional, defaults to 4096)
        """
        super().__init__(hass, config)
        self._api_key = config.get("api_key", "")
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._max_tokens = config.get("max_tokens", self.DEFAULT_MAX_TOKENS)

    @property
    def supports_tools(self) -> bool:
        """Return whether this provider supports tool/function calling.

        Returns:
            True - Anthropic Claude supports native function calling.
        """
        return True

    @property
    def api_url(self) -> str:
        """Return the API endpoint URL.

        Returns:
            The Anthropic Messages API endpoint URL.
        """
        return self.API_URL

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for the Anthropic API request.

        Returns:
            Dictionary of HTTP headers including x-api-key and anthropic-version.
        """
        return {
            "x-api-key": self._api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _extract_system(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Extract system message and convert messages for Anthropic format.

        Anthropic requires:
        - System message passed separately
        - Tool results as 'user' role with tool_result content blocks
        - Assistant messages with tool_use preserved

        Args:
            messages: List of message dictionaries with role and content.

        Returns:
            A tuple of (filtered_messages, system_content) where:
            - filtered_messages: Messages in Anthropic format
            - system_content: The system message content, or None if not present
        """
        system_content: str | None = None
        filtered_messages: list[dict[str, Any]] = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "system":
                system_content = content
            elif role == "function":
                # Tool result - Anthropic uses tool_result in user role
                tool_use_id = message.get("tool_use_id", message.get("name", ""))
                filtered_messages.append(
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
            elif role == "assistant" and content:
                # Check if this contains tool_use JSON
                try:
                    parsed = json.loads(content)
                    if "tool_use" in parsed:
                        tool_use = parsed["tool_use"]
                        filtered_messages.append(
                            {
                                "role": "assistant",
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "id": tool_use.get("id", ""),
                                        "name": tool_use.get("name", ""),
                                        "input": tool_use.get("input", {}),
                                    }
                                ],
                            }
                        )
                        continue
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
                filtered_messages.append({"role": role, "content": content})
            elif role == "user" and message.get("_images"):
                # Multimodal user message with images
                content_blocks: list[dict[str, Any]] = [
                    {"type": "text", "text": content},
                ]
                for img in message["_images"]:
                    content_blocks.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": img["mime_type"],
                                "data": img["data"],
                            },
                        }
                    )
                filtered_messages.append({"role": "user", "content": content_blocks})
            elif content:
                filtered_messages.append({"role": role, "content": content})

        return filtered_messages, system_content

    def _convert_tools(
        self, openai_tools: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic input_schema format.

        OpenAI format:
            {"type": "function", "function": {"name": ..., "parameters": ...}}

        Anthropic format:
            {"name": ..., "description": ..., "input_schema": ...}

        Args:
            openai_tools: List of tools in OpenAI format, or None.

        Returns:
            List of tools in Anthropic format.
        """
        if not openai_tools:
            return []

        anthropic_tools: list[dict[str, Any]] = []

        for tool in openai_tools:
            if tool.get("type") == "function":
                function_def = tool.get("function", {})
                anthropic_tool = {
                    "name": function_def.get("name", ""),
                    "description": function_def.get("description", ""),
                    "input_schema": function_def.get("parameters", {}),
                }
                anthropic_tools.append(anthropic_tool)

        return anthropic_tools

    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Build the request payload for the Anthropic API.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments including:
                - tools: List of tools in OpenAI format

        Returns:
            The request payload dictionary for Anthropic's Messages API.
        """
        filtered_messages, system_content = self._extract_system(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": filtered_messages,
        }

        # Add system message if present (Anthropic requires it separately)
        if system_content:
            payload["system"] = system_content

        # Convert and add tools if provided
        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = self._convert_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        return payload

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from the Anthropic API response.

        Anthropic returns content as an array of content blocks, where each
        block can be of type "text" or "tool_use". This method extracts the
        text content and handles tool use blocks appropriately.

        Args:
            response_data: The parsed JSON response from the Anthropic API.

        Returns:
            The extracted response text or a JSON representation for tool calls.
        """
        content_blocks = response_data.get("content", [])

        if not content_blocks:
            return ""

        # Separate text blocks from tool_use blocks
        text_parts = []
        tool_use_blocks = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_use_blocks.append(block)

        if tool_use_blocks:
            # Return structured JSON with tool_use separated from text
            result: dict[str, Any] = {
                "tool_use": {
                    "id": tool_use_blocks[0].get("id"),
                    "name": tool_use_blocks[0].get("name"),
                    "input": tool_use_blocks[0].get("input"),
                }
            }
            if text_parts:
                result["text"] = " ".join(text_parts)
            if len(tool_use_blocks) > 1:
                result["additional_tool_calls"] = [
                    {
                        "id": tb.get("id"),
                        "name": tb.get("name"),
                        "input": tb.get("input"),
                    }
                    for tb in tool_use_blocks[1:]
                ]
            return json.dumps(result)

        return " ".join(text_parts) if text_parts else ""

    @staticmethod
    def _build_tool_call_chunk(
        tool_state: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Build a tool_call chunk from accumulated streaming state."""
        name = tool_state.get("name", "")
        if not name:
            return None

        args: dict[str, Any] = {}

        # Some streams provide complete input up-front in content_block_start.
        start_input = tool_state.get("input")
        if isinstance(start_input, dict):
            args = start_input
        else:
            # Otherwise accumulate partial_json from input_json_delta events.
            input_json = "".join(tool_state.get("input_json_parts", []))
            if input_json:
                try:
                    parsed = json.loads(input_json)
                    if isinstance(parsed, dict):
                        args = parsed
                    else:
                        _LOGGER.debug(
                            "Anthropic tool input parsed to non-dict: %s", parsed
                        )
                except (TypeError, ValueError, json.JSONDecodeError):
                    _LOGGER.warning(
                        "Failed to parse Anthropic tool input JSON for %s", name
                    )

        return {
            "type": "tool_call",
            "name": name,
            "args": args,
            "id": tool_state.get("id", ""),
        }

    def _extract_stream_chunks(
        self,
        event_data: dict[str, Any],
        pending_tools: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert one Anthropic stream event into normalized chunks."""
        output: list[dict[str, Any]] = []
        event_type = event_data.get("type", "")

        if event_type == "content_block_start":
            block = event_data.get("content_block", {})
            if block.get("type") == "tool_use":
                index = int(event_data.get("index", 0))
                pending_tools[index] = {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input"),
                    "input_json_parts": [],
                }
            return output

        if event_type == "content_block_delta":
            delta = event_data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    output.append({"type": "text", "content": text})
                return output

            if delta_type == "input_json_delta":
                index = int(event_data.get("index", 0))
                tool_state = pending_tools.setdefault(
                    index,
                    {
                        "id": "",
                        "name": "",
                        "input": None,
                        "input_json_parts": [],
                    },
                )
                partial_json = delta.get("partial_json", "")
                if partial_json:
                    tool_state["input_json_parts"].append(partial_json)
                return output

        # On message stop, flush pending tool calls once.
        if event_type in {"message_delta", "message_stop"}:
            for index in sorted(pending_tools):
                chunk = self._build_tool_call_chunk(pending_tools[index])
                if chunk:
                    output.append(chunk)
            pending_tools.clear()

        return output

    async def get_response_stream(self, messages: list[dict[str, Any]], **kwargs: Any):
        """Stream response chunks from Anthropic Messages API.

        Yields normalized chunks consumed by QueryProcessor:
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
                        "Anthropic streaming request failed: status=%d body=%s",
                        response.status,
                        error_text[:500],
                    )
                    yield {
                        "type": "error",
                        "message": f"Anthropic API error {response.status}: {error_text[:200]}",
                    }
                    return

                async for raw_chunk in response.content.iter_any():
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
                            break

                        try:
                            event_data = json.loads(data_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            _LOGGER.debug(
                                "Skipping unparsable Anthropic stream event: %s",
                                data_text[:200],
                            )
                            continue

                        for out_chunk in self._extract_stream_chunks(
                            event_data, pending_tools
                        ):
                            yield out_chunk

                # Flush remaining event data at stream end.
                if buffer.strip():
                    for raw_event in buffer.strip().split("\n\n"):
                        data_lines = [
                            line[5:].strip()
                            for line in raw_event.splitlines()
                            if line.startswith("data:")
                        ]
                        if not data_lines:
                            continue
                        try:
                            event_data = json.loads("\n".join(data_lines))
                        except (TypeError, ValueError, json.JSONDecodeError):
                            continue
                        for out_chunk in self._extract_stream_chunks(
                            event_data, pending_tools
                        ):
                            yield out_chunk

                # Safety flush in case stream ended without message_stop.
                if pending_tools:
                    for index in sorted(pending_tools):
                        chunk = self._build_tool_call_chunk(pending_tools[index])
                        if chunk:
                            yield chunk

        except Exception as err:
            _LOGGER.error("Anthropic streaming exception: %s", err)
            yield {"type": "error", "message": str(err)}
