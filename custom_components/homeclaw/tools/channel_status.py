"""Channel status tools for Homeclaw."""

from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.const import CONF_API_TOKEN

from ..channels.base import ChannelTarget
from ..const import DOMAIN
from ..channels.config import build_channel_runtime_config
from ..channels.discord.helpers import get_last_target
from ..channels.discord.pairing import (
    consume_request,
    get_request_by_code,
    persist_pairing,
)
from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)


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


@ToolRegistry.register
class GetDiscordLastTarget(Tool):
    """Return last known Discord target for current Homeclaw user."""

    id = "get_discord_last_target"
    description = "Get the latest Discord target used by this user (channel/DM) for reliable reply routing."
    category = ToolCategory.HOME_ASSISTANT
    parameters = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Return last target metadata for current user."""
        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        user_id = str(kwargs.get("_user_id", "")).strip()
        if not user_id:
            return ToolResult(
                output="Missing user context",
                error="missing_user_context",
                success=False,
            )

        target = get_last_target(self.hass, user_id)
        if not target:
            payload = {
                "found": False,
                "summary": "No recent Discord target found for this user.",
            }
            return ToolResult(output=json.dumps(payload), metadata=payload)

        payload = {
            "found": True,
            "target_id": str(target.get("target_id", "")),
            "sender_id": str(target.get("sender_id", "")),
            "is_group": bool(target.get("is_group", False)),
            "summary": "Recent Discord target is available.",
        }
        return ToolResult(output=json.dumps(payload), metadata=payload)


@ToolRegistry.register
class SendDiscordMessage(Tool):
    """Send a message through Homeclaw Discord channel with confirmation."""

    id = "send_discord_message"
    description = (
        "Send a Discord message via Homeclaw and return delivery confirmation. "
        "Use target_id explicitly or fallback to the user's last Discord target."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="message",
            type="str",
            description="Message text to send",
            required=True,
        ),
        ToolParameter(
            name="target_id",
            type="str",
            description="Discord channel ID; optional if last target exists",
            required=False,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Send message to Discord target and return confirmed status."""
        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        text = str(kwargs.get("message", "")).strip()
        if not text:
            return ToolResult(
                output="Parameter 'message' is required",
                error="missing_message",
                success=False,
            )

        manager = self.hass.data.get(DOMAIN, {}).get("channel_manager")
        discord_channel = manager.get_channel("discord") if manager else None
        if not discord_channel:
            return ToolResult(
                output="Discord channel is not active",
                error="discord_channel_inactive",
                success=False,
            )

        user_id = str(kwargs.get("_user_id", "")).strip()
        target_id = str(kwargs.get("target_id", "")).strip()
        if not target_id and user_id:
            last = get_last_target(self.hass, user_id)
            if isinstance(last, dict):
                target_id = str(last.get("target_id", "")).strip()
                _LOGGER.debug(
                    "send_discord_message uses last target_id=%s for user=%s",
                    target_id,
                    user_id,
                )

        if not target_id:
            return ToolResult(
                output="Missing target_id and no last Discord target found",
                error="missing_target",
                success=False,
            )

        try:
            await discord_channel.send_response(
                ChannelTarget(channel_id="discord", target_id=target_id),
                text,
            )
            _LOGGER.info(
                "send_discord_message delivered to target=%s len=%s",
                target_id,
                len(text),
            )
        except Exception as err:
            _LOGGER.warning(
                "send_discord_message failed target=%s error=%s",
                target_id,
                err,
            )
            return ToolResult(
                output=f"Discord send failed: {err}",
                error="discord_send_failed",
                success=False,
            )

        payload = {
            "success": True,
            "target_id": target_id,
            "delivered": True,
            "summary": "Discord message delivered.",
        }
        return ToolResult(output=json.dumps(payload), metadata=payload)


@ToolRegistry.register
class ConfirmDiscordPairing(Tool):
    """Confirm Discord pairing code and bind sender to current HA user."""

    id = "confirm_discord_pairing"
    description = "Confirm a Discord pairing code and connect that Discord user with the current Homeclaw user."
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="code",
            type="str",
            description="6-digit pairing code from Discord DM",
            required=True,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Confirm pairing code and persist mapping/allowlist."""
        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        ha_user_id = str(kwargs.get("_user_id", "")).strip()
        if not ha_user_id:
            return ToolResult(
                output="Missing user context",
                error="missing_user_context",
                success=False,
            )

        code = str(kwargs.get("code", "")).strip()
        request = get_request_by_code(self.hass, code)
        if not request:
            return ToolResult(
                output="Pairing code is invalid or expired",
                error="invalid_pairing_code",
                success=False,
            )

        sender_id = str(request.get("sender_id", "")).strip()
        if not sender_id:
            consume_request(self.hass, code)
            return ToolResult(
                output="Pairing request is invalid",
                error="invalid_pairing_request",
                success=False,
            )

        persisted = await persist_pairing(
            self.hass,
            ha_user_id=ha_user_id,
            sender_id=sender_id,
        )
        consume_request(self.hass, code)

        manager = self.hass.data.get(DOMAIN, {}).get("channel_manager")
        discord_channel = manager.get_channel("discord") if manager else None
        if discord_channel and request.get("target_id"):
            try:
                await discord_channel.send_response(
                    ChannelTarget(
                        channel_id="discord",
                        target_id=str(request.get("target_id", "")),
                    ),
                    "Pairing completed. You can now chat with Homeclaw from Discord.",
                )
            except Exception as err:
                _LOGGER.debug("Failed to send Discord pairing confirmation: %s", err)

        payload = {
            "success": True,
            "paired": True,
            "sender_id": persisted["sender_id"],
            "ha_user_id": persisted["ha_user_id"],
            "summary": "Discord pairing completed successfully.",
        }
        return ToolResult(output=json.dumps(payload), metadata=payload)
