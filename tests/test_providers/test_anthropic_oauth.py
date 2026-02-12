"""Tests for Anthropic OAuth provider."""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.homeclaw.providers.anthropic_oauth import (
    AnthropicOAuthProvider,
    CLAUDE_CODE_SYSTEM_PREFIX,
    ANTHROPIC_BETA_FLAGS,
    USER_AGENT,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with OAuth tokens."""
    entry = MagicMock()
    entry.data = {
        "anthropic_oauth": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": 9999999999.0,  # Far future
        }
    }
    return entry


@pytest.fixture
def provider(mock_hass, mock_config_entry):
    """Create an AnthropicOAuthProvider instance."""
    config = {
        "model": "claude-sonnet-4-5-20250929",
        "config_entry": mock_config_entry,
    }
    return AnthropicOAuthProvider(mock_hass, config)


class TestAnthropicOAuthProviderInit:
    """Tests for provider initialization."""

    def test_init_stores_hass(self, mock_hass, mock_config_entry):
        """Test that provider stores hass reference."""
        config = {"config_entry": mock_config_entry}
        provider = AnthropicOAuthProvider(mock_hass, config)
        assert provider.hass is mock_hass

    def test_init_uses_default_model(self, mock_hass, mock_config_entry):
        """Test that provider uses default model if not specified."""
        config = {"config_entry": mock_config_entry}
        provider = AnthropicOAuthProvider(mock_hass, config)
        assert provider._model == "claude-sonnet-4-20250514"

    def test_init_custom_model(self, mock_hass, mock_config_entry):
        """Test that provider uses custom model if specified."""
        config = {"model": "claude-opus-4-20250514", "config_entry": mock_config_entry}
        provider = AnthropicOAuthProvider(mock_hass, config)
        assert provider._model == "claude-opus-4-20250514"

    def test_init_loads_oauth_data_from_config_entry(
        self, mock_hass, mock_config_entry
    ):
        """Test that provider loads OAuth data from config entry."""
        config = {"config_entry": mock_config_entry}
        provider = AnthropicOAuthProvider(mock_hass, config)
        assert provider._oauth_data["access_token"] == "test_access_token"
        assert provider._oauth_data["refresh_token"] == "test_refresh_token"

    def test_supports_tools(self, provider):
        """Test that provider reports tool support."""
        assert provider.supports_tools is True


class TestAnthropicOAuthProviderTokenManagement:
    """Tests for OAuth token management."""

    @pytest.mark.asyncio
    async def test_get_valid_token_returns_cached_token(self, provider):
        """Test that valid token is returned without refresh."""
        token = await provider._get_valid_token()
        assert token == "test_access_token"

    @pytest.mark.asyncio
    async def test_get_valid_token_refreshes_expired_token(
        self, mock_hass, mock_config_entry
    ):
        """Test that expired token triggers refresh."""
        import time

        mock_config_entry.data = {
            "anthropic_oauth": {
                "access_token": "old_token",
                "refresh_token": "test_refresh_token",
                "expires_at": time.time() - 1000,  # Expired
            }
        }

        config = {"config_entry": mock_config_entry}
        provider = AnthropicOAuthProvider(mock_hass, config)

        with patch("custom_components.homeclaw.oauth.refresh_token") as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_at": time.time() + 3600,
            }

            token = await provider._get_valid_token()

            assert token == "new_access_token"
            mock_refresh.assert_called_once()


class TestAnthropicOAuthProviderTransformations:
    """Tests for request/response transformations."""

    def test_transform_request_adds_tool_prefix(self, provider):
        """Test that mcp_ prefix is added to tool names."""
        payload = {
            "tools": [
                {"name": "get_weather", "description": "Get weather"},
            ]
        }

        result = provider._transform_request(payload)

        assert result["tools"][0]["name"] == "mcp_get_weather"

    def test_transform_request_replaces_opencode(self, provider):
        """Test that OpenCode references are replaced in system prompt."""
        payload = {"system": "You are OpenCode, an AI assistant."}

        result = provider._transform_request(payload)

        assert "OpenCode" not in result["system"]
        assert "Claude Code" in result["system"]

    def test_transform_response_removes_prefix(self, provider):
        """Test that mcp_ prefix is removed from response."""
        text = '{"name": "mcp_get_weather", "input": {}}'

        result = provider._transform_response(text)

        assert '"name": "get_weather"' in result


class TestAnthropicOAuthProviderToolConversion:
    """Tests for tool format conversion."""

    def test_convert_tools_empty(self, provider):
        """Test empty tools list."""
        result = provider._convert_tools([])
        assert result == []

    def test_convert_tools_single_function(self, provider):
        """Test single function conversion to Anthropic format."""
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]

        result = provider._convert_tools(openai_tools)

        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather for a location"
        assert "input_schema" in result[0]


class TestAnthropicOAuthProviderGetResponse:
    """Tests for get_response method."""

    @pytest.mark.asyncio
    async def test_get_response_success(self, provider):
        """Test successful API response."""
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {"content": [{"type": "text", "text": "Hello there!"}]}
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_session_class.return_value = mock_session

            response = await provider.get_response(messages)

            assert response == "Hello there!"

    @pytest.mark.asyncio
    async def test_get_response_includes_system_prefix(self, provider):
        """Test that API request includes Claude Code system prefix."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps({"content": [{"type": "text", "text": "Response"}]})
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_session_class.return_value = mock_session

            await provider.get_response(messages)

            # Verify post was called
            call_args = mock_session.post.call_args
            assert call_args is not None
            payload = call_args.kwargs.get("json", {})

            # System should be array with Claude Code prefix first
            assert isinstance(payload["system"], list)
            assert payload["system"][0]["text"] == CLAUDE_CODE_SYSTEM_PREFIX

    @pytest.mark.asyncio
    async def test_get_response_with_tool_use(self, provider):
        """Test handling of tool_use response blocks."""
        messages = [{"role": "user", "content": "What's the weather?"}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "content": [
                        {"type": "text", "text": "Let me check"},
                        {
                            "type": "tool_use",
                            "id": "tool_123",
                            "name": "get_weather",
                            "input": {"location": "NYC"},
                        },
                    ]
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_session_class.return_value = mock_session

            response = await provider.get_response(messages)

            assert "Let me check" in response
            assert "tool_use" in response
            assert "get_weather" in response


class TestAnthropicOAuthProviderConstants:
    """Tests for provider constants."""

    def test_claude_code_prefix_exists(self):
        """Test that Claude Code system prefix is defined."""
        assert "Claude Code" in CLAUDE_CODE_SYSTEM_PREFIX
        assert "Anthropic" in CLAUDE_CODE_SYSTEM_PREFIX

    def test_beta_flags_include_oauth(self):
        """Test that beta flags include OAuth flag."""
        assert "oauth-2025-04-20" in ANTHROPIC_BETA_FLAGS
        assert "interleaved-thinking" in ANTHROPIC_BETA_FLAGS

    def test_api_url_is_anthropic(self):
        """Test that API URL points to Anthropic with beta param."""
        assert "anthropic.com" in AnthropicOAuthProvider.API_URL
        assert "beta=true" in AnthropicOAuthProvider.API_URL

    def test_user_agent_matches_claude_cli(self):
        """Test that user agent identifies as claude-cli."""
        assert "claude-cli" in USER_AGENT


class TestAnthropicOAuthProviderStreaming:
    """Tests for Anthropic OAuth streaming event parsing."""

    def test_unprefix_tool_name(self, provider):
        """Tool names from stream should be de-prefixed."""
        assert provider._unprefix_tool_name("mcp_get_weather") == "get_weather"
        assert provider._unprefix_tool_name("get_weather") == "get_weather"

    def test_extract_stream_chunks_text_delta(self, provider):
        """Text stream delta should map to text chunk."""
        pending_tools = {}
        event = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "hello"},
        }

        chunks = provider._extract_stream_chunks(event, pending_tools)
        assert chunks == [{"type": "text", "content": "hello"}]

    def test_extract_stream_chunks_tool_use_and_json(self, provider):
        """Tool stream blocks should assemble to normalized tool_call."""
        pending_tools = {}
        start_event = {
            "type": "content_block_start",
            "index": 2,
            "content_block": {
                "type": "tool_use",
                "id": "tool_1",
                "name": "mcp_get_weather",
            },
        }
        delta_event = {
            "type": "content_block_delta",
            "index": 2,
            "delta": {
                "type": "input_json_delta",
                "partial_json": '{"location":"Krakow"}',
            },
        }
        stop_event = {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
        }

        assert provider._extract_stream_chunks(start_event, pending_tools) == []
        assert provider._extract_stream_chunks(delta_event, pending_tools) == []

        chunks = provider._extract_stream_chunks(stop_event, pending_tools)
        assert chunks == [
            {
                "type": "tool_call",
                "name": "get_weather",
                "args": {"location": "Krakow"},
                "id": "tool_1",
            }
        ]
