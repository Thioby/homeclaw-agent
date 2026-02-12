"""Tests for the Anthropic AI provider."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from custom_components.homeclaw.providers import ProviderRegistry

# Import to trigger registration
from custom_components.homeclaw.providers import (
    anthropic as anthropic_module,
)  # noqa: F401
from custom_components.homeclaw.providers.anthropic import AnthropicProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestAnthropicProviderRegistration:
    """Tests for AnthropicProvider registration."""

    def test_registered_in_registry(self) -> None:
        """Test that 'anthropic' is registered in available_providers."""
        available = ProviderRegistry.available_providers()
        assert "anthropic" in available


class TestAnthropicProviderSupportsTools:
    """Tests for AnthropicProvider tool support."""

    def test_supports_tools(self, hass: HomeAssistant) -> None:
        """Test that AnthropicProvider supports tools."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        assert provider.supports_tools is True


class TestAnthropicProviderHeaders:
    """Tests for AnthropicProvider header building."""

    def test_build_headers(self, hass: HomeAssistant) -> None:
        """Test that _build_headers includes x-api-key and anthropic-version."""
        config = {"api_key": "sk-ant-test-key"}

        provider = AnthropicProvider(hass, config)
        headers = provider._build_headers()

        assert headers["x-api-key"] == "sk-ant-test-key"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["Content-Type"] == "application/json"


class TestAnthropicProviderSystemMessage:
    """Tests for AnthropicProvider system message extraction."""

    def test_extract_system_message(self, hass: HomeAssistant) -> None:
        """Test that _extract_system separates system message from messages."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        filtered_messages, system = provider._extract_system(messages)

        assert system == "You are a helpful assistant."
        assert len(filtered_messages) == 2
        assert filtered_messages[0]["role"] == "user"
        assert filtered_messages[1]["role"] == "assistant"

    def test_extract_system_message_no_system(self, hass: HomeAssistant) -> None:
        """Test _extract_system when no system message present."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        filtered_messages, system = provider._extract_system(messages)

        assert system is None
        assert len(filtered_messages) == 2

    def test_extract_system_with_additional_tool_calls(
        self, hass: HomeAssistant
    ) -> None:
        """Assistant tool_use with additional calls should preserve all IDs."""
        provider = AnthropicProvider(hass, {"api_key": "test-key"})

        messages = [
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "tool_use": {
                            "id": "toolu_1",
                            "name": "get_entity_state",
                            "input": {"entity_id": "light.kitchen"},
                        },
                        "additional_tool_calls": [
                            {
                                "id": "toolu_2",
                                "name": "get_entity_state",
                                "input": {"entity_id": "switch.kettle"},
                            }
                        ],
                    }
                ),
            }
        ]

        filtered_messages, system = provider._extract_system(messages)

        assert system is None
        assert len(filtered_messages) == 1
        assistant_content = filtered_messages[0]["content"]
        assert len(assistant_content) == 2
        assert assistant_content[0]["id"] == "toolu_1"
        assert assistant_content[1]["id"] == "toolu_2"


