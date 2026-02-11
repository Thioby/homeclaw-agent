"""OpenRouter provider implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .base_client import BaseHTTPClient
from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@ProviderRegistry.register("openrouter")
class OpenRouterProvider(BaseHTTPClient):
    """OpenRouter API provider.

    This provider implements the OpenRouter API which is OpenAI-compatible.
    OpenRouter provides access to multiple AI models through a unified API.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "openai/gpt-4o"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the OpenRouter provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration dictionary. Expected keys:
                - token: OpenRouter API key (required)
                - model: Model name (optional, defaults to openai/gpt-4o)
        """
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._token = config.get("token", "")

    @property
    def api_url(self) -> str:
        """Return the OpenRouter API endpoint URL.

        Returns:
            The OpenRouter chat completions endpoint URL.
        """
        return self.API_URL

    @property
    def supports_tools(self) -> bool:
        """Return whether this provider supports tool/function calling.

        Returns:
            True, as OpenRouter supports tool calling (OpenAI-compatible).
        """
        return True

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for OpenRouter API requests.

        Returns:
            Dictionary with Authorization, Content-Type, HTTP-Referer,
            and X-Title headers as required by OpenRouter.
        """
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://home-assistant.io",
            "X-Title": "Homeclaw",
        }

    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Build the request payload for OpenRouter API.

        Uses OpenAI-compatible format.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments. Supports:
                - tools: List of tool definitions for function calling.

        Returns:
            The request payload dictionary.
        """
        # Convert multimodal messages (with _images) to OpenAI vision format
        converted_messages = OpenAIProvider._convert_multimodal_messages(messages)

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
        """Extract the response text from OpenRouter API response.

        Uses OpenAI-compatible extraction logic. Handles both regular text
        responses and tool call responses.

        Args:
            response_data: The parsed JSON response from the OpenRouter API.

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
