"""Tests for channel runtime config normalization."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from custom_components.homeclaw.channels.config import build_channel_runtime_config


def _as_hass(value: Any) -> Any:
    return cast(Any, value)


class _FakeConfigEntries:
    def __init__(self, entries):
        self._entries = entries

    def async_entries(self, domain):
        if domain != "discord":
            return []
        return self._entries


class _FakeHass:
    def __init__(self, entries=None):
        self.config_entries = _FakeConfigEntries(entries or [])

    async def async_add_executor_job(self, target, *args):
        return target(*args)


@pytest.mark.asyncio
class TestBuildChannelRuntimeConfig:
    async def test_legacy_discord_token_auto_enables_channel(self):
        hass = _FakeHass()

        config = await build_channel_runtime_config(
            _as_hass(hass),
            {
                "discord_bot_token": "abc123",
            },
        )

        discord = config["channel_discord"]
        assert discord["bot_token"] == "abc123"
        assert discord["enabled"] is True

    async def test_reuses_token_from_ha_discord_integration(self):
        entry = SimpleNamespace(data={"api_token": "ha-token"})
        hass = _FakeHass([entry])

        config = await build_channel_runtime_config(_as_hass(hass), {})

        discord = config["channel_discord"]
        assert discord["bot_token"] == "ha-token"
        assert discord["enabled"] is True

    async def test_explicit_disabled_wins_even_with_token(self):
        hass = _FakeHass()
        config = await build_channel_runtime_config(
            _as_hass(hass),
            {
                "channel_discord": {"enabled": False},
                "discord_bot_token": "abc123",
            },
        )

        discord = config["channel_discord"]
        assert discord["enabled"] is False
        assert discord["bot_token"] == "abc123"

    async def test_normalizes_legacy_channel_lists(self):
        hass = _FakeHass()

        config = await build_channel_runtime_config(
            _as_hass(hass),
            {
                "discord_auto_respond_channels": "c1,c2\nc3",
                "discord_allowed_ids": ["u1", "  u2  ", ""],
            },
        )

        discord = config["channel_discord"]
        assert discord["auto_respond_channels"] == ["c1", "c2", "c3"]
        assert discord["allowed_ids"] == ["u1", "u2"]

    async def test_preserves_explicit_channel_discord_config(self):
        hass = _FakeHass([SimpleNamespace(data={"api_token": "ha-token"})])

        config = await build_channel_runtime_config(
            _as_hass(hass),
            {
                "channel_discord": {
                    "enabled": True,
                    "bot_token": "custom-token",
                    "group_policy": "open",
                }
            },
        )

        discord = config["channel_discord"]
        assert discord["enabled"] is True
        assert discord["bot_token"] == "custom-token"
        assert discord["group_policy"] == "open"

    async def test_merges_external_user_mapping_into_channel_config(self):
        hass = _FakeHass()

        config = await build_channel_runtime_config(
            _as_hass(hass),
            {
                "external_user_mapping": {"d1": "ha1"},
                "channel_discord": {
                    "user_mapping": {"d2": "ha2"},
                },
            },
        )

        discord = config["channel_discord"]
        assert discord["user_mapping"]["d1"] == "ha1"
        assert discord["user_mapping"]["d2"] == "ha2"
        assert discord["external_user_mapping"]["d1"] == "ha1"
