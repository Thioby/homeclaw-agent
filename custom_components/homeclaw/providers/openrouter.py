"""OpenRouter provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@ProviderRegistry.register("openrouter")
class OpenRouterProvider(OpenAIProvider):
    """OpenRouter API provider.

    OpenRouter provides access to multiple AI models through a unified,
    OpenAI-compatible API. Extends OpenAIProvider with custom headers
    and endpoint.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "openai/gpt-4o"

    @property
    def api_url(self) -> str:
        """Return the OpenRouter API endpoint URL.

        Returns:
            The OpenRouter chat completions endpoint URL.
        """
        return self.API_URL

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
