"""Tests for the AI provider registry."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from custom_components.homeclaw.providers.registry import (
    AIProvider,
    ProviderRegistry,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        ProviderRegistry._providers = {}

    def test_register_provider(self) -> None:
        """Test that decorator registers provider class."""

        @ProviderRegistry.register("test_provider")
        class TestProvider(AIProvider):
            @property
            def supports_tools(self) -> bool:
                return True

            async def get_response(self, messages: list, **kwargs) -> str:
                return "test response"

        assert "test_provider" in ProviderRegistry._providers
        assert ProviderRegistry._providers["test_provider"] is TestProvider

    def test_create_provider(self, hass: HomeAssistant) -> None:
        """Test factory creates instance with hass and config."""
        config = {"api_key": "test_key"}

        @ProviderRegistry.register("test_provider")
        class TestProvider(AIProvider):
            @property
            def supports_tools(self) -> bool:
                return True

            async def get_response(self, messages: list, **kwargs) -> str:
                return "test response"

        provider = ProviderRegistry.create("test_provider", hass, config)

        assert isinstance(provider, TestProvider)
        assert provider.hass is hass
        assert provider.config == config

    def test_create_unknown_provider_raises(self, hass: HomeAssistant) -> None:
        """Test that creating unknown provider raises ValueError."""
        config = {}

        with pytest.raises(ValueError, match="Unknown provider: unknown_provider"):
            ProviderRegistry.create("unknown_provider", hass, config)

    def test_available_providers(self) -> None:
        """Test listing registered providers."""

        @ProviderRegistry.register("provider_a")
        class ProviderA(AIProvider):
            @property
            def supports_tools(self) -> bool:
                return True

            async def get_response(self, messages: list, **kwargs) -> str:
                return "a"

        @ProviderRegistry.register("provider_b")
        class ProviderB(AIProvider):
            @property
            def supports_tools(self) -> bool:
                return False

            async def get_response(self, messages: list, **kwargs) -> str:
                return "b"

        available = ProviderRegistry.available_providers()

        assert sorted(available) == ["provider_a", "provider_b"]


class TestAIProvider:
    """Tests for AIProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self, hass: HomeAssistant) -> None:
        """Test that AIProvider cannot be instantiated directly."""
        config = {}

        with pytest.raises(TypeError):
            AIProvider(hass, config)

    def test_must_implement_supports_tools(self, hass: HomeAssistant) -> None:
        """Test that subclass must implement supports_tools property."""
        config = {}

        class IncompleteProvider(AIProvider):
            async def get_response(self, messages: list, **kwargs) -> str:
                return "response"

        with pytest.raises(TypeError):
            IncompleteProvider(hass, config)

    def test_must_implement_get_response(self, hass: HomeAssistant) -> None:
        """Test that subclass must implement get_response method."""
        config = {}

        class IncompleteProvider(AIProvider):
            @property
            def supports_tools(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteProvider(hass, config)
