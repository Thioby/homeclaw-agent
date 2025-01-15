"""Tests for the Gemini AI provider."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from custom_components.homeclaw.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGeminiProviderRegistration:
    """Tests for Gemini provider registration."""

    def test_registered_in_registry(self) -> None:
        """Test that 'gemini' is in available_providers."""
        # Import to trigger registration
        from custom_components.homeclaw.providers import gemini  # noqa: F401

        available = ProviderRegistry.available_providers()
        assert "gemini" in available


class TestGeminiProviderSupportsTools:
    """Tests for Gemini provider tool support."""

    def test_supports_tools(self, hass: HomeAssistant) -> None:
        """Test that supports_tools returns True."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_api_key"}

        provider = GeminiProvider(hass, config)

        assert provider.supports_tools is True


class TestGeminiProviderBuildHeaders:
    """Tests for Gemini provider header building."""

    def test_build_headers(self, hass: HomeAssistant) -> None:
        """Test that _build_headers includes x-goog-api-key."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_api_key"}

        provider = GeminiProvider(hass, config)
        headers = provider._build_headers()

        assert "x-goog-api-key" in headers
        assert headers["x-goog-api-key"] == "test_api_key"
        assert headers["Content-Type"] == "application/json"


class TestGeminiProviderConvertMessages:
    """Tests for Gemini message format conversion."""

    def test_convert_messages_user_role(self, hass: HomeAssistant) -> None:
        """Test that user messages are converted to 'user' role."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [{"role": "user", "content": "Hello"}]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"] == [{"text": "Hello"}]
        assert system is None

    def test_convert_messages_assistant_to_model(self, hass: HomeAssistant) -> None:
        """Test that assistant messages are converted to 'model' role."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [{"role": "assistant", "content": "Hi there!"}]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert contents[0]["role"] == "model"
        assert contents[0]["parts"] == [{"text": "Hi there!"}]

    def test_convert_messages_extract_system(self, hass: HomeAssistant) -> None:
        """Test that system messages are extracted separately."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1  # Only user message in contents
        assert contents[0]["role"] == "user"
        assert system == "You are a helpful assistant."

    def test_convert_messages_multiple_system_messages(self, hass: HomeAssistant) -> None:
        """Test that multiple system messages are concatenated."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [
            {"role": "system", "content": "First instruction."},
            {"role": "system", "content": "Second instruction."},
            {"role": "user", "content": "Hello"},
        ]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert system == "First instruction.\n\nSecond instruction."


class TestGeminiProviderBuildPayload:
    """Tests for Gemini payload building."""

    def test_build_payload_basic(self, hass: HomeAssistant) -> None:
        """Test that payload has correct contents structure."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert "contents" in payload
        assert len(payload["contents"]) == 1
        assert payload["contents"][0]["role"] == "user"
        assert payload["contents"][0]["parts"] == [{"text": "Hello"}]

    def test_build_payload_with_system_instruction(self, hass: HomeAssistant) -> None:
        """Test that system instruction is included in payload."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello"},
        ]
        payload = provider._build_payload(messages)

        assert "systemInstruction" in payload
        assert payload["systemInstruction"]["parts"] == [{"text": "Be helpful."}]

    def test_build_payload_no_system_instruction(self, hass: HomeAssistant) -> None:
        """Test that systemInstruction is absent when no system message."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert "systemInstruction" not in payload


class TestGeminiProviderExtractResponse:
    """Tests for Gemini response extraction."""

    def test_extract_response(self, hass: HomeAssistant) -> None:
        """Test extracting response from candidates[0].content.parts[0].text."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello from Gemini!"}]
                    }
                }
            ]
        }

        result = provider._extract_response(response_data)

        assert result == "Hello from Gemini!"

    def test_extract_response_empty_candidates(self, hass: HomeAssistant) -> None:
        """Test extracting response when candidates is empty."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        response_data = {"candidates": []}

        with pytest.raises(ValueError, match="No response"):
            provider._extract_response(response_data)

    def test_extract_response_missing_text(self, hass: HomeAssistant) -> None:
        """Test extracting response when text is missing."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{}]  # No text field
                    }
                }
            ]
        }

        result = provider._extract_response(response_data)
        assert result == ""


class TestGeminiProviderConvertTools:
    """Tests for Gemini tool format conversion."""

    def test_convert_tools(self, hass: HomeAssistant) -> None:
        """Test converting OpenAI tool format to Gemini functionDeclarations."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"}
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

        gemini_tools = provider._convert_tools(openai_tools)

        assert len(gemini_tools) == 1
        assert "functionDeclarations" in gemini_tools[0]
        declarations = gemini_tools[0]["functionDeclarations"]
        assert len(declarations) == 1
        assert declarations[0]["name"] == "get_weather"
        assert declarations[0]["description"] == "Get the weather"
        assert "parameters" in declarations[0]

    def test_convert_tools_empty_list(self, hass: HomeAssistant) -> None:
        """Test converting empty tool list."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        gemini_tools = provider._convert_tools([])

        assert gemini_tools == []

    def test_convert_tools_multiple(self, hass: HomeAssistant) -> None:
        """Test converting multiple tools."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}
        provider = GeminiProvider(hass, config)

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "tool_a",
                    "description": "First tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_b",
                    "description": "Second tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        gemini_tools = provider._convert_tools(openai_tools)

        assert len(gemini_tools) == 1
        declarations = gemini_tools[0]["functionDeclarations"]
        assert len(declarations) == 2
        assert declarations[0]["name"] == "tool_a"
        assert declarations[1]["name"] == "tool_b"


class TestGeminiProviderApiUrl:
    """Tests for Gemini API URL construction."""

    def test_api_url_default_model(self, hass: HomeAssistant) -> None:
        """Test API URL with default model."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key"}

        provider = GeminiProvider(hass, config)

        assert "gemini-2.5-flash" in provider.api_url
        assert "generativelanguage.googleapis.com" in provider.api_url
        assert ":generateContent" in provider.api_url

    def test_api_url_custom_model(self, hass: HomeAssistant) -> None:
        """Test API URL with custom model."""
        from custom_components.homeclaw.providers.gemini import GeminiProvider

        config = {"token": "test_key", "model": "gemini-pro"}

        provider = GeminiProvider(hass, config)

        assert "gemini-pro" in provider.api_url
        assert "generativelanguage.googleapis.com" in provider.api_url
