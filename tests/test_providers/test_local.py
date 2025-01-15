"""Tests for the Local/Ollama provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from custom_components.homeclaw.providers import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestLocalProviderRegistration:
    """Tests for Local provider registration."""

    def test_registered_in_registry(self) -> None:
        """Test that 'local' is in available_providers()."""
        # Import to trigger registration
        from custom_components.homeclaw.providers import local as local_module  # noqa: F401

        available = ProviderRegistry.available_providers()
        assert "local" in available


class TestLocalProviderSupportsTools:
    """Tests for Local provider tool support."""

    def test_supports_tools_default(self, hass: HomeAssistant) -> None:
        """Test that Local provider returns False for supports_tools by default."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)

        assert provider.supports_tools is False

    def test_supports_tools_configurable(self, hass: HomeAssistant) -> None:
        """Test that supports_tools is configurable via config."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {"supports_tools": True}

        provider = LocalProvider(hass, config)

        assert provider.supports_tools is True


class TestLocalProviderApiUrl:
    """Tests for Local provider API URL configuration."""

    def test_api_url_default(self, hass: HomeAssistant) -> None:
        """Test that api_url defaults to localhost:11434 with /api/chat endpoint."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)

        assert provider.api_url == "http://localhost:11434/api/chat"

    def test_api_url_configurable(self, hass: HomeAssistant) -> None:
        """Test that api_url is configurable via config."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {"api_url": "http://192.168.1.100:8080"}

        provider = LocalProvider(hass, config)

        assert provider.api_url == "http://192.168.1.100:8080/api/chat"

    def test_api_url_removes_trailing_slash(self, hass: HomeAssistant) -> None:
        """Test that trailing slash is handled correctly."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {"api_url": "http://192.168.1.100:8080/"}

        provider = LocalProvider(hass, config)

        # Should not result in double slash
        assert provider.api_url == "http://192.168.1.100:8080/api/chat"


class TestLocalProviderBuildHeaders:
    """Tests for Local provider header building."""

    def test_build_headers_basic(self, hass: HomeAssistant) -> None:
        """Test that Content-Type is included in headers."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        headers = provider._build_headers()

        assert headers["Content-Type"] == "application/json"

    def test_build_headers_with_token(self, hass: HomeAssistant) -> None:
        """Test that Authorization header is included when token is provided."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {"token": "my-secret-token"}

        provider = LocalProvider(hass, config)
        headers = provider._build_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer my-secret-token"

    def test_build_headers_no_auth_without_token(self, hass: HomeAssistant) -> None:
        """Test that Authorization header is not included when token is not provided."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        headers = provider._build_headers()

        assert "Authorization" not in headers


class TestLocalProviderBuildPayload:
    """Tests for Local provider payload building."""

    def test_build_payload_basic(self, hass: HomeAssistant) -> None:
        """Test that payload has Ollama format with model, messages, stream: false."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {"model": "llama3"}

        provider = LocalProvider(hass, config)
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "llama3"
        assert payload["messages"] == messages
        assert payload["stream"] is False

    def test_build_payload_default_model(self, hass: HomeAssistant) -> None:
        """Test that default model is 'llama3.2' when not specified."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "llama3.2"
        assert payload["messages"] == messages
        assert payload["stream"] is False

    def test_build_payload_multiple_messages(self, hass: HomeAssistant) -> None:
        """Test payload with multiple messages."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {"model": "mistral"}

        provider = LocalProvider(hass, config)
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        payload = provider._build_payload(messages)

        assert payload["model"] == "mistral"
        assert payload["messages"] == messages
        assert payload["stream"] is False


class TestLocalProviderExtractResponse:
    """Tests for Local provider response extraction."""

    def test_extract_response(self, hass: HomeAssistant) -> None:
        """Test extraction from message.content (Ollama format)."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        response_data = {
            "model": "llama3",
            "created_at": "2024-01-15T10:00:00Z",
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?",
            },
            "done": True,
        }

        result = provider._extract_response(response_data)

        assert result == "Hello! How can I help you today?"

    def test_extract_response_empty_content(self, hass: HomeAssistant) -> None:
        """Test extraction when content is empty."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        response_data = {
            "model": "llama3",
            "message": {
                "role": "assistant",
                "content": "",
            },
            "done": True,
        }

        result = provider._extract_response(response_data)

        assert result == ""

    def test_extract_response_missing_message(self, hass: HomeAssistant) -> None:
        """Test extraction when message field is missing."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        response_data = {
            "model": "llama3",
            "done": True,
        }

        result = provider._extract_response(response_data)

        assert result == ""

    def test_extract_response_missing_content(self, hass: HomeAssistant) -> None:
        """Test extraction when content field is missing in message."""
        from custom_components.homeclaw.providers.local import LocalProvider

        config = {}

        provider = LocalProvider(hass, config)
        response_data = {
            "model": "llama3",
            "message": {
                "role": "assistant",
            },
            "done": True,
        }

        result = provider._extract_response(response_data)

        assert result == ""
