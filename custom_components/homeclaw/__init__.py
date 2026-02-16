"""The Homeclaw integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .agent_compat import HomeclawAgent
from .const import CONF_RAG_ENABLED, DEFAULT_RAG_ENABLED, DOMAIN, PLATFORMS
from .websocket_api import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

# Config schema - this integration only supports config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Define service schema to accept a custom prompt
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("prompt"): cv.string,
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
    # if entry.version < 2:
    #     # Migrate from version 1 to 2
    #     new_data = dict(entry.data)
    #     # Add migration logic here
    #     hass.config_entries.async_update_entry(entry, data=new_data, version=2)

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

        # Convert ConfigEntry to dict and ensure all required keys exist
        config_data = dict(entry.data)

        # Ensure backward compatibility - check for required keys
        if "ai_provider" not in config_data:
            _LOGGER.error(
                "Config entry missing required 'ai_provider' key. Entry data: %s",
                config_data,
            )
            raise ConfigEntryNotReady("Config entry missing required 'ai_provider' key")

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {"agents": {}, "configs": {}, "_ws_registered": False}

        provider = config_data["ai_provider"]

        # Validate provider
        if provider not in [
            "llama",
            "openai",
            "gemini",
            "gemini_oauth",
            "openrouter",
            "anthropic",
            "anthropic_oauth",
            "alter",
            "zai",
            "local",
        ]:
            _LOGGER.error("Unknown AI provider: %s", provider)
            raise ConfigEntryNotReady(f"Unknown AI provider: {provider}")

        # Store config for this provider
        hass.data[DOMAIN]["configs"][provider] = config_data

        # Create agent for this provider
        _LOGGER.debug(
            "Creating AI agent for provider %s with config: %s",
            provider,
            {
                k: v
                for k, v in config_data.items()
                if k
                not in [
                    "llama_token",
                    "openai_token",
                    "gemini_token",
                    "openrouter_token",
                    "anthropic_token",
                    "zai_token",
                ]
            },
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

        # Initialize RAG system if enabled for this entry (and not already initialized)
        rag_enabled = config_data.get(CONF_RAG_ENABLED, DEFAULT_RAG_ENABLED)
        if rag_enabled and not existing_rag_manager:
            await _initialize_rag(hass, config_data, entry)
        elif not rag_enabled and not existing_rag_manager:
            _LOGGER.debug("RAG system not enabled for provider: %s", provider)

    except KeyError as err:
        _LOGGER.error("Missing required configuration key: %s", err)
        raise ConfigEntryNotReady(f"Missing required configuration key: {err}")
    except Exception as err:
        _LOGGER.exception("Unexpected error setting up Homeclaw")
        raise ConfigEntryNotReady(f"Error setting up Homeclaw: {err}")

    # Modify the query service handler to use the correct provider
    async def async_handle_query(call):
        """Handle the query service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                result = {"error": "No AI agents configured"}
                hass.bus.async_fire("homeclaw_response", result)
                return

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    result = {"error": "No AI agents configured"}
                    hass.bus.async_fire("homeclaw_response", result)
                    return
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            result = await agent.process_query(
                call.data.get("prompt", ""),
                provider=provider,
                debug=call.data.get("debug", False),
            )
            hass.bus.async_fire("homeclaw_response", result)
        except Exception as e:
            _LOGGER.error(f"Error processing query: {e}")
            result = {"error": str(e)}
            hass.bus.async_fire("homeclaw_response", result)

    async def async_handle_create_automation(call):
        """Handle the create_automation service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            result = await agent.create_automation(call.data.get("automation", {}))
            return result
        except Exception as e:
            _LOGGER.error(f"Error creating automation: {e}")
            return {"error": str(e)}

    async def async_handle_save_prompt_history(call):
        """Handle the save_prompt_history service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            user_id = call.context.user_id if call.context.user_id else "default"
            result = await agent.save_user_prompt_history(
                user_id, call.data.get("history", [])
            )
            return result
        except Exception as e:
            _LOGGER.error(f"Error saving prompt history: {e}")
            return {"error": str(e)}

    async def async_handle_load_prompt_history(call):
        """Handle the load_prompt_history service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            user_id = call.context.user_id if call.context.user_id else "default"
            result = await agent.load_user_prompt_history(user_id)
            _LOGGER.debug("Load prompt history result: %s", result)
            return result
        except Exception as e:
            _LOGGER.error(f"Error loading prompt history: {e}")
            return {"error": str(e)}

    async def async_handle_create_dashboard(call):
        """Handle the create_dashboard service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]

            # Parse dashboard config if it's a string
            dashboard_config = call.data.get("dashboard_config", {})
            if isinstance(dashboard_config, str):
                try:
                    import json

                    dashboard_config = json.loads(dashboard_config)
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"Invalid JSON in dashboard_config: {e}")
                    return {"error": f"Invalid JSON in dashboard_config: {e}"}

            result = await agent.create_dashboard(dashboard_config)
            return result
        except Exception as e:
            _LOGGER.error(f"Error creating dashboard: {e}")
            return {"error": str(e)}

    async def async_handle_update_dashboard(call):
        """Handle the update_dashboard service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]

            # Parse dashboard config if it's a string
            dashboard_config = call.data.get("dashboard_config", {})
            if isinstance(dashboard_config, str):
                try:
                    import json

                    dashboard_config = json.loads(dashboard_config)
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"Invalid JSON in dashboard_config: {e}")
                    return {"error": f"Invalid JSON in dashboard_config: {e}"}

            dashboard_url = call.data.get("dashboard_url", "")
            if not dashboard_url:
                return {"error": "Dashboard URL is required"}

            result = await agent.update_dashboard(dashboard_url, dashboard_config)
            return result
        except Exception as e:
            _LOGGER.error(f"Error updating dashboard: {e}")
            return {"error": str(e)}

    async def async_handle_rag_reindex(call):
        """Handle the rag_reindex service call to reindex all entities."""
        try:
            rag_manager = hass.data[DOMAIN].get("rag_manager")
            if not rag_manager:
                _LOGGER.warning("RAG system not initialized, cannot reindex")
                return {"error": "RAG system not initialized"}

            _LOGGER.info("Starting RAG full reindex via service call...")
            await rag_manager.full_reindex()
            stats = await rag_manager.get_stats()
            _LOGGER.info(
                "RAG reindex completed: %d entities indexed",
                stats.get("total_documents", 0),
            )
            return {
                "success": True,
                "entities_indexed": stats.get("total_documents", 0),
            }
        except Exception as e:
            _LOGGER.error(f"Error during RAG reindex: {e}")
            return {"error": str(e)}

    # Register services
    hass.services.async_register(DOMAIN, "query", async_handle_query)
    hass.services.async_register(
        DOMAIN, "create_automation", async_handle_create_automation
    )
    hass.services.async_register(
        DOMAIN, "save_prompt_history", async_handle_save_prompt_history
    )
    hass.services.async_register(
        DOMAIN, "load_prompt_history", async_handle_load_prompt_history
    )
    hass.services.async_register(
        DOMAIN, "create_dashboard", async_handle_create_dashboard
    )
    hass.services.async_register(
        DOMAIN, "update_dashboard", async_handle_update_dashboard
    )
    hass.services.async_register(DOMAIN, "rag_reindex", async_handle_rag_reindex)

    # Forward platform setups (conversation entity)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Clean up old file uploads (> 7 days) at startup
    try:
        from .file_processor import cleanup_old_uploads

        await cleanup_old_uploads(hass)
    except Exception as err:
        _LOGGER.warning("Failed to clean up old uploads: %s", err)

    # --- Proactive subsystem: heartbeat + scheduler + subagent ---
    await _initialize_proactive(hass)

    # --- External channels subsystem ---
    await _initialize_channels(hass, entry)

    # Register WebSocket API commands (only once)
    if not hass.data[DOMAIN].get("_ws_registered"):
        async_register_websocket_commands(hass)
        hass.data[DOMAIN]["_ws_registered"] = True

    # Register static path for frontend
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/frontend/homeclaw",
                hass.config.path("custom_components/homeclaw/frontend"),
                False,
            )
        ]
    )

    # Panel registration with proper error handling
    panel_name = "homeclaw"
    try:
        if await _panel_exists(hass, panel_name):
            _LOGGER.debug("Homeclaw panel already exists, skipping registration")
            return True

        _LOGGER.debug("Registering Homeclaw panel")
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="Homeclaw",
            sidebar_icon="mdi:robot",
            frontend_url_path=panel_name,
            require_admin=False,
            config={
                "_panel_custom": {
                    "name": "homeclaw-panel",
                    "module_url": "/frontend/homeclaw/homeclaw-panel.js",
                    "embed_iframe": False,
                }
            },
        )
        _LOGGER.debug("Homeclaw panel registered successfully")
    except Exception as e:
        _LOGGER.warning("Panel registration error: %s", str(e))

    return True


async def _initialize_rag(
    hass: HomeAssistant, config_data: dict, entry: ConfigEntry
) -> None:
    """Initialize the RAG system with graceful degradation.

    If RAG initialization fails, the integration continues to work
    without RAG functionality (logs a warning).
    """
    try:
        from .rag import RAGManager

        rag_manager = RAGManager(hass, config_data, entry)
        await rag_manager.async_initialize()

        # Store RAG manager in hass.data
        hass.data[DOMAIN]["rag_manager"] = rag_manager

        # Connect RAG manager to agents
        for agent in hass.data[DOMAIN]["agents"].values():
            agent.set_rag_manager(rag_manager)

        stats = await rag_manager.get_stats()
        _LOGGER.info(
            "RAG system initialized with %d entities indexed",
            stats.get("indexed_entities", 0),
        )

    except ImportError as err:
        _LOGGER.warning(
            "RAG system unavailable (missing dependencies: %s). "
            "Agent will work without semantic search.",
            err,
        )
    except Exception as err:
        _LOGGER.warning(
            "RAG system initialization failed: %s. "
            "Agent will work without semantic search.",
            err,
        )


async def _initialize_proactive(hass: HomeAssistant) -> None:
    """Initialize the proactive subsystem (heartbeat + scheduler + subagent).

    Uses graceful degradation — if initialization fails, the integration
    continues to work without proactive features (logs a warning).
    """
    if hass.data.get(DOMAIN, {}).get("_proactive_initialized"):
        _LOGGER.debug("Proactive subsystem already initialized, skipping")
        return

    try:
        from .core.subagent import SubagentManager
        from .proactive import HeartbeatService, SchedulerService

        # 1. Heartbeat
        heartbeat = HeartbeatService(hass)
        await heartbeat.async_initialize()
        await heartbeat.async_start()
        hass.data[DOMAIN]["heartbeat"] = heartbeat

        # 2. Scheduler
        scheduler = SchedulerService(hass)
        await scheduler.async_initialize()
        await scheduler.async_start()
        hass.data[DOMAIN]["scheduler"] = scheduler

        # 3. Subagent manager (no async init needed)
        subagent_manager = SubagentManager(hass)
        hass.data[DOMAIN]["subagent_manager"] = subagent_manager

        hass.data[DOMAIN]["_proactive_initialized"] = True

        _LOGGER.info(
            "Proactive subsystem initialized (heartbeat=%s, scheduler_jobs=%d)",
            heartbeat.get_config().get("enabled", False),
            scheduler.get_status().get("total_jobs", 0),
        )

    except ImportError as err:
        _LOGGER.warning(
            "Proactive subsystem unavailable (missing module: %s). "
            "Agent will work without heartbeat/scheduler/subagent features.",
            err,
        )
    except Exception as err:
        _LOGGER.warning(
            "Proactive subsystem initialization failed: %s. "
            "Agent will work without heartbeat/scheduler/subagent features.",
            err,
        )


async def _shutdown_proactive(hass: HomeAssistant) -> None:
    """Shutdown the proactive subsystem gracefully."""
    if DOMAIN not in hass.data:
        return

    domain_data = hass.data[DOMAIN]

    # Stop heartbeat
    heartbeat = domain_data.get("heartbeat")
    if heartbeat:
        try:
            await heartbeat.async_stop()
            _LOGGER.debug("Heartbeat service stopped")
        except Exception as err:
            _LOGGER.warning("Error stopping heartbeat: %s", err)
        finally:
            domain_data.pop("heartbeat", None)

    # Stop scheduler
    scheduler = domain_data.get("scheduler")
    if scheduler:
        try:
            await scheduler.async_stop()
            _LOGGER.debug("Scheduler service stopped")
        except Exception as err:
            _LOGGER.warning("Error stopping scheduler: %s", err)
        finally:
            domain_data.pop("scheduler", None)

    # Clean up subagent manager
    domain_data.pop("subagent_manager", None)
    domain_data.pop("_proactive_initialized", None)


async def _initialize_channels(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Initialize the external channels subsystem (Telegram, Discord, etc.).

    Creates a ChannelManager with a MessageIntake and starts all enabled
    channels.  Uses graceful degradation — if initialization fails, the
    integration continues without external channels.
    """
    if hass.data.get(DOMAIN, {}).get("channel_manager"):
        _LOGGER.debug("Channel manager already initialized, skipping")
        return

    try:
        from .channels.config import build_channel_runtime_config
        from .channels.intake import MessageIntake
        from .channels.manager import ChannelManager

        intake = MessageIntake(hass)
        manager = ChannelManager(hass, intake)

        # Channel config: base from entry.data, overridden by entry.options
        # and normalized with channel-specific defaults/fallbacks.
        channel_config = await build_channel_runtime_config(
            hass,
            {**entry.data, **entry.options},
        )
        await manager.async_setup(channel_config)

        hass.data[DOMAIN]["channel_manager"] = manager

        active = manager.active_channels
        if active:
            _LOGGER.info("Channel manager initialized with channels: %s", active)
        else:
            _LOGGER.debug("Channel manager initialized, no channels enabled")

    except Exception as err:
        _LOGGER.warning(
            "Channel subsystem initialization failed: %s. "
            "Agent will work without external channels.",
            err,
        )


