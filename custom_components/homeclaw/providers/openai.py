"""OpenAI provider implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .base_client import BaseHTTPClient
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
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
