"""z.ai (Zhipu AI / BigModel) provider implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Endpoint URLs for z.ai API (OpenAI-compatible)
ZAI_ENDPOINTS: dict[str, str] = {
    "general": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "coding": "https://codegeex.cn/api/paas/v4/chat/completions",
}


@ProviderRegistry.register("zai")
class ZaiProvider(OpenAIProvider):
    """z.ai (Zhipu AI) provider - OpenAI-compatible API.

    Zhipu AI provides GLM models through an OpenAI-compatible REST API.
    Supports two endpoint types:
      - general: standard GLM models
      - coding: CodeGeeX coding models (3x usage, 1/7 cost)
    """

    DEFAULT_MODEL = "glm-4-flash"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the z.ai provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration. Expected keys:
                - token: z.ai API key (required)
                - model: Model name (optional, defaults to glm-4-flash)
                - endpoint_type: 'general' or 'coding' (optional, defaults to general)
        """
        super().__init__(hass, config)
        self._endpoint_type = config.get("endpoint_type", "general")
        _LOGGER.debug(
            "ZaiProvider initialized: model=%s, endpoint=%s",
            self._model,
            self._endpoint_type,
        )

    @property
    def api_url(self) -> str:
        """Return the z.ai API endpoint URL.

        Returns:
            The z.ai chat completions endpoint URL based on endpoint type.
        """
        return ZAI_ENDPOINTS.get(self._endpoint_type, ZAI_ENDPOINTS["general"])
