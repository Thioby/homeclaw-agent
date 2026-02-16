"""Tests for Discord connection status tool."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from custom_components.homeclaw.tools.channel_status import CheckDiscordConnection


class _FakeConfigEntries:
    def __init__(self, by_domain: dict[str, list[object]]):
        self._by_domain = by_domain

    def async_entries(self, domain: str) -> list[object]:
        return self._by_domain.get(domain, [])


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
