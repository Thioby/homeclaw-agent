"""Gemini AI provider implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..models import get_model_ids
from .adapters.gemini_adapter import GeminiAdapter
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
        self.adapter = GeminiAdapter()

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
        contents, system_instruction = self.adapter.transform_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.config.get("temperature", 0.2),
                "topP": self.config.get("top_p", 0.9),
            },
        }

        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        # Convert and add tools if provided
        tools = kwargs.get("tools")
        if tools:
            gemini_tools = self.adapter.transform_tools(tools)
            if gemini_tools:
                payload["tools"] = gemini_tools
                _LOGGER.debug(
                    "Added %d tools to Gemini request",
                    len(gemini_tools[0].get("functionDeclarations", [])),
                )

        return payload

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from Gemini API response.

        Delegates to GeminiAdapter.extract_response() and converts back to
        a string for backward compatibility with the agentic loop.

        Args:
            response_data: The parsed JSON response from Gemini API.

        Returns:
            The extracted response text, or JSON string for function calls.

        Raises:
            ValueError: If no response is available in candidates.
        """
        import json

        result = self.adapter.extract_response(response_data)

        if result["type"] == "tool_calls":
            # Preserve Gemini's native format for function call detection
            raw_part = result["tool_calls"][0].get("_raw_function_call", {})
            return json.dumps(raw_part)

        return result.get("content", "")

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