async def _shutdown_channels(hass: HomeAssistant) -> None:
    """Shutdown the channel subsystem gracefully."""
    if DOMAIN not in hass.data:
        return

    manager = hass.data[DOMAIN].get("channel_manager")
    if manager:
        try:
            await manager.async_teardown()
            _LOGGER.debug("Channel manager shut down successfully")
        except Exception as err:
            _LOGGER.warning("Error shutting down channel manager: %s", err)
        finally:
            hass.data[DOMAIN].pop("channel_manager", None)


async def _shutdown_rag(hass: HomeAssistant) -> None:
    """Shutdown the RAG system gracefully."""
    if DOMAIN not in hass.data:
        return

    rag_manager = hass.data[DOMAIN].get("rag_manager")
    if rag_manager:
        try:
            await rag_manager.async_shutdown()
            _LOGGER.debug("RAG system shut down successfully")
        except Exception as err:
            _LOGGER.warning("Error shutting down RAG system: %s", err)
        finally:
            hass.data[DOMAIN].pop("rag_manager", None)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload conversation platform
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    # Shutdown channels subsystem
    await _shutdown_channels(hass)

    # Shutdown proactive subsystem
    await _shutdown_proactive(hass)

    # Shutdown RAG system
    await _shutdown_rag(hass)

    if await _panel_exists(hass, "homeclaw"):
        try:
            from homeassistant.components.frontend import async_remove_panel

            async_remove_panel(hass, "homeclaw")
            _LOGGER.debug("Homeclaw panel removed successfully")
        except Exception as e:
            _LOGGER.debug("Error removing panel: %s", str(e))

    # Remove services
    hass.services.async_remove(DOMAIN, "query")
    hass.services.async_remove(DOMAIN, "create_automation")
    hass.services.async_remove(DOMAIN, "save_prompt_history")
    hass.services.async_remove(DOMAIN, "load_prompt_history")
    hass.services.async_remove(DOMAIN, "create_dashboard")
    hass.services.async_remove(DOMAIN, "update_dashboard")
    hass.services.async_remove(DOMAIN, "rag_reindex")

    # Clean up storage cache instances
    storage_cache_prefix = f"{DOMAIN}_storage_"
    storage_keys = [
        k for k in list(hass.data.keys()) if k.startswith(storage_cache_prefix)
    ]
    for key in storage_keys:
        hass.data.pop(key, None)

    # Remove domain data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True


async def _panel_exists(hass: HomeAssistant, panel_name: str) -> bool:
    """Check if a panel already exists."""
    try:
        return hasattr(hass.data, "frontend_panels") and panel_name in hass.data.get(
            "frontend_panels", {}
        )
    except Exception as e:
        _LOGGER.debug("Error checking panel existence: %s", str(e))
        return False
