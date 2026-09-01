from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.providers.grok_oauth import GrokOAuthProvider, is_oauth_zero_cost_provider
from custom_components.homeclaw.providers.grok_oauth.auth import OAuthRefreshError, TokenSet
from custom_components.homeclaw.providers.grok_oauth.constants import (
    CHAT_COMPLETIONS_URL,
    CLIENT_IDENTIFIER,
    CLIENT_VERSION,
    TOKEN_AUTH_VALUE,
)


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
        "grok_oauth": {
            "access_token": "ACCESS",
            "refresh_token": "REFRESH",
            "expires_at": time.time() + 3600,
        }
    }
    return entry


@pytest.fixture
def provider(mock_hass, mock_config_entry):
    return GrokOAuthProvider(mock_hass, {"config_entry": mock_config_entry, "model": "grok-4.6"})


class TestInit:
    def test_default_model(self, mock_hass, mock_config_entry):
        p = GrokOAuthProvider(mock_hass, {"config_entry": mock_config_entry})
        assert p._model == "grok-4.6"

    def test_custom_model(self, mock_hass, mock_config_entry):
        p = GrokOAuthProvider(mock_hass, {"config_entry": mock_config_entry, "model": "grok-4.5"})
        assert p._model == "grok-4.5"

    def test_supports_tools(self, provider):
        assert provider.supports_tools is True

    def test_api_url(self, provider):
        assert provider.api_url == CHAT_COMPLETIONS_URL


class TestHeaders:
    def test_cli_identity_headers(self, provider):
        headers = provider._build_headers()
        assert headers["Authorization"] == "Bearer ACCESS"
        assert headers["X-XAI-Token-Auth"] == TOKEN_AUTH_VALUE
        assert headers["x-grok-client-identifier"] == CLIENT_IDENTIFIER
        assert headers["x-grok-client-version"] == CLIENT_VERSION
        assert headers["x-grok-model-override"] == "grok-4.6"

    def test_payload_drops_reasoning_effort(self, provider):
        payload = provider._build_payload(
            [{"role": "user", "content": "hi"}],
            reasoning=True,
        )
        assert "reasoning_effort" not in payload
        assert payload["model"] == "grok-4.6"


class TestTokenManagement:
    pytestmark = pytest.mark.asyncio

    async def test_read_oauth_data_returns_fresh(self, provider, mock_config_entry):
        mock_config_entry.data = {"grok_oauth": {"access_token": "NEW", "refresh_token": "RNEW", "expires_at": 9e9}}
        result = provider._read_oauth_data()
        assert result["access_token"] == "NEW"

    async def test_get_valid_access_token_cached(self, provider):
        token = await provider._get_valid_access_token()
        assert token == "ACCESS"

    async def test_get_valid_access_token_triggers_refresh(self, provider, mock_config_entry):
        mock_config_entry.data = {
            "grok_oauth": {
                "access_token": "OLD",
                "refresh_token": "REFRESH",
                "expires_at": time.time() - 1000,
            }
        }
        new_tokens = TokenSet("FRESH", "NEW_REFRESH", time.time() + 3600)
        with patch.object(provider._refresh_gate, "refresh", AsyncMock(return_value=new_tokens)):
            token = await provider._get_valid_access_token()
        assert token == "FRESH"
        provider.hass.config_entries.async_update_entry.assert_called_once()
        call_args = provider.hass.config_entries.async_update_entry.call_args
        assert call_args.kwargs["data"]["grok_oauth"]["access_token"] == "FRESH"
        assert call_args.kwargs["data"]["grok_oauth"]["refresh_token"] == "NEW_REFRESH"

    async def test_permanent_failure_triggers_reauth(self, provider, mock_config_entry):
        mock_config_entry.data = {"grok_oauth": {"access_token": "", "refresh_token": "", "expires_at": 0}}
        with patch.object(
            provider._refresh_gate,
            "refresh",
            AsyncMock(side_effect=OAuthRefreshError("dead", is_permanent=True)),
        ):
            with pytest.raises(OAuthRefreshError):
                await provider._get_valid_access_token()
        mock_config_entry.async_start_reauth.assert_called_once_with(provider.hass)

    async def test_entitlement_failure_does_not_reauth(self, provider, mock_config_entry):
        mock_config_entry.data = {"grok_oauth": {"access_token": "", "refresh_token": "R", "expires_at": 0}}
        with patch.object(
            provider._refresh_gate,
            "refresh",
            AsyncMock(side_effect=OAuthRefreshError("nope", is_permanent=True, is_entitlement=True)),
        ):
            with pytest.raises(OAuthRefreshError):
                await provider._get_valid_access_token()
        mock_config_entry.async_start_reauth.assert_not_called()


class TestGetResponse:
    pytestmark = pytest.mark.asyncio

    async def test_collects_stream_text(self, provider):
        async def fake_stream(_messages, **_kwargs):
            yield {"type": "text", "content": "hel"}
            yield {"type": "text", "content": "lo"}

        with patch.object(provider, "get_response_stream", fake_stream):
            result = await provider.get_response([{"role": "user", "content": "hi"}])
        assert result == "hello"

    async def test_collects_tool_calls(self, provider):
        async def fake_stream(_messages, **_kwargs):
            yield {"type": "tool_call", "id": "1", "name": "turn_on", "args": {"entity": "light.x"}}

        with patch.object(provider, "get_response_stream", fake_stream):
            result = await provider.get_response([{"role": "user", "content": "hi"}])
        parsed = json.loads(result)
        assert parsed["tool_calls"][0]["function"]["name"] == "turn_on"

    async def test_error_chunk_raises(self, provider):
        async def fake_stream(_messages, **_kwargs):
            yield {"type": "error", "message": "boom"}

        with patch.object(provider, "get_response_stream", fake_stream):
            with pytest.raises(RuntimeError, match="boom"):
                await provider.get_response([{"role": "user", "content": "hi"}])


class TestEntitlementRewrite:
    def test_rewrite_entitlement_error(self, provider):
        chunk = provider._rewrite_entitlement_error({"type": "error", "message": "GrokOAuthProvider API error 403: gated"})
        assert "not entitled" in chunk["message"]


class TestZeroCost:
    def test_grok_and_anthropic(self):
        assert is_oauth_zero_cost_provider("grok_oauth") is True
        assert is_oauth_zero_cost_provider("anthropic_oauth") is True
        assert is_oauth_zero_cost_provider("openai") is False
