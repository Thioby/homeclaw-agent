"""OpenRouter provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant  # noqa: F401


@ProviderRegistry.register("openrouter")
class OpenRouterProvider(OpenAIProvider):
    """OpenRouter API provider.

    OpenRouter provides access to multiple AI models through a unified,
    OpenAI-compatible API. Extends OpenAIProvider with custom headers
    and endpoint. Defaults target free models that support tool calling
    so that out-of-the-box use does not incur cost.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "tencent/hy3-preview:free"

    @property
    def api_url(self) -> str:
        """Return the OpenRouter API endpoint URL."""
        return self.API_URL

    @property
    def lightweight_model(self) -> str | None:
        """Return the cheapest/fastest model for background tasks.

        Reads from models_config.json (entry tagged lightweight: true).
        Falls back to the user-selected model if the JSON has no tag.
        """
        from ..models import get_lightweight_model

        return get_lightweight_model("openrouter") or self._model

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for OpenRouter API requests."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://home-assistant.io",
            "X-Title": "Homeclaw",
        }
