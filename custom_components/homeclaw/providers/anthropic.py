"""Anthropic AI provider implementation."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from .adapters.anthropic_adapter import AnthropicAdapter
from .adapters.stream_utils import SSEParser, ToolAccumulator
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
        self.adapter = AnthropicAdapter()

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
        filtered_messages, system_content = self.adapter.transform_messages(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self.config.get("temperature", 0.2),
            "messages": filtered_messages,
        }

        # Add system message if present (Anthropic requires it separately)
        if system_content:
            payload["system"] = system_content

        # Convert and add tools if provided
        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = self.adapter.transform_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        return payload

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from the Anthropic API response.

        Uses the shared adapter to parse the response, then converts back to
        the string format expected by BaseHTTPClient callers:
        - Plain text string for text responses
        - JSON string with tool_use/additional_tool_calls for tool call responses

        Args:
            response_data: The parsed JSON response from the Anthropic API.

        Returns:
            The extracted response text or a JSON representation for tool calls.
        """
        parsed = self.adapter.extract_response(response_data)
        return self.adapter.format_response_as_legacy_string(parsed)

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

        sse_parser = SSEParser()
        tool_acc = ToolAccumulator()

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

                    for data_text in sse_parser.feed(
                        raw_chunk.decode("utf-8", errors="ignore")
                    ):
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

                        for out_chunk in self.adapter.extract_stream_events(
                            event_data, tool_acc
                        ):
                            yield out_chunk

                # Flush remaining buffer at stream end.
                for data_text in sse_parser.flush():
                    try:
                        event_data = json.loads(data_text)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
                    for out_chunk in self.adapter.extract_stream_events(
                        event_data, tool_acc
                    ):
                        yield out_chunk

                # Safety flush in case stream ended without message_stop.
                if tool_acc.has_pending:
                    for tc in tool_acc.flush_all():
                        yield {
                            "type": "tool_call",
                            "id": tc["id"],
                            "name": tc["name"],
                            "args": tc["args"],
                        }

        except Exception as err:
            _LOGGER.error("Anthropic streaming exception: %s", err)
            yield {"type": "error", "message": str(err)}
