"""Xiaomi MiMo provider implementation."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@ProviderRegistry.register("xiaomi")
class XiaomiProvider(OpenAIProvider):
    """Xiaomi MiMo provider - OpenAI-compatible with api-key auth.

    Xiaomi MiMo provides reasoning and multimodal models via an
    OpenAI-compatible API. The only behavioral difference from the base
    OpenAI provider is the authentication header format: Xiaomi uses
    ``api-key`` instead of ``Authorization: Bearer``.
    """

    API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
    DEFAULT_MODEL = "mimo-v2-flash"

    @property
    def api_url(self) -> str:
        """Return the Xiaomi MiMo API endpoint URL.

        Returns:
            The Xiaomi chat completions endpoint URL.
        """
        return self.API_URL

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for Xiaomi MiMo API requests.

        Xiaomi uses ``api-key`` header instead of ``Authorization: Bearer``.

        Returns:
            Dictionary with api-key and Content-Type headers.
        """
        return {
            "api-key": self._token,
            "Content-Type": "application/json",
        }
