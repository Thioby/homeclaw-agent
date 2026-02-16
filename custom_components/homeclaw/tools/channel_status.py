"""Channel status tools for Homeclaw."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.const import CONF_API_TOKEN

from ..const import DOMAIN
from ..channels.config import build_channel_runtime_config
from .base import Tool, ToolCategory, ToolRegistry, ToolResult


@ToolRegistry.register
class CheckDiscordConnection(Tool):
    """Check Homeclaw Discord channel configuration and live connectivity."""

    id = "check_discord_connection"
    description = (
        "Check if Discord is connected for Homeclaw right now. "
        "Returns whether Discord is configured, enabled, and currently connected."
    )
    category = ToolCategory.HOME_ASSISTANT

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Return current Discord connection status."""
        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        merged_config, ha_discord_has_token = self._get_config_sources()
        runtime = await build_channel_runtime_config(self.hass, merged_config)
        discord_cfg = runtime.get("channel_discord", {})

        manager = self.hass.data.get(DOMAIN, {}).get("channel_manager")
        discord_channel = manager.get_channel("discord") if manager else None
        connected = bool(discord_channel and discord_channel.is_available)
        active = discord_channel is not None

        status = {
            "channel": "discord",
            "configured": bool(str(discord_cfg.get("bot_token", "")).strip()),
            "enabled": bool(discord_cfg.get("enabled", False)),
            "active": active,
            "connected": connected,
            "ha_discord_integration_has_token": ha_discord_has_token,
        }

        status["summary"] = self._build_summary(status)
        return ToolResult(output=json.dumps(status), metadata=status)

    def _get_config_sources(self) -> tuple[dict[str, Any], bool]:
        """Get merged Homeclaw config and HA Discord token flag."""
        merged: dict[str, Any] = {}
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            data = getattr(entry, "data", {}) or {}
            options = getattr(entry, "options", {}) or {}
            merged = {**data, **options}
            break

        ha_discord_has_token = False
        for entry in self.hass.config_entries.async_entries("discord"):
            data = getattr(entry, "data", {}) or {}
            if str(data.get(CONF_API_TOKEN, "")).strip():
                ha_discord_has_token = True
                break

        return merged, ha_discord_has_token

    @staticmethod
    def _build_summary(status: dict[str, Any]) -> str:
        """Create short natural-language status summary."""
        if status["connected"]:
            return "Discord connection is active."
        if status["enabled"] and status["configured"]:
            return "Discord is configured but not connected right now."
        if status["configured"]:
            return "Discord token is configured but channel is not enabled."
        if status["ha_discord_integration_has_token"]:
            return "HA Discord integration has a token, but Homeclaw channel is not active yet."
        return "Discord is not configured for Homeclaw."
