from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.providers.grok_oauth.auth import DeviceCode, OAuthRefreshError, TokenSet

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def enable_custom_integrations(auto_enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def bypass_setup_entry():
    with patch("custom_components.homeclaw.async_setup_entry", return_value=True):
        yield


def _device() -> DeviceCode:
    return DeviceCode(
        device_code="dev",
        user_code="WXYZ-1234",
        verification_uri="https://auth.x.ai/device",
        verification_uri_complete="https://auth.x.ai/device?user_code=WXYZ-1234",
        expires_in=300.0,
        interval=5.0,
    )


async def test_user_step_routes_to_grok_progress(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    device = _device()
    tokens = TokenSet("A", "R", 9e9)
    with (
        patch(
            "custom_components.homeclaw.config_flow.request_device_code",
            AsyncMock(return_value=device),
        ),
        patch(
            "custom_components.homeclaw.config_flow.poll_device_code_token",
            AsyncMock(return_value=tokens),
        ),
        patch(
            "custom_components.homeclaw.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "grok_oauth"},
        )
        if result["type"] == FlowResultType.SHOW_PROGRESS:
            await hass.async_block_till_done()
            result = await hass.config_entries.flow.async_configure(result["flow_id"])
            if result["type"] == FlowResultType.SHOW_PROGRESS_DONE:
                result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Homeclaw (Grok)"
    assert result["data"]["ai_provider"] == "grok_oauth"
    assert result["data"]["grok_oauth"]["access_token"] == "A"
    assert result["data"]["grok_oauth"]["refresh_token"] == "R"


async def test_device_code_request_failure_aborts(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with (
        patch(
            "custom_components.homeclaw.config_flow.request_device_code",
            AsyncMock(side_effect=OAuthRefreshError("nope", is_permanent=True)),
        ),
        patch(
            "custom_components.homeclaw.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "grok_oauth"},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "oauth_failed"


async def test_poll_failure_shows_retry_form(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    device = _device()
    with (
        patch(
            "custom_components.homeclaw.config_flow.request_device_code",
            AsyncMock(return_value=device),
        ),
        patch(
            "custom_components.homeclaw.config_flow.poll_device_code_token",
            AsyncMock(side_effect=OAuthRefreshError("denied", is_permanent=True)),
        ),
        patch(
            "custom_components.homeclaw.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "grok_oauth"},
        )
        if result["type"] == FlowResultType.SHOW_PROGRESS:
            await hass.async_block_till_done()
            result = await hass.config_entries.flow.async_configure(result["flow_id"])
            if result["type"] == FlowResultType.SHOW_PROGRESS_DONE:
                result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "grok_oauth_failed"
