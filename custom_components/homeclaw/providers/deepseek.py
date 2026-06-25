"""DeepSeek provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@ProviderRegistry.register("deepseek")
class DeepSeekProvider(OpenAIProvider):
    """DeepSeek provider - OpenAI-compatible with a thinking-mode toggle.

    DeepSeek exposes an OpenAI-compatible chat completions API, so we extend
    OpenAIProvider and override only the API URL, the default model, and the
    reasoning control. DeepSeek switches reasoning on or off via a ``thinking``
    object rather than OpenAI's ``reasoning_effort`` field, and defaults to
    thinking enabled, so we always send it explicitly to keep latency and cost
    down when the user has not asked for reasoning.
    """

    API_URL = "https://api.deepseek.com/chat/completions"
    DEFAULT_MODEL = "deepseek-v4-pro"

    @property
    def api_url(self) -> str:
        """Return the DeepSeek API endpoint URL.

        Returns:
            The DeepSeek chat completions endpoint URL.
        """
        return self.API_URL

    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        payload = super()._build_payload(messages, **kwargs)
        payload.pop("reasoning_effort", None)
        payload["thinking"] = {
            "type": "enabled" if kwargs.get("reasoning") else "disabled",
        }
        return payload
