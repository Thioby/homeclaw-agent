"""Tests for Discord connection status tool."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homeclaw.tools.channel_status import (
    CheckDiscordConnection,
    ConfirmDiscordPairing,
    GetDiscordLastTarget,
    SendDiscordMessage,
)


class _FakeConfigEntries:
    def __init__(self, by_domain: dict[str, list[object]]):
        self._by_domain = by_domain
        self._updated_options = None

    def async_entries(self, domain: str) -> list[object]:
        return self._by_domain.get(domain, [])

    def async_update_entry(self, entry: object, *, options=None, data=None):
        if options is not None:
            setattr(entry, "options", options)
            self._updated_options = options
        if data is not None:
            setattr(entry, "data", data)


class _FakeManager:
    def __init__(self, channel):
        self._channel = channel

    def get_channel(self, _channel_id: str):
        return self._channel


class _FakeHass:
    def __init__(self, by_domain: dict[str, list[object]], manager=None):
        self.config_entries = _FakeConfigEntries(by_domain)
        self.data = {"homeclaw": {}}
        if manager is not None:
            self.data["homeclaw"]["channel_manager"] = manager

    async def async_add_executor_job(self, target, *args):
        return target(*args)


@pytest.mark.asyncio
class TestCheckDiscordConnection:
    async def test_reports_connected_when_channel_is_available(self):
        homeclaw_entry = SimpleNamespace(
            data={"channel_discord": {"enabled": True, "bot_token": "token-1"}},
            options={},
        )
        channel = SimpleNamespace(is_available=True)
        hass = _FakeHass({"homeclaw": [homeclaw_entry]}, _FakeManager(channel))
        tool = CheckDiscordConnection(hass=hass)

        result = await tool.execute()
        payload = json.loads(result.output)

        assert result.success is True
        assert payload["connected"] is True
        assert payload["configured"] is True
        assert payload["summary"] == "Discord connection is active."

    async def test_uses_ha_discord_token_fallback(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        discord_entry = SimpleNamespace(data={"api_token": "ha-token"}, options={})
        hass = _FakeHass({"homeclaw": [homeclaw_entry], "discord": [discord_entry]})
        tool = CheckDiscordConnection(hass=hass)

        result = await tool.execute()
        payload = json.loads(result.output)

        assert payload["configured"] is True
        assert payload["enabled"] is True
        assert payload["connected"] is False
        assert payload["ha_discord_integration_has_token"] is True

    async def test_reports_not_configured(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        hass = _FakeHass({"homeclaw": [homeclaw_entry]})
        tool = CheckDiscordConnection(hass=hass)

        result = await tool.execute()
        payload = json.loads(result.output)

        assert payload["configured"] is False
        assert payload["enabled"] is False
        assert payload["connected"] is False
        assert payload["summary"] == "Discord is not configured for Homeclaw."

    async def test_returns_error_when_hass_missing(self):
        tool = CheckDiscordConnection(hass=None)
        result = await tool.execute()

        assert result.success is False
        assert result.error == "hass_not_available"


@pytest.mark.asyncio
class TestGetDiscordLastTarget:
    async def test_returns_last_target(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        hass = _FakeHass({"homeclaw": [homeclaw_entry]})
        hass.data["homeclaw_discord_last_targets"] = {
            "user-1": {"target_id": "chan-1", "sender_id": "s1", "is_group": False}
        }
        tool = GetDiscordLastTarget(hass=hass)

        result = await tool.execute(_user_id="user-1")
        payload = json.loads(result.output)

        assert result.success is True
        assert payload["found"] is True
        assert payload["target_id"] == "chan-1"

    async def test_returns_not_found(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        hass = _FakeHass({"homeclaw": [homeclaw_entry]})
        tool = GetDiscordLastTarget(hass=hass)

        result = await tool.execute(_user_id="missing")
        payload = json.loads(result.output)

        assert payload["found"] is False


@pytest.mark.asyncio
class TestSendDiscordMessage:
    async def test_sends_to_explicit_target(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        channel = SimpleNamespace(send_response=AsyncMock())
        hass = _FakeHass({"homeclaw": [homeclaw_entry]}, _FakeManager(channel))
        tool = SendDiscordMessage(hass=hass)

        result = await tool.execute(message="hello", target_id="chan-5")
        payload = json.loads(result.output)

        assert result.success is True
        assert payload["delivered"] is True
        channel.send_response.assert_awaited_once()

    async def test_falls_back_to_last_target(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        channel = SimpleNamespace(send_response=AsyncMock())
        hass = _FakeHass({"homeclaw": [homeclaw_entry]}, _FakeManager(channel))
        hass.data["homeclaw_discord_last_targets"] = {
            "user-2": {"target_id": "chan-9", "sender_id": "s2", "is_group": True}
        }
        tool = SendDiscordMessage(hass=hass)

        result = await tool.execute(message="hello", _user_id="user-2")
        payload = json.loads(result.output)

        assert result.success is True
        assert payload["target_id"] == "chan-9"

    async def test_returns_error_without_target(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        channel = SimpleNamespace(send_response=AsyncMock())
        hass = _FakeHass({"homeclaw": [homeclaw_entry]}, _FakeManager(channel))
        tool = SendDiscordMessage(hass=hass)

        result = await tool.execute(message="hello")

        assert result.success is False
        assert result.error == "missing_target"


@pytest.mark.asyncio
class TestConfirmDiscordPairing:
    async def test_confirm_pairing_success(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        channel = SimpleNamespace(send_response=AsyncMock())
        hass = _FakeHass({"homeclaw": [homeclaw_entry]}, _FakeManager(channel))
        hass.data["homeclaw_discord_pairing_requests"] = {
            "123456": {
                "code": "123456",
                "sender_id": "discord-user-1",
                "target_id": "dm-channel-1",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        }
        tool = ConfirmDiscordPairing(hass=hass)

        result = await tool.execute(code="123456", _user_id="ha-user-1")
        payload = json.loads(result.output)

        assert result.success is True
        assert payload["paired"] is True
        assert payload["sender_id"] == "discord-user-1"
        assert (
            homeclaw_entry.options["external_user_mapping"]["discord-user-1"]
            == "ha-user-1"
        )
        assert (
            "discord-user-1" in homeclaw_entry.options["channel_discord"]["allowed_ids"]
        )

    async def test_confirm_pairing_invalid_code(self):
        homeclaw_entry = SimpleNamespace(data={}, options={})
        hass = _FakeHass({"homeclaw": [homeclaw_entry]})
        tool = ConfirmDiscordPairing(hass=hass)

        result = await tool.execute(code="000000", _user_id="ha-user-1")

        assert result.success is False
        assert result.error == "invalid_pairing_code"
