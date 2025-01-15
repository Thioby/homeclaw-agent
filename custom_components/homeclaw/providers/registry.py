"""AI Provider registry for the plugin architecture."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class AIProvider(ABC):
    """Abstract base class for AI providers.

    All AI providers must inherit from this class and implement
    the required abstract methods.
    """

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the AI provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration dictionary.
        """
        self.hass = hass
        self.config = config

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Return whether this provider supports tool/function calling.

        Returns:
            True if the provider supports tools, False otherwise.
        """

    @abstractmethod
    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Get a response from the AI provider.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The AI response as a string.
        """


class ProviderRegistry:
    """Registry for AI providers.

    This class manages registration and creation of AI provider instances.
    Providers register themselves using the @ProviderRegistry.register decorator.
    """

    _providers: dict[str, type[AIProvider]] = {}

    @classmethod
    def register(cls, name: str) -> type[AIProvider]:
        """Decorator to register a provider class.

        Args:
            name: The name to register the provider under.

        Returns:
            A decorator that registers the provider class.

        Example:
            @ProviderRegistry.register("openai")
            class OpenAIProvider(AIProvider):
                ...
        """

        def decorator(provider_cls: type[AIProvider]) -> type[AIProvider]:
            cls._providers[name] = provider_cls
            return provider_cls

        return decorator

    @classmethod
    def create(
        cls, name: str, hass: HomeAssistant, config: dict[str, Any]
    ) -> AIProvider:
        """Create a provider instance.

        Args:
            name: The registered name of the provider.
            hass: Home Assistant instance.
            config: Provider configuration dictionary.

        Returns:
            An instance of the requested provider.

        Raises:
            ValueError: If the provider name is not registered.
        """
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")

        provider_cls = cls._providers[name]
        return provider_cls(hass, config)

    @classmethod
    def available_providers(cls) -> list[str]:
        """List all registered providers.

        Returns:
            A list of registered provider names.
        """
        return list(cls._providers.keys())