class TestAnthropicProviderPayload:
    """Tests for AnthropicProvider payload building."""

    def test_build_payload(self, hass: HomeAssistant) -> None:
        """Test that _build_payload creates correct Anthropic payload structure."""
        config = {"api_key": "test-key", "model": "claude-sonnet-4-5-20250929"}

        provider = AnthropicProvider(hass, config)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]

        payload = provider._build_payload(messages)

        assert payload["model"] == "claude-sonnet-4-5-20250929"
        assert payload["max_tokens"] == 4096
        assert payload["system"] == "You are helpful."
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Hello"

    def test_build_payload_default_model(self, hass: HomeAssistant) -> None:
        """Test that _build_payload uses default model when not specified."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert "model" in payload
        # Default model should be set (synced with models_config.json)
        assert payload["model"] == "claude-sonnet-4-20250514"

    def test_build_payload_no_system(self, hass: HomeAssistant) -> None:
        """Test that _build_payload works without system message."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert "system" not in payload

    def test_build_payload_with_tools(self, hass: HomeAssistant) -> None:
        """Test that _build_payload includes converted tools."""
        config = {"api_key": "test-key", "model": "claude-sonnet-4-5-20250929"}

        provider = AnthropicProvider(hass, config)

        messages = [{"role": "user", "content": "What's the weather?"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

        payload = provider._build_payload(messages, tools=tools)

        assert "tools" in payload
        assert len(payload["tools"]) == 1
        assert payload["tools"][0]["name"] == "get_weather"
        assert "input_schema" in payload["tools"][0]


class TestAnthropicProviderToolConversion:
    """Tests for AnthropicProvider tool format conversion."""

    def test_convert_tools(self, hass: HomeAssistant) -> None:
        """Test that _convert_tools converts OpenAI format to Anthropic input_schema format."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"},
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

        anthropic_tools = provider._convert_tools(openai_tools)

        assert len(anthropic_tools) == 1
        assert anthropic_tools[0]["name"] == "get_weather"
        assert anthropic_tools[0]["description"] == "Get weather for a location"
        assert "input_schema" in anthropic_tools[0]
        assert anthropic_tools[0]["input_schema"]["type"] == "object"
        assert "location" in anthropic_tools[0]["input_schema"]["properties"]

    def test_convert_tools_empty(self, hass: HomeAssistant) -> None:
        """Test that _convert_tools handles empty list."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        result = provider._convert_tools([])
        assert result == []

    def test_convert_tools_none(self, hass: HomeAssistant) -> None:
        """Test that _convert_tools handles None input."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        result = provider._convert_tools(None)
        assert result == []


class TestAnthropicProviderResponseExtraction:
    """Tests for AnthropicProvider response extraction."""

    def test_extract_response(self, hass: HomeAssistant) -> None:
        """Test that _extract_response extracts text from content[0].text."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        response_data = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello! How can I help you?"}],
            "model": "claude-sonnet-4-5-20250929",
            "stop_reason": "end_turn",
        }

        result = provider._extract_response(response_data)

        assert result == "Hello! How can I help you?"

    def test_extract_response_with_tool_use(self, hass: HomeAssistant) -> None:
        """Test that _extract_response handles tool_use blocks correctly."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        response_data = {
            "id": "msg_456",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "get_weather",
                    "input": {"location": "San Francisco"},
                }
            ],
            "model": "claude-sonnet-4-5-20250929",
            "stop_reason": "tool_use",
        }

        result = provider._extract_response(response_data)

        # Should return the tool use data as JSON for further processing
        parsed = json.loads(result)
        assert "tool_use" in parsed
        assert parsed["tool_use"]["name"] == "get_weather"
        assert parsed["tool_use"]["input"]["location"] == "San Francisco"

    def test_extract_response_multiple_content_blocks(
        self, hass: HomeAssistant
    ) -> None:
        """Test _extract_response with multiple content blocks including text and tool_use."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        response_data = {
            "id": "msg_789",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check the weather for you."},
                {
                    "type": "tool_use",
                    "id": "toolu_456",
                    "name": "get_weather",
                    "input": {"location": "New York"},
                },
            ],
            "model": "claude-sonnet-4-5-20250929",
            "stop_reason": "tool_use",
        }

        result = provider._extract_response(response_data)

        # Should include the text part at minimum
        assert "Let me check the weather for you." in str(result)

    def test_extract_response_empty_content(self, hass: HomeAssistant) -> None:
        """Test _extract_response with empty content array."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        response_data = {
            "id": "msg_empty",
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": "claude-sonnet-4-5-20250929",
            "stop_reason": "end_turn",
        }

        result = provider._extract_response(response_data)

        # Should return empty string or handle gracefully
        assert result == ""


class TestAnthropicProviderAPIUrl:
    """Tests for AnthropicProvider API URL."""

    def test_api_url(self, hass: HomeAssistant) -> None:
        """Test that api_url returns correct Anthropic API endpoint."""
        config = {"api_key": "test-key"}

        provider = AnthropicProvider(hass, config)

        assert provider.api_url == "https://api.anthropic.com/v1/messages"


class TestAnthropicProviderStreaming:
    """Tests for AnthropicProvider streaming event parsing."""

    def test_extract_stream_chunks_text_delta(self, hass: HomeAssistant) -> None:
        """Text deltas should be converted to text chunks."""
        provider = AnthropicProvider(hass, {"api_key": "test-key"})
        pending_tools: dict[int, dict[str, Any]] = {}

        event = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {
                "type": "text_delta",
                "text": "Hello",
            },
        }

        chunks = provider._extract_stream_chunks(event, pending_tools)
        assert chunks == [{"type": "text", "content": "Hello"}]

    def test_extract_stream_chunks_tool_use_and_input_json(
        self, hass: HomeAssistant
    ) -> None:
        """Tool blocks should be assembled into tool_call chunks."""
        provider = AnthropicProvider(hass, {"api_key": "test-key"})
        pending_tools: dict[int, dict[str, Any]] = {}

        start_event = {
            "type": "content_block_start",
            "index": 1,
            "content_block": {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "get_weather",
            },
        }
        delta_event = {
            "type": "content_block_delta",
            "index": 1,
            "delta": {
                "type": "input_json_delta",
                "partial_json": '{"location":"Warsaw"}',
            },
        }
        stop_event = {
            "type": "message_delta",
            "delta": {
                "stop_reason": "tool_use",
            },
        }

        assert provider._extract_stream_chunks(start_event, pending_tools) == []
        assert provider._extract_stream_chunks(delta_event, pending_tools) == []

        chunks = provider._extract_stream_chunks(stop_event, pending_tools)
        assert chunks == [
            {
                "type": "tool_call",
                "name": "get_weather",
                "args": {"location": "Warsaw"},
                "id": "toolu_123",
            }
        ]
