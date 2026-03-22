"""Tests for the Xiaomi MiMo provider.

Covers requirements CHAT-01 through CHAT-10:
- CHAT-01: Registration in ProviderRegistry
- CHAT-02: Subclass of OpenAIProvider
- CHAT-03: Correct API URL
- CHAT-04: api-key header format (NOT Bearer)
- CHAT-05: Default model mimo-v2-flash
- CHAT-06: models_config.json entries with correct context windows
- CHAT-07: agent_compat token_keys and default model mappings
- CHAT-08: Import in __init__.py triggers registration (covered by CHAT-01)
- CHAT-09: Multimodal message conversion (inherited)
- CHAT-10: Tool calling support (inherited)
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from custom_components.homeclaw.providers import ProviderRegistry

# Import to trigger registration
from custom_components.homeclaw.providers import xiaomi as xiaomi_module  # noqa: F401
from custom_components.homeclaw.providers.xiaomi import XiaomiProvider
from custom_components.homeclaw.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# ---------------------------------------------------------------------------
# CHAT-01 / CHAT-08: Registration
# ---------------------------------------------------------------------------


class TestXiaomiProviderRegistration:
    """Tests for Xiaomi provider registration (CHAT-01, CHAT-08)."""

    def test_registered_in_registry(self) -> None:
        """Test that 'xiaomi' is in available_providers().

        Re-registers to handle test ordering (test_registry.py clears registry).
        """
        # Re-register if cleared by prior tests
        if "xiaomi" not in ProviderRegistry._providers:
            ProviderRegistry.register("xiaomi")(XiaomiProvider)

        available = ProviderRegistry.available_providers()
        assert "xiaomi" in available


# ---------------------------------------------------------------------------
# CHAT-02: Inheritance
# ---------------------------------------------------------------------------


class TestXiaomiProviderInheritance:
    """Tests for Xiaomi provider class hierarchy (CHAT-02)."""

    def test_extends_openai_provider(self) -> None:
        """Test that XiaomiProvider is a subclass of OpenAIProvider."""
        assert issubclass(XiaomiProvider, OpenAIProvider)


# ---------------------------------------------------------------------------
# CHAT-03: API URL
# ---------------------------------------------------------------------------


class TestXiaomiProviderApiUrl:
    """Tests for Xiaomi provider API URL (CHAT-03)."""

    def test_api_url(self, hass: HomeAssistant) -> None:
        """Test that api_url returns the correct Xiaomi MiMo endpoint."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        assert provider.api_url == "https://api.xiaomimimo.com/v1/chat/completions"


# ---------------------------------------------------------------------------
# CHAT-04: Headers (api-key, NOT Bearer)
# ---------------------------------------------------------------------------


class TestXiaomiProviderBuildHeaders:
    """Tests for Xiaomi provider header building (CHAT-04)."""

    def test_build_headers_uses_api_key_format(self, hass: HomeAssistant) -> None:
        """Test api-key header format (NOT Bearer token)."""
        provider = XiaomiProvider(hass, {"token": "my-xiaomi-key"})
        headers = provider._build_headers()

        assert headers["api-key"] == "my-xiaomi-key"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# CHAT-05: Default model
# ---------------------------------------------------------------------------


class TestXiaomiProviderDefaultModel:
    """Tests for Xiaomi provider default model (CHAT-05)."""

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


# ---------------------------------------------------------------------------
# CHAT-10 (partial): Tool support
# ---------------------------------------------------------------------------


class TestXiaomiProviderSupportsTools:
    """Tests for Xiaomi provider tool support (CHAT-10)."""

    def test_supports_tools(self, hass: HomeAssistant) -> None:
        """Test that Xiaomi provider returns True for supports_tools."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        assert provider.supports_tools is True


# ---------------------------------------------------------------------------
# CHAT-10: Build payload with tools
# ---------------------------------------------------------------------------


class TestXiaomiProviderBuildPayload:
    """Tests for Xiaomi provider payload building (CHAT-10)."""

    def test_build_payload(self, hass: HomeAssistant) -> None:
        """Test that model and messages are in payload."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "mimo-v2-flash"
        assert payload["messages"] == messages

    def test_build_payload_with_tools(self, hass: HomeAssistant) -> None:
        """Test that tools are included when passed."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        messages = [{"role": "user", "content": "Turn on the lights"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "turn_on_light",
                    "description": "Turn on a light",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {"type": "string"}
                        },
                        "required": ["entity_id"],
                    },
                },
            }
        ]

        payload = provider._build_payload(messages, tools=tools)

        assert payload["model"] == "mimo-v2-flash"
        assert payload["messages"] == messages
        assert payload["tools"] == tools


# ---------------------------------------------------------------------------
# CHAT-10: Extract response (inherited from OpenAI)
# ---------------------------------------------------------------------------


class TestXiaomiProviderExtractResponse:
    """Tests for Xiaomi provider response extraction (CHAT-10)."""

    def test_extract_response(self, hass: HomeAssistant) -> None:
        """Test extraction from choices[0].message.content."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello from MiMo!",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }

        result = provider._extract_response(response_data)
        assert result == "Hello from MiMo!"

    def test_extract_response_with_tool_calls(self, hass: HomeAssistant) -> None:
        """Test handling of tool_calls in response."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        response_data = {
            "id": "chatcmpl-456",
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
        parsed_result = json.loads(result)
        assert "tool_calls" in parsed_result
        assert len(parsed_result["tool_calls"]) == 1
        assert parsed_result["tool_calls"][0]["function"]["name"] == "turn_on_light"

    def test_extract_response_empty_choices(self, hass: HomeAssistant) -> None:
        """Test handling of empty choices in response."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        response_data = {"id": "chatcmpl-789", "choices": []}

        result = provider._extract_response(response_data)
        assert result == ""


