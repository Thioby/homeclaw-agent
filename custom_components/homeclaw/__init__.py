"""The Homeclaw integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .agent_compat import HomeclawAgent
from .const import (
    CONF_RAG_ENABLED,
    DEFAULT_RAG_ENABLED,
    DOMAIN,
    PLATFORMS,
    VALID_PROVIDERS,
)
from .lifecycle import SubsystemLifecycle

_LOGGER = logging.getLogger(__name__)

# Config schema - this integration only supports config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Define service schema to accept a custom prompt
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("prompt"): cv.string,
    }
)

_SENSITIVE_KEYS = frozenset(
    {
        "llama_token",
        "openai_token",
        "gemini_token",
        "openrouter_token",
        "anthropic_token",
        "zai_token",
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Homeclaw component."""
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    _LOGGER.debug("Migrating config entry from version %s", entry.version)

    if entry.version == 1:
        # No migration needed for version 1
        return True

    # Future migrations would go here
    _LOGGER.info("Migration to version %s successful", entry.version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homeclaw from a config entry."""
    try:
        # Handle version compatibility
        if not hasattr(entry, "version") or entry.version != 1:
            _LOGGER.warning(
                "Config entry has version %s, expected 1. Attempting compatibility mode.",
                getattr(entry, "version", "unknown"),
            )

        config_data = dict(entry.data)

        # Validate required keys
        if "ai_provider" not in config_data:
            _LOGGER.error(
                "Config entry missing required 'ai_provider' key. Entry data: %s",
                config_data,
            )
            raise ConfigEntryNotReady("Config entry missing required 'ai_provider' key")

        # Initialize domain data structure
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {"agents": {}, "configs": {}}

        provider = config_data["ai_provider"]

        # Validate provider
        if provider not in VALID_PROVIDERS:
            _LOGGER.error("Unknown AI provider: %s", provider)
            raise ConfigEntryNotReady(f"Unknown AI provider: {provider}")

        # Store config for this provider
        hass.data[DOMAIN]["configs"][provider] = config_data

        # Create agent for this provider
        _LOGGER.debug(
            "Creating AI agent for provider %s with config: %s",
            provider,
            {k: v for k, v in config_data.items() if k not in _SENSITIVE_KEYS},
        )
        if provider in ("anthropic_oauth", "gemini_oauth"):
            hass.data[DOMAIN]["agents"][provider] = HomeclawAgent(
                hass, config_data, entry
            )
        else:
            hass.data[DOMAIN]["agents"][provider] = HomeclawAgent(hass, config_data)

        _LOGGER.info("Successfully set up Homeclaw for provider: %s", provider)

        # Connect existing RAG manager to new agent (if RAG was initialized by another entry)
        existing_rag_manager = hass.data[DOMAIN].get("rag_manager")
        if existing_rag_manager:
            hass.data[DOMAIN]["agents"][provider].set_rag_manager(existing_rag_manager)
            _LOGGER.info("Connected existing RAG manager to new agent: %s", provider)

    except KeyError as err:
        _LOGGER.error("Missing required configuration key: %s", err)
        raise ConfigEntryNotReady(f"Missing required configuration key: {err}")
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected error setting up Homeclaw")
        raise ConfigEntryNotReady(f"Error setting up Homeclaw: {err}")

    # Clean up old file uploads (> 7 days) at startup
    try:
        from .file_processor import cleanup_old_uploads

        await cleanup_old_uploads(hass)
    except Exception as err:
        _LOGGER.warning("Failed to clean up old uploads: %s", err)

    # Delegate subsystem init to lifecycle (proactive, channels, rag, services, ws, frontend)
    lifecycle = hass.data[DOMAIN].get("_lifecycle")
    if not lifecycle:
        lifecycle = SubsystemLifecycle()
        hass.data[DOMAIN]["_lifecycle"] = lifecycle
    await lifecycle.async_setup_entry(hass, entry, config_data)

    # Forward platform setups OUTSIDE lifecycle lock to avoid deadlocks
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms first
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    # Remove THIS entry's agent and config only
    config_data = dict(entry.data)
    provider = config_data.get("ai_provider")
    if DOMAIN in hass.data:
        hass.data[DOMAIN].get("agents", {}).pop(provider, None)
        hass.data[DOMAIN].get("configs", {}).pop(provider, None)

    # Delegate to lifecycle (handles refcount, last-entry-stops-all)
    lifecycle = hass.data[DOMAIN].get("_lifecycle") if DOMAIN in hass.data else None
    if lifecycle:
        await lifecycle.async_unload_entry(hass, entry)

    # Clean up domain data ONLY if no entries left
    if DOMAIN in hass.data:
        lc = hass.data[DOMAIN].get("_lifecycle")
        if lc and not lc._entry_ids:
            hass.data.pop(DOMAIN)

    return True


# ---------------------------------------------------------------------------
# Backward-compat re-exports for tests
# ---------------------------------------------------------------------------


async def _initialize_rag(
    hass: HomeAssistant, config_data: dict, entry: ConfigEntry
) -> None:
    """Backward-compat wrapper. Delegates to lifecycle._start_rag."""
    lifecycle = hass.data.get(DOMAIN, {}).get("_lifecycle")
    if lifecycle:
        await lifecycle._start_rag(hass, config_data, entry)


async def _shutdown_rag(hass: HomeAssistant) -> None:
    """Backward-compat wrapper. Delegates to lifecycle._stop_rag."""
    lifecycle = hass.data.get(DOMAIN, {}).get("_lifecycle")
    if lifecycle:
        await lifecycle._stop_rag(hass)


async def _initialize_proactive(hass: HomeAssistant) -> None:
    """Backward-compat wrapper. Delegates to lifecycle._start_proactive.

    Preserves the ``_proactive_initialized`` flag in ``hass.data[DOMAIN]``
    for existing tests that check it.  Uses the lifecycle lock to guarantee
    exactly-once semantics even under concurrent calls.
    """
    domain_data = hass.data.get(DOMAIN, {})
    if domain_data.get("_proactive_initialized"):
        _LOGGER.debug("Proactive subsystem already initialized, skipping")
        return

    # Ensure a shared lifecycle exists (create-if-absent, reuse otherwise)
    lifecycle = domain_data.get("_lifecycle")
    if not lifecycle:
        lifecycle = SubsystemLifecycle()
        if DOMAIN in hass.data:
            hass.data[DOMAIN]["_lifecycle"] = lifecycle

    async with lifecycle._lock:
        # Re-check under lock to prevent races
        if hass.data.get(DOMAIN, {}).get("_proactive_initialized"):
            return
        await lifecycle._start_proactive(hass)
        if DOMAIN in hass.data:
            hass.data[DOMAIN]["_proactive_initialized"] = True


async def _panel_exists(hass: HomeAssistant, panel_name: str) -> bool:
    """Check if a panel already exists."""
    try:
        return hasattr(hass.data, "frontend_panels") and panel_name in hass.data.get(
            "frontend_panels", {}
        )
    except Exception:
        return False
