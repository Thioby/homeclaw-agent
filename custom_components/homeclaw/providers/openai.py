"""OpenAI provider implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from ..core.tool_call_codec import extract_tool_calls_from_assistant_content
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
