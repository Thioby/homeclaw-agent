"""Service handlers for the Homeclaw integration."""

from __future__ import annotations

import functools
import json
import logging
from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

SERVICE_QUERY = "query"
SERVICE_CREATE_AUTOMATION = "create_automation"
SERVICE_SAVE_PROMPT_HISTORY = "save_prompt_history"
SERVICE_LOAD_PROMPT_HISTORY = "load_prompt_history"
SERVICE_CREATE_DASHBOARD = "create_dashboard"
SERVICE_UPDATE_DASHBOARD = "update_dashboard"
SERVICE_RAG_REINDEX = "rag_reindex"

ALL_SERVICES = (
    SERVICE_QUERY,
    SERVICE_CREATE_AUTOMATION,
    SERVICE_SAVE_PROMPT_HISTORY,
    SERVICE_LOAD_PROMPT_HISTORY,
    SERVICE_CREATE_DASHBOARD,
    SERVICE_UPDATE_DASHBOARD,
    SERVICE_RAG_REINDEX,
)


def _get_agent(hass: HomeAssistant, provider_hint: str | None) -> tuple[Any, str]:
    """Resolve an AI agent from hass.data, with fallback to first available.

    Args:
        hass: The Home Assistant instance.
        provider_hint: Optional provider name from the service call.

    Returns:
        Tuple of (agent_instance, resolved_provider_name).

    Raises:
        RuntimeError: If no agents are configured.
    """
    agents: dict[str, Any] | None = hass.data.get(DOMAIN, {}).get("agents")
    if not agents:
        raise RuntimeError(
            "No AI agents configured. Please configure the integration first."
        )

    if provider_hint and provider_hint in agents:
        return agents[provider_hint], provider_hint

    # Fallback to first available
    first_provider = next(iter(agents))
    _LOGGER.debug(
        "Provider %s not found, falling back to %s", provider_hint, first_provider
    )
    return agents[first_provider], first_provider


def _parse_dashboard_config(raw_config: Any) -> dict[str, Any]:
    """Parse dashboard_config from a JSON string if needed.

    Args:
        raw_config: Dashboard config as dict or JSON string.

    Returns:
        Parsed dashboard config dict.

    Raises:
        ValueError: If the JSON string is invalid.
    """
    if isinstance(raw_config, str):
        try:
            return json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in dashboard_config: {exc}") from exc
    return raw_config if isinstance(raw_config, dict) else {}


async def _handle_query(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the query service call.

    Fires a ``homeclaw_response`` event with the result (or error).
    """
    try:
        agent, _provider = _get_agent(hass, call.data.get("provider"))
        result = await agent.process_query(
            call.data.get("prompt", ""),
            provider=_provider,
            debug=call.data.get("debug", False),
        )
    except RuntimeError as exc:
        _LOGGER.error("Query service error: %s", exc)
        result = {"error": str(exc)}
    except Exception as exc:
        _LOGGER.error("Error processing query: %s", exc)
        result = {"error": str(exc)}
    hass.bus.async_fire("homeclaw_response", result)


async def _handle_create_automation(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any] | None:
    """Handle the create_automation service call."""
    try:
        agent, _provider = _get_agent(hass, call.data.get("provider"))
        return await agent.create_automation(call.data.get("automation", {}))
    except RuntimeError as exc:
        _LOGGER.error("Create automation error: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _LOGGER.error("Error creating automation: %s", exc)
        return {"error": str(exc)}


async def _handle_save_prompt_history(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any] | None:
    """Handle the save_prompt_history service call."""
    try:
        agent, _provider = _get_agent(hass, call.data.get("provider"))
        user_id = call.context.user_id if call.context.user_id else "default"
        return await agent.save_user_prompt_history(
            user_id, call.data.get("history", [])
        )
    except RuntimeError as exc:
        _LOGGER.error("Save prompt history error: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _LOGGER.error("Error saving prompt history: %s", exc)
        return {"error": str(exc)}


async def _handle_load_prompt_history(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any] | None:
    """Handle the load_prompt_history service call."""
    try:
        agent, _provider = _get_agent(hass, call.data.get("provider"))
        user_id = call.context.user_id if call.context.user_id else "default"
        result = await agent.load_user_prompt_history(user_id)
        _LOGGER.debug("Load prompt history result: %s", result)
        return result
    except RuntimeError as exc:
        _LOGGER.error("Load prompt history error: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _LOGGER.error("Error loading prompt history: %s", exc)
        return {"error": str(exc)}


async def _handle_create_dashboard(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any] | None:
    """Handle the create_dashboard service call."""
    try:
        agent, _provider = _get_agent(hass, call.data.get("provider"))
        dashboard_config = _parse_dashboard_config(
            call.data.get("dashboard_config", {})
        )
        return await agent.create_dashboard(dashboard_config)
    except (RuntimeError, ValueError) as exc:
        _LOGGER.error("Create dashboard error: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _LOGGER.error("Error creating dashboard: %s", exc)
        return {"error": str(exc)}


async def _handle_update_dashboard(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any] | None:
    """Handle the update_dashboard service call."""
    try:
        agent, _provider = _get_agent(hass, call.data.get("provider"))
        dashboard_config = _parse_dashboard_config(
            call.data.get("dashboard_config", {})
        )
        dashboard_url = call.data.get("dashboard_url", "")
        if not dashboard_url:
            return {"error": "Dashboard URL is required"}
        return await agent.update_dashboard(dashboard_url, dashboard_config)
    except (RuntimeError, ValueError) as exc:
        _LOGGER.error("Update dashboard error: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _LOGGER.error("Error updating dashboard: %s", exc)
        return {"error": str(exc)}


async def _handle_rag_reindex(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any] | None:
    """Handle the rag_reindex service call to reindex all entities."""
    try:
        rag_manager = hass.data.get(DOMAIN, {}).get("rag_manager")
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
        return {"success": True, "entities_indexed": stats.get("total_documents", 0)}
    except Exception as exc:
        _LOGGER.error("Error during RAG reindex: %s", exc)
        return {"error": str(exc)}


async def async_register_services(hass: HomeAssistant) -> None:
    """Register all Homeclaw services with Home Assistant.

    Args:
        hass: The Home Assistant instance.
    """
    _reg = functools.partial(hass.services.async_register, DOMAIN)
    _reg(SERVICE_QUERY, functools.partial(_handle_query, hass))
    _reg(SERVICE_CREATE_AUTOMATION, functools.partial(_handle_create_automation, hass))
    _reg(
        SERVICE_SAVE_PROMPT_HISTORY,
        functools.partial(_handle_save_prompt_history, hass),
    )
    _reg(
        SERVICE_LOAD_PROMPT_HISTORY,
        functools.partial(_handle_load_prompt_history, hass),
    )
    _reg(SERVICE_CREATE_DASHBOARD, functools.partial(_handle_create_dashboard, hass))
    _reg(SERVICE_UPDATE_DASHBOARD, functools.partial(_handle_update_dashboard, hass))
    _reg(SERVICE_RAG_REINDEX, functools.partial(_handle_rag_reindex, hass))


async def async_remove_services(hass: HomeAssistant) -> None:
    """Remove all Homeclaw services from Home Assistant.

    Args:
        hass: The Home Assistant instance.
    """
    for service_name in ALL_SERVICES:
        hass.services.async_remove(DOMAIN, service_name)
