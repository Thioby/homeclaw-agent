"""Tests for the OpenAI provider."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from custom_components.homeclaw.providers import ProviderRegistry

# Import to trigger registration
from custom_components.homeclaw.providers import openai as openai_module  # noqa: F401
from custom_components.homeclaw.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestOpenAIProviderRegistration:
    """Tests for OpenAI provider registration."""

    def test_registered_in_registry(self) -> None:
        """Test that 'openai' is in available_providers()."""
        available = ProviderRegistry.available_providers()
        assert "openai" in available


class TestOpenAIProviderSupportsTools:
    """Tests for OpenAI provider tool support."""

    def test_supports_tools(self, hass: HomeAssistant) -> None:
        """Test that OpenAI provider returns True for supports_tools."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)

        assert provider.supports_tools is True


class TestOpenAIProviderBuildHeaders:
    """Tests for OpenAI provider header building."""

    def test_build_headers(self, hass: HomeAssistant) -> None:
        """Test Authorization Bearer token and Content-Type headers."""
        config = {"token": "sk-test-key-12345"}

        provider = OpenAIProvider(hass, config)
        headers = provider._build_headers()

        assert headers["Authorization"] == "Bearer sk-test-key-12345"
        assert headers["Content-Type"] == "application/json"


class TestOpenAIProviderBuildPayload:
    """Tests for OpenAI provider payload building."""

    def test_build_payload(self, hass: HomeAssistant) -> None:
        """Test that model and messages are in payload."""
        config = {"token": "sk-test-key", "model": "gpt-4"}

        provider = OpenAIProvider(hass, config)
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "gpt-4"
        assert payload["messages"] == messages

    def test_build_payload_default_model(self, hass: HomeAssistant) -> None:
        """Test that default model is used when not specified."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "gpt-4o"
        assert payload["messages"] == messages

    def test_build_payload_with_tools(self, hass: HomeAssistant) -> None:
        """Test that tools are included when passed."""
        config = {"token": "sk-test-key", "model": "gpt-4"}

        provider = OpenAIProvider(hass, config)
        messages = [{"role": "user", "content": "Turn on the lights"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "turn_on_light",
                    "description": "Turn on a light",
                    "parameters": {
                        "type": "object",
                        "properties": {"entity_id": {"type": "string"}},
                        "required": ["entity_id"],
                    },
                },
            }
        ]

        payload = provider._build_payload(messages, tools=tools)

        assert payload["model"] == "gpt-4"
        assert payload["messages"] == messages
        assert payload["tools"] == tools


class TestOpenAIProviderExtractResponse:
    """Tests for OpenAI provider response extraction."""

    def test_extract_response(self, hass: HomeAssistant) -> None:
        """Test extraction from choices[0].message.content."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        }

        result = provider._extract_response(response_data)

        assert result == "Hello! How can I help you today?"

    def test_extract_response_with_tool_calls(self, hass: HomeAssistant) -> None:
        """Test handling of tool_calls in response."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "turn_on_light",
                                    "arguments": '{"entity_id": "light.living_room"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }

        result = provider._extract_response(response_data)

        # When tool_calls are present, return a JSON string with the tool calls
        parsed_result = json.loads(result)
        assert "tool_calls" in parsed_result
        assert len(parsed_result["tool_calls"]) == 1
        assert parsed_result["tool_calls"][0]["function"]["name"] == "turn_on_light"

    def test_extract_response_empty_content(self, hass: HomeAssistant) -> None:
        """Test handling of empty content in response."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        response_data = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                    },
                }
            ],
        }

        result = provider._extract_response(response_data)

        assert result == ""


class TestOpenAIProviderApiUrl:
    """Tests for OpenAI provider API URL."""

    def test_api_url(self, hass: HomeAssistant) -> None:
        """Test that api_url returns the correct OpenAI endpoint."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)

        assert provider.api_url == "https://api.openai.com/v1/chat/completions"
