"""Groq provider implementation."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@ProviderRegistry.register("groq")
class GroqProvider(OpenAIProvider):
    """Groq provider - OpenAI-compatible with different URL.

    Groq provides fast inference for open-source LLMs using their custom
    hardware (LPU). The API is OpenAI-compatible, so we extend OpenAIProvider
    and override only the API URL and default model.
    """

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    @property
    def api_url(self) -> str:
        """Return the Groq API endpoint URL.

        Returns:
            The Groq chat completions endpoint URL.
        """
        return self.API_URL
