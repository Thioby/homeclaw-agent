"""Tests for the Xiaomi MiMo provider."""
from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.homeclaw.providers import ProviderRegistry

# Import to trigger registration
from custom_components.homeclaw.providers import xiaomi as xiaomi_module  # noqa: F401
from custom_components.homeclaw.providers.xiaomi import XiaomiProvider
from custom_components.homeclaw.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestXiaomiProviderRegistration:
    """Tests for Xiaomi provider registration."""

    def test_registered_in_registry(self) -> None:
        """Test that 'xiaomi' is in available_providers()."""
        available = ProviderRegistry.available_providers()
        assert "xiaomi" in available


class TestXiaomiProviderInheritance:
    """Tests for Xiaomi provider class hierarchy."""

    def test_extends_openai_provider(self) -> None:
        """Test that XiaomiProvider is a subclass of OpenAIProvider."""
        assert issubclass(XiaomiProvider, OpenAIProvider)


class TestXiaomiProviderApiUrl:
    """Tests for Xiaomi provider API URL."""

    def test_api_url(self, hass: HomeAssistant) -> None:
        """Test that api_url returns the correct Xiaomi MiMo endpoint."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        assert provider.api_url == "https://api.xiaomimimo.com/v1/chat/completions"


class TestXiaomiProviderBuildHeaders:
    """Tests for Xiaomi provider header building."""

    def test_build_headers_uses_api_key_format(self, hass: HomeAssistant) -> None:
        """Test api-key header format (NOT Bearer token)."""
        provider = XiaomiProvider(hass, {"token": "my-xiaomi-key"})
        headers = provider._build_headers()

        assert headers["api-key"] == "my-xiaomi-key"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers


class TestXiaomiProviderDefaultModel:
    """Tests for Xiaomi provider default model."""

    def test_default_model(self, hass: HomeAssistant) -> None:
        """Test that default model is mimo-v2-flash."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        payload = provider._build_payload([{"role": "user", "content": "Hi"}])
        assert payload["model"] == "mimo-v2-flash"

    def test_custom_model(self, hass: HomeAssistant) -> None:
        """Test that custom model overrides the default."""
        provider = XiaomiProvider(hass, {"token": "test-key", "model": "mimo-v2-pro"})
        payload = provider._build_payload([{"role": "user", "content": "Hi"}])
        assert payload["model"] == "mimo-v2-pro"
