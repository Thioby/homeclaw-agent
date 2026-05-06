"""Integration tests for AnthropicOAuthProvider.

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.providers.anthropic_oauth import AnthropicOAuthProvider
from custom_components.homeclaw.providers.anthropic_oauth.auth import OAuthRefreshError, TokenSet


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.data = {
        "anthropic_oauth": {
            "access_token": "ACCESS",
            "refresh_token": "REFRESH",
            "expires_at": time.time() + 3600,
        }
    }
    return entry


@pytest.fixture
def provider(mock_hass, mock_config_entry):
    return AnthropicOAuthProvider(mock_hass, {"config_entry": mock_config_entry, "model": "claude-sonnet-4-20250514"})


class TestInit:
    def test_default_model(self, mock_hass, mock_config_entry):
        p = AnthropicOAuthProvider(mock_hass, {"config_entry": mock_config_entry})
        assert p._model == AnthropicOAuthProvider.DEFAULT_MODEL

    def test_custom_model(self, mock_hass, mock_config_entry):
        p = AnthropicOAuthProvider(mock_hass, {"config_entry": mock_config_entry, "model": "claude-opus-4-1"})
        assert p._model == "claude-opus-4-1"

    def test_supports_tools(self, provider):
        assert provider.supports_tools is True


class TestTokenManagement:
    pytestmark = pytest.mark.asyncio

    def test_read_oauth_data_returns_fresh(self, provider, mock_config_entry):
        # Simulate config_entry mutation between reads
        mock_config_entry.data = {"anthropic_oauth": {"access_token": "NEW", "refresh_token": "RNEW", "expires_at": 9e9}}
        result = provider._read_oauth_data()
        assert result["access_token"] == "NEW"

    async def test_get_valid_access_token_cached(self, provider):
        # Token valid in window — no refresh
        token = await provider._get_valid_access_token()
        assert token == "ACCESS"

    async def test_get_valid_access_token_triggers_refresh(self, provider, mock_config_entry):
        mock_config_entry.data = {
            "anthropic_oauth": {
                "access_token": "OLD",
                "refresh_token": "REFRESH",
                "expires_at": time.time() - 1000,  # already expired
            }
        }
        new_tokens = TokenSet("FRESH", "NEW_REFRESH", time.time() + 3600)
        with patch.object(provider._refresh_gate, "refresh", AsyncMock(return_value=new_tokens)):
            token = await provider._get_valid_access_token()
        assert token == "FRESH"
        # Verify persistence call
        provider.hass.config_entries.async_update_entry.assert_called_once()
        call_args = provider.hass.config_entries.async_update_entry.call_args
        assert call_args.kwargs["data"]["anthropic_oauth"]["access_token"] == "FRESH"
        assert call_args.kwargs["data"]["anthropic_oauth"]["refresh_token"] == "NEW_REFRESH"

    async def test_permanent_failure_triggers_reauth(self, provider, mock_config_entry):
        mock_config_entry.data = {"anthropic_oauth": {"access_token": "", "refresh_token": "", "expires_at": 0}}
        with patch.object(
            provider._refresh_gate,
            "refresh",
            AsyncMock(side_effect=OAuthRefreshError("dead", is_permanent=True)),
        ):
            with pytest.raises(OAuthRefreshError):
                await provider._get_valid_access_token()
        mock_config_entry.async_start_reauth.assert_called_once_with(provider.hass)


class TestGetResponse:
    pytestmark = pytest.mark.asyncio

    async def test_happy_path_assembles_correct_request(self, provider):
        with patch.object(provider, "_get_valid_access_token", AsyncMock(return_value="ACCESS")):
            ctx = AsyncMock()
            ctx.__aenter__.return_value.status = 200
            ctx.__aenter__.return_value.text = AsyncMock(
                return_value=json.dumps(
                    {
                        "content": [{"type": "text", "text": "ok"}],
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                )
            )
            captured = {}

            def capture_post(url, headers=None, json=None, timeout=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return ctx

            session_ctx = AsyncMock()
            session_mock = MagicMock()
            session_mock.post = MagicMock(side_effect=capture_post)
            session_ctx.__aenter__.return_value = session_mock

            with patch("aiohttp.ClientSession", return_value=session_ctx):
                await provider.get_response(
                    [{"role": "user", "content": "hello"}],
                )

        # Assertions on captured payload/headers
        assert "?beta=true" in captured["url"]
        assert captured["headers"]["authorization"] == "Bearer ACCESS"
        assert "oauth-2025-04-20" in captured["headers"]["anthropic-beta"]
        assert captured["headers"]["user-agent"] == "claude-cli/2.1.87 (external, cli)"
        # System should be a list with billing + identity
        sys_blocks = captured["json"]["system"]
        assert sys_blocks[0]["text"].startswith("x-anthropic-billing-header:")
        assert "Claude Agent SDK" in sys_blocks[1]["text"]