# ---------------------------------------------------------------------------
# CHAT-06: Models config
# ---------------------------------------------------------------------------


class TestXiaomiModelsConfig:
    """Tests for Xiaomi models in models_config.json (CHAT-06)."""

    def test_xiaomi_models_in_config(self) -> None:
        """Test that xiaomi key exists with 3 models."""
        from custom_components.homeclaw.models import load_models_config, invalidate_cache

        invalidate_cache()
        config = load_models_config()
        assert "xiaomi" in config
        models = config["xiaomi"]["models"]
        assert len(models) == 3
        model_ids = [m["id"] for m in models]
        assert model_ids == ["mimo-v2-flash", "mimo-v2-pro", "mimo-v2-omni"]

    def test_xiaomi_context_windows(self) -> None:
        """Test correct context windows for each model."""
        from custom_components.homeclaw.models import load_models_config, invalidate_cache

        invalidate_cache()
        config = load_models_config()
        models = {m["id"]: m for m in config["xiaomi"]["models"]}

        assert models["mimo-v2-flash"]["context_window"] == 262144
        assert models["mimo-v2-pro"]["context_window"] == 1048576
        assert models["mimo-v2-omni"]["context_window"] == 262144

    def test_xiaomi_default_model(self) -> None:
        """Test that exactly one model has default=true and it is mimo-v2-flash."""
        from custom_components.homeclaw.models import load_models_config, invalidate_cache

        invalidate_cache()
        config = load_models_config()
        models = config["xiaomi"]["models"]
        defaults = [m for m in models if m.get("default")]
        assert len(defaults) == 1
        assert defaults[0]["id"] == "mimo-v2-flash"


# ---------------------------------------------------------------------------
# CHAT-07: Agent compat mappings
# ---------------------------------------------------------------------------


class TestXiaomiAgentCompat:
    """Tests for Xiaomi in agent_compat.py (CHAT-07)."""

    def test_token_key_mapping(self, hass: HomeAssistant) -> None:
        """Test that agent_compat maps xiaomi to xiaomi_token."""
        from custom_components.homeclaw.agent_compat import HomeclawAgent

        agent = HomeclawAgent(
            hass,
            {"ai_provider": "xiaomi", "xiaomi_token": "test-key-123"},
        )
        # The provider config should have picked up the token
        provider_config = agent._build_provider_config()
        assert provider_config["token"] == "test-key-123"

    def test_default_model_mapping(self, hass: HomeAssistant) -> None:
        """Test that _get_default_model returns mimo-v2-flash for xiaomi."""
        from custom_components.homeclaw.agent_compat import HomeclawAgent

        agent = HomeclawAgent(
            hass,
            {"ai_provider": "xiaomi", "xiaomi_token": "test-key"},
        )
        assert agent._get_default_model("xiaomi") == "mimo-v2-flash"


# ---------------------------------------------------------------------------
# Config flow integration
# ---------------------------------------------------------------------------


class TestXiaomiConfigFlow:
    """Tests for Xiaomi in config_flow.py dicts."""

    def test_xiaomi_in_providers(self) -> None:
        """Test that xiaomi key exists in PROVIDERS dict."""
        from custom_components.homeclaw.config_flow import PROVIDERS

        assert "xiaomi" in PROVIDERS
        assert PROVIDERS["xiaomi"] == "Xiaomi MiMo"

    def test_xiaomi_token_field(self) -> None:
        """Test that TOKEN_FIELD_NAMES maps xiaomi correctly."""
        from custom_components.homeclaw.config_flow import TOKEN_FIELD_NAMES

        assert TOKEN_FIELD_NAMES["xiaomi"] == "xiaomi_token"

    def test_xiaomi_token_label(self) -> None:
        """Test that TOKEN_LABELS maps xiaomi correctly."""
        from custom_components.homeclaw.config_flow import TOKEN_LABELS

        assert TOKEN_LABELS["xiaomi"] == "Xiaomi MiMo API Key"


# ---------------------------------------------------------------------------
# CHAT-09: Multimodal (inherited from OpenAI)
# ---------------------------------------------------------------------------


class TestXiaomiMultimodal:
    """Tests for multimodal message conversion (CHAT-09)."""

    def test_multimodal_messages_converted(self, hass: HomeAssistant) -> None:
        """Test that _convert_multimodal_messages handles images correctly."""
        provider = XiaomiProvider(hass, {"token": "test-key"})
        messages = [
            {
                "role": "user",
                "content": "Describe this image",
                "_images": [
                    {"mime_type": "image/png", "data": "iVBORw0KGgo="}
                ],
            }
        ]

        result = provider._convert_multimodal_messages(messages)

        assert len(result) == 1
        content = result[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Describe this image"
        assert content[1]["type"] == "image_url"
        assert "data:image/png;base64,iVBORw0KGgo=" in content[1]["image_url"]["url"]
