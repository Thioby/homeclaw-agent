"""OpenAI provider implementation."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from .adapters.openai_compat import OpenAICompatAdapter
from .adapters.stream_utils import SSEParser, ToolAccumulator
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
        self.adapter = OpenAICompatAdapter()

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
        converted_messages, _ = self.adapter.transform_messages(messages)

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
        result = self.adapter.extract_response(response_data)

        if result["type"] == "tool_calls":
            # Return raw OpenAI tool_calls for backward compat
            return json.dumps(
                {"tool_calls": response_data["choices"][0]["message"]["tool_calls"]}
            )

        return result["content"] if result.get("content") else ""

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

                    text = raw_chunk.decode("utf-8", errors="ignore")
                    for event_text in sse_parser.feed(text):
                        if event_text == "[DONE]":
                            done = True
                            break
                        try:
                            event_data = json.loads(event_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            _LOGGER.debug(
                                "Skipping unparsable OpenAI stream event: %s",
                                event_text[:200],
                            )
                            continue

                        for chunk in self.adapter.extract_stream_events(
                            event_data, tool_acc
                        ):
                            yield chunk

                # Flush remaining buffer
                for event_text in sse_parser.flush():
                    if event_text == "[DONE]":
                        break
                    try:
                        event_data = json.loads(event_text)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
                    for chunk in self.adapter.extract_stream_events(
                        event_data, tool_acc
                    ):
                        yield chunk

                # Safety flush: emit any remaining pending tool calls (no finish_reason received)
                if tool_acc.has_pending:
                    _LOGGER.warning(
                        "Safety flush: emitting %d pending tool calls without finish_reason",
                        len(tool_acc._calls),
                    )
                    for tool in tool_acc.flush_all():
                        yield {"type": "tool_call", **tool}

        except Exception:
            _LOGGER.exception("Error during OpenAI streaming")
            yield {"type": "error", "message": "OpenAI streaming connection error"}
