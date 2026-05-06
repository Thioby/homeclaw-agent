"""Tests for Anthropic OAuth method-selection and API-key creation flow."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homeclaw.const import DOMAIN

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def enable_custom_integrations(auto_enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture(autouse=True)
def bypass_setup_entry():
    """Bypass entry setup."""
    with patch("custom_components.homeclaw.async_setup_entry", return_value=True):
        yield


def _make_authorize_mock(mode: str):
    """Return (authorize_mock, request_mock, pkce_mock) tuple."""
    mock_request = MagicMock()
    mock_request.url = f"http://auth-url-{mode}"
    mock_request.state = f"state-{mode}"
    mock_pkce = MagicMock()
    mock_pkce.verifier = f"verifier-{mode}"
    mock_pkce.challenge = f"challenge-{mode}"
    authorize_mock = MagicMock(return_value=(mock_request, mock_pkce))
    return authorize_mock, mock_request, mock_pkce


# ---------------------------------------------------------------------------
# async_step_anthropic_method
# ---------------------------------------------------------------------------


async def test_anthropic_method_shows_form(hass: HomeAssistant):
    """Selecting anthropic_oauth shows method-selection form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "anthropic_oauth"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_method"


async def test_anthropic_method_max_routes_to_oauth(hass: HomeAssistant):
    """Choosing 'max' in method step routes to existing anthropic_oauth step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "anthropic_oauth"},
    )
    assert result["step_id"] == "anthropic_method"

    authorize_mock, mock_request, mock_pkce = _make_authorize_mock("max")
    with patch(
        "custom_components.homeclaw.config_flow.authorize",
        authorize_mock,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"method": "max"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_oauth"
    assert result["description_placeholders"]["auth_url"] == "http://auth-url-max"
    authorize_mock.assert_called_once_with(mode="max")


async def test_anthropic_method_console_routes_to_create_key(hass: HomeAssistant):
    """Choosing 'console' in method step routes to create-key step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "anthropic_oauth"},
    )
    assert result["step_id"] == "anthropic_method"

    authorize_mock, mock_request, mock_pkce = _make_authorize_mock("console")
    with patch(
        "custom_components.homeclaw.config_flow.authorize",
        authorize_mock,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"method": "console"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_create_key"
    assert result["description_placeholders"]["auth_url"] == "http://auth-url-console"
    authorize_mock.assert_called_once_with(mode="console")


# ---------------------------------------------------------------------------
# async_step_anthropic_create_key
# ---------------------------------------------------------------------------


async def _init_to_create_key_form(hass: HomeAssistant):
    """Helper: navigate to the anthropic_create_key step and return flow_id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "anthropic_oauth"},
    )

    authorize_mock, _, _ = _make_authorize_mock("console")
    with patch("custom_components.homeclaw.config_flow.authorize", authorize_mock):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"method": "console"},
        )

    assert result["step_id"] == "anthropic_create_key"
    return result["flow_id"]


async def test_create_key_shows_auth_url(hass: HomeAssistant):
    """anthropic_create_key shows form with auth_url placeholder."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "anthropic_oauth"},
    )

    authorize_mock, mock_request, _ = _make_authorize_mock("console")
    with patch("custom_components.homeclaw.config_flow.authorize", authorize_mock):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"method": "console"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_create_key"
    assert "auth_url" in result["description_placeholders"]
    assert result["description_placeholders"]["auth_url"] == "http://auth-url-console"


async def test_create_key_empty_code_shows_error(hass: HomeAssistant):
    """Submitting empty code shows validation error."""
    flow_id = await _init_to_create_key_form(hass)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        user_input={"code": ""},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_create_key"
    assert "code" in result["errors"]


async def test_create_key_success_creates_anthropic_entry(hass: HomeAssistant):
    """Valid code exchange + create_api_key creates an 'anthropic' provider entry."""
    flow_id = await _init_to_create_key_form(hass)

    mock_tokens = MagicMock()
    mock_tokens.access_token = "at-abc"
    mock_tokens.refresh_token = "rt-abc"
    mock_tokens.expires_at = 9999.0

    mock_exchange = AsyncMock(return_value=mock_tokens)
    mock_create_key = AsyncMock(return_value="sk-ant-permanent-key")

    with (
        patch("custom_components.homeclaw.config_flow.exchange_code", mock_exchange),
        patch("custom_components.homeclaw.config_flow.create_api_key", mock_create_key),
        patch("aiohttp.ClientSession"),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            user_input={"code": "auth-code-123"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["ai_provider"] == "anthropic"
    assert result["data"]["anthropic_token"] == "sk-ant-permanent-key"
    mock_exchange.assert_called_once()
    mock_create_key.assert_called_once()


async def test_create_key_exchange_failure_shows_error(hass: HomeAssistant):
    """exchange_code raising OAuthRefreshError shows oauth_failed error."""
    from custom_components.homeclaw.providers.anthropic_oauth.auth import OAuthRefreshError

    flow_id = await _init_to_create_key_form(hass)

    mock_exchange = AsyncMock(side_effect=OAuthRefreshError("bad token", is_permanent=False))

    with (
        patch("custom_components.homeclaw.config_flow.exchange_code", mock_exchange),
        patch("aiohttp.ClientSession"),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            user_input={"code": "bad-code"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_create_key"
    assert result["errors"]["base"] == "oauth_failed"


async def test_create_key_api_key_creation_failure_shows_error(hass: HomeAssistant):
    """create_api_key raising OAuthRefreshError shows oauth_failed error."""
    from custom_components.homeclaw.providers.anthropic_oauth.auth import OAuthRefreshError

    flow_id = await _init_to_create_key_form(hass)

    mock_tokens = MagicMock()
    mock_tokens.access_token = "at-abc"
    mock_tokens.refresh_token = "rt-abc"
    mock_tokens.expires_at = 9999.0

    mock_exchange = AsyncMock(return_value=mock_tokens)
    mock_create_key = AsyncMock(side_effect=OAuthRefreshError("key creation failed", is_permanent=True))

    with (
        patch("custom_components.homeclaw.config_flow.exchange_code", mock_exchange),
        patch("custom_components.homeclaw.config_flow.create_api_key", mock_create_key),
        patch("aiohttp.ClientSession"),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            user_input={"code": "auth-code-456"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_create_key"
    assert result["errors"]["base"] == "oauth_failed"
