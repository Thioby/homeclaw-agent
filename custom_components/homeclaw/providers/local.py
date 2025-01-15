"""Local AI provider for Ollama, LM Studio, and similar local inference servers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base_client import BaseHTTPClient
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@ProviderRegistry.register("local")
class LocalProvider(BaseHTTPClient):
    """Local AI provider for Ollama, LM Studio, etc.

    This provider supports local AI inference servers that expose an
    Ollama-compatible API. It can be configured to connect to any
    local server running Ollama, LM Studio, or similar software.

    Configuration options:
        - api_url: Base URL of the server (default: http://localhost:11434)
        - model: Model name to use (default: llama3.2)
        - token: Optional auth token for secured endpoints
        - supports_tools: Whether the model supports tool calling (default: False)
    """

    DEFAULT_API_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the Local provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration dictionary. Expected keys:
                - api_url: Base URL of the local server (optional)
                - model: Model name (optional, defaults to llama3.2)
                - token: Optional auth token for secured endpoints
                - supports_tools: Whether model supports tools (optional, defaults to False)
        """
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)

    @property
    def api_url(self) -> str:
        """Return the API endpoint URL.

        Returns:
            The full URL for the Ollama chat API endpoint.
        """
        base = self.config.get("api_url", self.DEFAULT_API_URL)
        # Remove trailing slash if present
        base = base.rstrip("/")
        return f"{base}/api/chat"

    @property
    def supports_tools(self) -> bool:
        """Return whether this provider supports tool/function calling.

        Most local models do not support tool calling by default,
        but this can be overridden via configuration.

        Returns:
            False by default, or the value from config if specified.
        """
        return self.config.get("supports_tools", False)

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for the request.

        Returns:
            Dictionary with Content-Type header and optional Authorization.
        """
        headers = {"Content-Type": "application/json"}
        if "token" in self.config:
            headers["Authorization"] = f"Bearer {self.config['token']}"
        return headers

    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Build the request payload for Ollama API.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional provider-specific arguments (unused).

        Returns:
            The request payload dictionary in Ollama format.
        """
        return {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from Ollama API response.

        Args:
            response_data: The parsed JSON response from the Ollama API.

        Returns:
            The extracted response text from message.content.
        """
        return response_data.get("message", {}).get("content", "")
