"""Helpers for building channel runtime configuration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_DISCORD_DEFAULTS_PATH = Path(__file__).parent / "discord" / "defaults.json"


async def build_channel_runtime_config(
    hass: HomeAssistant,
    base_config: dict[str, Any],
) -> dict[str, Any]:
    """Build normalized channel config from integration entry data/options.

    Applies Discord defaults, supports legacy top-level keys, and can reuse
    the token from HA's official ``discord`` integration when not explicitly
    configured in Homeclaw.
    """
    config = dict(base_config)
    config["channel_discord"] = await _build_discord_config(hass, config)
    return config


async def _build_discord_config(
    hass: HomeAssistant,
    raw_config: dict[str, Any],
) -> dict[str, Any]:
    """Build Discord channel config from defaults + user overrides."""
    defaults = await _load_discord_defaults(hass)

    raw_channel = raw_config.get("channel_discord", {})
    has_explicit_enabled = isinstance(raw_channel, dict) and "enabled" in raw_channel
    has_explicit_auto_respond = isinstance(raw_channel, dict) and (
        "auto_respond_channels" in raw_channel
    )
    has_explicit_allowed_ids = (
        isinstance(raw_channel, dict) and "allowed_ids" in raw_channel
    )

    channel_cfg = dict(defaults)
    if isinstance(raw_channel, dict):
        channel_cfg.update(raw_channel)

    if not has_explicit_auto_respond and raw_config.get(
        "discord_auto_respond_channels"
    ):
        channel_cfg["auto_respond_channels"] = _normalize_string_list(
            raw_config.get("discord_auto_respond_channels")
        )

    if not has_explicit_allowed_ids and raw_config.get("discord_allowed_ids"):
        channel_cfg["allowed_ids"] = _normalize_string_list(
            raw_config.get("discord_allowed_ids")
        )

    token = str(channel_cfg.get("bot_token", "")).strip()
    if not token:
        token = str(raw_config.get("discord_bot_token", "")).strip()
    if not token:
        token = _get_ha_discord_token(hass)

    if token:
        channel_cfg["bot_token"] = token

    if has_explicit_enabled:
        channel_cfg["enabled"] = bool(channel_cfg.get("enabled"))
    elif "discord_enabled" in raw_config:
        channel_cfg["enabled"] = bool(raw_config.get("discord_enabled"))
    else:
        channel_cfg["enabled"] = bool(token)

    return channel_cfg


async def _load_discord_defaults(hass: HomeAssistant) -> dict[str, Any]:
    """Load Discord defaults JSON with safe fallback."""
    try:
        loaded = await hass.async_add_executor_job(_read_discord_defaults_file)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        _LOGGER.exception("Failed loading Discord defaults JSON")

    return {
        "enabled": False,
        "bot_token": "",
        "auto_respond_channels": [],
        "allowed_ids": [],
        "max_concurrent": 3,
        "rate_limit": 10,
        "rate_limit_hour": 60,
        "group_policy": "allowlist",
        "require_mention": True,
        "dm_policy": "pairing",
    }


def _read_discord_defaults_file() -> dict[str, Any]:
    """Read Discord defaults JSON from disk (executor-only)."""
    with _DISCORD_DEFAULTS_PATH.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    return loaded if isinstance(loaded, dict) else {}


def _normalize_string_list(raw: Any) -> list[str]:
    """Normalize list/CSV/newline values into a list of strings."""
    if raw is None:
        return []
    if isinstance(raw, str):
        values = [line.strip() for line in raw.replace(",", "\n").splitlines()]
    else:
        values = [str(v).strip() for v in raw]
    return [v for v in values if v]


def _get_ha_discord_token(hass: HomeAssistant) -> str:
    """Get token from HA official Discord integration config entry."""
    try:
        entries = hass.config_entries.async_entries("discord")
    except Exception:
        return ""

    for entry in entries:
        data = getattr(entry, "data", {}) or {}
        token = str(data.get(CONF_API_TOKEN, "")).strip()
        if token:
            return token
    return ""
