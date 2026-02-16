"""ChannelManager — lifecycle owner for all external chat channels.

Manages startup, shutdown, and health monitoring of enabled channels.
Stored at ``hass.data[DOMAIN]["channel_manager"]`` and wired into the
integration's ``async_setup_entry`` / ``async_unload_entry`` lifecycle.

Usage in ``__init__.py``::

    from .channels.manager import ChannelManager
    from .channels.intake import MessageIntake

    intake = MessageIntake(hass)
    manager = ChannelManager(hass, intake)
    await manager.async_setup(channel_config)
    hass.data[DOMAIN]["channel_manager"] = manager
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .base import Channel, ChannelRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .intake import MessageIntake

_LOGGER = logging.getLogger(__name__)


class ChannelManager:
    """Manages channel lifecycle, independent of per-provider config entries.

    Owns startup and shutdown of all enabled channels.  Provides a
    ``get_status()`` method for health monitoring and WS API queries.

    Args:
        hass: Home Assistant instance.
        intake: Shared ``MessageIntake`` for message processing.
    """

    def __init__(self, hass: HomeAssistant, intake: MessageIntake) -> None:
        self._hass = hass
        self._intake = intake
        self._channels: dict[str, Channel] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self, config: dict[str, Any]) -> None:
        """Start all enabled channels.

        Iterates over all registered channel classes.  For each one, checks
        ``config["channel_{id}"]["enabled"]``.  If ``True``, instantiates the
        channel and calls ``async_setup()``.  Failures in one channel do
        not prevent other channels from starting.

        Args:
            config: Full integration config (or options dict).
                    Expected keys like ``channel_telegram``, ``channel_discord``, etc.
        """
        for channel_id, channel_cls in ChannelRegistry.all().items():
            ch_config = config.get(f"channel_{channel_id}", {})
            if not ch_config.get("enabled", False):
                _LOGGER.debug("Channel %s not enabled, skipping", channel_id)
                continue

            channel = channel_cls(self._hass, self._intake, ch_config)
            try:
                await channel.async_setup()
                self._channels[channel_id] = channel
                _LOGGER.info("Channel %s started successfully", channel_id)
            except Exception:
                _LOGGER.exception("Failed to start channel %s", channel_id)

    async def async_teardown(self) -> None:
        """Stop all running channels (safe for HA unload).

        Each channel's ``async_teardown()`` is called individually so that
        a failure in one channel does not prevent others from shutting down.
        """
        for channel_id, channel in self._channels.items():
            try:
                await channel.async_teardown()
                _LOGGER.debug("Channel %s stopped", channel_id)
            except Exception:
                _LOGGER.exception("Error stopping channel %s", channel_id)
        self._channels.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Health status of all running channels.

        Each channel's ``is_available`` property is read inside a
        try/except so that a broken channel does not crash the
        entire status query.

        Returns:
            Dict mapping channel_id to ``{available: bool, name: str}``.
        """
        result: dict[str, Any] = {}
        for cid, ch in self._channels.items():
            try:
                available = ch.is_available
            except Exception:
                _LOGGER.exception("Error checking availability for channel %s", cid)
                available = False
            result[cid] = {"available": available, "name": ch.name}
        return result

    def get_channel(self, channel_id: str) -> Channel | None:
        """Return a running channel instance by ID, or None."""
        return self._channels.get(channel_id)

    @property
    def active_channels(self) -> list[str]:
        """List IDs of all currently running channels."""
        return list(self._channels.keys())
