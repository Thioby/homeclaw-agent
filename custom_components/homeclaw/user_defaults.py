"""Centralized resolution of the agent / provider / model to use for a user.

All non-chat code paths (scheduler, heartbeat, Discord channel, background
emoji/title generation, ...) need the same fallback chain when picking which
AI agent to call. This module is the single source of truth for that chain so
the per-user "default selected model" is honored consistently.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_STORAGE_CACHE_PREFIX = f"{DOMAIN}_storage_"


async def resolve_user_agent(
    hass: "HomeAssistant",
    user_id: str = "",
    *,
    storage: Any | None = None,
    override_provider: str | None = None,
    override_model: str | None = None,
    fallback_to_first_agent: bool = True,
) -> tuple[Any | None, str | None, str | None]:
    """Resolve ``(agent, provider_name, model)`` honoring user preferences.

    Resolution order:
        1. ``override_provider`` / ``override_model`` arguments (e.g. job
           config, request message, channel config).
        2. The user's ``default_provider`` / ``default_model`` saved in
           ``SessionStorage`` preferences.
        3. If ``fallback_to_first_agent`` is ``True``: the first registered
           agent, with ``model=None`` (provider uses its own default).
           If ``False``: ``(None, None, None)`` so the caller can apply its
           own fallback (e.g. a channel-specific config default).

    Returns ``(None, None, None)`` when no agents are configured.
    """
    agents = hass.data.get(DOMAIN, {}).get("agents", {})
    if not agents:
        return None, None, None

    provider_name = override_provider
    model = override_model

    if not provider_name or not model:
        prefs = await _load_preferences(hass, user_id, storage=storage)
        if not provider_name:
            provider_name = prefs.get("default_provider")
        if not model:
            model = prefs.get("default_model")

    if provider_name and provider_name not in agents:
        _LOGGER.debug(
            "Preferred provider %r not in registered agents; falling back",
            provider_name,
        )
        provider_name = None
        model = None

    if not provider_name:
        if not fallback_to_first_agent:
            return None, None, None
        provider_name = next(iter(agents))
        model = None

    return agents[provider_name], provider_name, model


async def _load_preferences(
    hass: "HomeAssistant",
    user_id: str,
    *,
    storage: Any | None = None,
) -> dict[str, Any]:
    if storage is None and user_id:
        cache_key = f"{_STORAGE_CACHE_PREFIX}{user_id}"
        storage = hass.data.get(cache_key)
    if storage is None:
        return {}
    try:
        return await storage.get_preferences()
    except Exception as err:
        _LOGGER.debug("Failed to load preferences for user %s: %s", user_id, err)
        return {}
