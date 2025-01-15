"""Gemini AI provider implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..models import get_model_ids
from .base_client import BaseHTTPClient
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@ProviderRegistry.register("gemini")
class GeminiProvider(BaseHTTPClient):
    """Gemini AI provider using Google's Generative Language API.

    This provider implements the BaseHTTPClient interface for Gemini,
    handling message format conversion, tool conversion, and response parsing.
    """

    API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the Gemini provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration containing:
                - token: Google API key
                - model: Optional model name (default: gemini-2.5-flash)
        """
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)

    @property
    def supports_tools(self) -> bool:
        """Return True as Gemini supports function calling."""
        return True

    @property
    def api_url(self) -> str:
        """Return the API endpoint URL with model substituted.

        Returns:
            The full URL for the Gemini generateContent endpoint.
        """
        return self.API_URL_TEMPLATE.format(model=self._model)

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for Gemini API requests.

        Returns:
            Dictionary with x-goog-api-key and Content-Type headers.
        """
        return {
            "x-goog-api-key": self.config.get("token", ""),
            "Content-Type": "application/json",
        }

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert OpenAI-style messages to Gemini format.

        Gemini uses:
        - 'user' role (same as OpenAI)
        - 'model' role (instead of 'assistant')
        - System messages are extracted for systemInstruction
        - Function results use 'user' role with functionResponse parts

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Tuple of (contents list, system instruction text or None).
        """
        import json as _json

        contents = []
        system_instruction = None

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                # Concatenate multiple system messages
                if system_instruction is None:
                    system_instruction = content
                else:
                    system_instruction += "\n\n" + content
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                # Check if this is a function call response (JSON with functionCall)
                try:
                    parsed = _json.loads(content)
                    if "functionCall" in parsed:
                        contents.append({"role": "model", "parts": [parsed]})
                        continue
                except (ValueError, TypeError):
                    pass
                contents.append({"role": "model", "parts": [{"text": content}]})
            elif role == "function":
                # Tool result - Gemini uses functionResponse in user role
                func_name = message.get("name", "unknown")
                try:
                    result_data = _json.loads(content)
                except (ValueError, TypeError):
                    result_data = {"result": content}
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": func_name,
                                    "response": result_data,
                                }
                            }
                        ],
                    }
                )

        return contents, system_instruction

    def _convert_tools(
        self, openai_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Gemini functionDeclarations format.

        Args:
            openai_tools: List of OpenAI-formatted tool definitions.

        Returns:
            List containing a single dict with 'functionDeclarations' key.
        """
        if not openai_tools:
            return []

        function_declarations = []
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                function_declarations.append(
                    {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    }
                )

        return [{"functionDeclarations": function_declarations}]

    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Build the request payload for Gemini API.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments (e.g., tools for function calling).

        Returns:
            The request payload dictionary with contents and optional
            systemInstruction and tools.
        """
        contents, system_instruction = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.config.get("temperature", 0.7),
                "topP": self.config.get("top_p", 0.9),
            },
        }

        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        # Convert and add tools if provided
        tools = kwargs.get("tools")
        if tools:
            gemini_tools = self._convert_tools(tools)
            if gemini_tools:
                payload["tools"] = gemini_tools
                _LOGGER.debug(
                    "Added %d tools to Gemini request",
                    len(gemini_tools[0].get("functionDeclarations", [])),
                )

        return payload

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from Gemini API response.

        Handles both text responses and function calls for agentic loop.

        Args:
            response_data: The parsed JSON response from Gemini API.

        Returns:
            The extracted response text, or JSON string for function calls.

        Raises:
            ValueError: If no response is available in candidates.
        """
        import json

        candidates = response_data.get("candidates", [])

        if not candidates:
            raise ValueError("No response from Gemini API (empty candidates)")

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        if parts:
            first_part = parts[0]
            # Check for function call first
            if "functionCall" in first_part:
                # Return JSON for agentic loop to detect
                return json.dumps(first_part)
            # Otherwise return text
            if "text" in first_part:
                return first_part["text"]
            # No text and no functionCall - empty response
            return ""

        return ""

    def _get_api_url(self, model: str | None = None) -> str:
        """Get API URL with optional model override.

        Args:
            model: Optional model to use instead of configured default.

        Returns:
            The full URL for the Gemini generateContent endpoint.
        """
        effective_model = model or self._model
        available = get_model_ids("gemini")
        if available and effective_model not in available:
            _LOGGER.warning(
                "Model '%s' not in available models, using default '%s'",
                effective_model,
                self.DEFAULT_MODEL,
            )
            effective_model = self.DEFAULT_MODEL
        return self.API_URL_TEMPLATE.format(model=effective_model)

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Get a response from Gemini with optional model override.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments including optional 'model' override.

        Returns:
            The AI response as a string.
        """
        import asyncio

        # Allow per-request model override
        model = kwargs.pop("model", None)
        api_url = self._get_api_url(model)

        _LOGGER.debug("Gemini API request to model: %s", model or self._model)

        headers = self._build_headers()
        payload = self._build_payload(messages, **kwargs)

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                async with self.session.post(
                    api_url,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return self._extract_response(response_data)

                    error_text = await response.text()
                    _LOGGER.warning(
                        "Gemini API request failed (attempt %d/%d): status=%d, body=%s",
                        attempt + 1,
                        self._max_retries,
                        response.status,
                        error_text[:500],
                    )
                    last_error = Exception(
                        f"Gemini API request failed with status {response.status}"
                    )

            except Exception as e:
                _LOGGER.warning(
                    "Gemini API request exception (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries,
                    str(e),
                )
                last_error = e

            if attempt < self._max_retries - 1:
                await asyncio.sleep(self._retry_delay)

        raise last_error or Exception("Gemini API request failed after all retries")
