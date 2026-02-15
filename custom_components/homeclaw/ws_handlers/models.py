"""WebSocket handlers for models, providers, preferences, and config CRUD."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import VALID_PROVIDERS
from ..models import (
    get_models_for_provider,
    invalidate_cache,
    load_models_config,
    save_models_config,
)
from ._common import (
    ERR_INVALID_INPUT,
    ERR_STORAGE_ERROR,
    _get_storage,
    _get_user_id,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model listing / provider config
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/models/list",
        vol.Optional("provider"): str,
    }
)
@websocket_api.async_response
async def ws_get_available_models(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get available models for a provider.

    Returns a list of available models with their descriptions.
    Models are loaded from models_config.json for easy editing.
    """
    provider = msg.get("provider", "gemini_oauth")
    # Run file I/O in executor to avoid blocking event loop
    models = await hass.async_add_executor_job(get_models_for_provider, provider)

    connection.send_result(
        msg["id"],
        {
            "provider": provider,
            "models": models,
            "supports_model_selection": len(models) > 0,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/providers/config",
    }
)
@websocket_api.async_response
async def ws_get_providers_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get full providers configuration including display names and model lists.

    Returns the complete models_config.json content, enabling the frontend
    to populate provider labels, model selectors, and custom model options
    without hardcoding provider metadata.
    """
    config = await hass.async_add_executor_job(load_models_config)

    connection.send_result(
        msg["id"],
        {
            "providers": config,
        },
    )


# ---------------------------------------------------------------------------
# User preferences (default provider + model)
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/preferences/get",
    }
)
@websocket_api.async_response
async def ws_get_preferences(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get user preferences (default provider and model)."""
    user_id = _get_user_id(connection)

    try:
        storage = _get_storage(hass, user_id)
        prefs = await storage.get_preferences()
        connection.send_result(msg["id"], {"preferences": prefs})
    except Exception:
        _LOGGER.exception("Failed to get preferences for user %s", user_id)
        connection.send_error(
            msg["id"], ERR_STORAGE_ERROR, "Failed to load preferences"
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/preferences/set",
        vol.Optional("default_provider"): vol.Any(str, None),
        vol.Optional("default_model"): vol.Any(str, None),
        vol.Optional("rag_optimizer_provider"): vol.Any(str, None),
        vol.Optional("rag_optimizer_model"): vol.Any(str, None),
        vol.Optional("theme"): vol.Any("light", "dark", "system", None),
    }
)
@websocket_api.async_response
async def ws_set_preferences(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set user preferences (default provider, model, theme).

    Validates that the provider exists in models_config.json and the model
    belongs to that provider. Pass null/None to clear a preference.
    """
    user_id = _get_user_id(connection)

    try:
        prefs_update: dict[str, Any] = {}

        default_provider = msg.get("default_provider")
        default_model = msg.get("default_model")
        theme = msg.get("theme")

        # Validate provider exists in config
        if default_provider is not None:
            config = await hass.async_add_executor_job(load_models_config)
            if default_provider not in config:
                connection.send_error(
                    msg["id"],
                    ERR_INVALID_INPUT,
                    f"Unknown provider: {default_provider}",
                )
                return
            prefs_update["default_provider"] = default_provider

        # Validate model belongs to provider
        if default_model is not None:
            provider_for_model = default_provider
            if provider_for_model is None:
                # Use existing preference as context
                storage = _get_storage(hass, user_id)
                existing = await storage.get_preferences()
                provider_for_model = existing.get("default_provider")

            if provider_for_model:
                model_ids = await hass.async_add_executor_job(
                    get_models_for_provider, provider_for_model
                )
                valid_ids = [m["id"] for m in model_ids]
                # Allow custom model if provider permits it
                from ..models import get_allow_custom_model

                allow_custom = await hass.async_add_executor_job(
                    get_allow_custom_model, provider_for_model
                )
                if default_model not in valid_ids and not allow_custom:
                    connection.send_error(
                        msg["id"],
                        ERR_INVALID_INPUT,
                        f"Model '{default_model}' not available for provider '{provider_for_model}'",
                    )
                    return

            prefs_update["default_model"] = default_model

        # Handle explicit None (clear) vs absent key
        if "default_provider" in msg and msg["default_provider"] is None:
            prefs_update["default_provider"] = None
        if "default_model" in msg and msg["default_model"] is None:
            prefs_update["default_model"] = None
        if "theme" in msg:
            prefs_update["theme"] = theme

        # RAG optimizer provider/model (used by auto-sanitization and manual optimize)
        rag_provider = msg.get("rag_optimizer_provider")
        rag_model = msg.get("rag_optimizer_model")

        if "rag_optimizer_provider" in msg:
            if rag_provider is not None:
                config = await hass.async_add_executor_job(load_models_config)
                if rag_provider not in config:
                    connection.send_error(
                        msg["id"],
                        ERR_INVALID_INPUT,
                        f"Unknown RAG optimizer provider: {rag_provider}",
                    )
                    return
            prefs_update["rag_optimizer_provider"] = rag_provider

        if "rag_optimizer_model" in msg:
            prefs_update["rag_optimizer_model"] = rag_model

        if not prefs_update:
            connection.send_error(
                msg["id"], ERR_INVALID_INPUT, "No preferences to update"
            )
            return

        storage = _get_storage(hass, user_id)
        updated = await storage.set_preferences(prefs_update)
        connection.send_result(msg["id"], {"preferences": updated})

    except Exception:
        _LOGGER.exception("Failed to set preferences for user %s", user_id)
        connection.send_error(
            msg["id"], ERR_STORAGE_ERROR, "Failed to save preferences"
        )


# ---------------------------------------------------------------------------
# Models config CRUD (admin)
# ---------------------------------------------------------------------------


def _validate_model_entry(model: dict[str, Any]) -> str | None:
    """Validate a single model entry dict. Returns error message or None."""
    if not isinstance(model, dict):
        return "Each model must be a dictionary"
    if not model.get("id") or not isinstance(model.get("id"), str):
        return "Model must have a non-empty string 'id'"
    if not model.get("name") or not isinstance(model.get("name"), str):
        return "Model must have a non-empty string 'name'"
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/config/models/get",
        vol.Optional("force_reload", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_config_models_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get the full models configuration (for admin editing).

    Optionally force a cache reload from disk.
    """
    try:
        if msg.get("force_reload"):
            await hass.async_add_executor_job(invalidate_cache)

        config = await hass.async_add_executor_job(load_models_config)
        connection.send_result(msg["id"], {"config": config})
    except Exception:
        _LOGGER.exception("Failed to get models config")
        connection.send_error(
            msg["id"], ERR_STORAGE_ERROR, "Failed to load models config"
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/config/models/update",
        vol.Required("provider"): str,
        vol.Optional("models"): list,
        vol.Optional("display_name"): str,
        vol.Optional("description"): str,
        vol.Optional("allow_custom_model"): bool,
    }
)
@websocket_api.async_response
async def ws_config_models_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update models/metadata for a specific provider.

    Merges provided fields into the existing provider config. If 'models' list
    is provided, it replaces the entire models list for that provider.
    Validates model entries and enforces max 1 default.
    """
    provider = msg["provider"]

    try:
        config = await hass.async_add_executor_job(load_models_config)

        if provider not in config:
            connection.send_error(
                msg["id"],
                ERR_INVALID_INPUT,
                f"Provider '{provider}' not found in config. Use add_provider first.",
            )
            return

        provider_config = config[provider]

        # Update optional metadata fields
        if "display_name" in msg:
            provider_config["display_name"] = msg["display_name"]
        if "description" in msg:
            provider_config["description"] = msg["description"]
        if "allow_custom_model" in msg:
            provider_config["allow_custom_model"] = msg["allow_custom_model"]

        # Update models list
        if "models" in msg:
            models = msg["models"]
            if not isinstance(models, list):
                connection.send_error(
                    msg["id"], ERR_INVALID_INPUT, "models must be a list"
                )
                return

            # Validate each model entry
            for m in models:
                err = _validate_model_entry(m)
                if err:
                    connection.send_error(msg["id"], ERR_INVALID_INPUT, err)
                    return

            # Enforce max 1 default
            defaults = [m for m in models if m.get("default")]
            if len(defaults) > 1:
                connection.send_error(
                    msg["id"],
                    ERR_INVALID_INPUT,
                    "Only one model can be marked as default",
                )
                return

            # Clean model entries (keep only known keys)
            cleaned: list[dict[str, Any]] = []
            for m in models:
                entry: dict[str, Any] = {"id": m["id"], "name": m["name"]}
                if m.get("description"):
                    entry["description"] = m["description"]
                if m.get("default"):
                    entry["default"] = True
                cleaned.append(entry)

            provider_config["models"] = cleaned

        config[provider] = provider_config
        await hass.async_add_executor_job(save_models_config, config)

        connection.send_result(
            msg["id"], {"provider": provider, "config": provider_config}
        )

    except Exception:
        _LOGGER.exception("Failed to update models config for provider %s", provider)
        connection.send_error(
            msg["id"], ERR_STORAGE_ERROR, "Failed to update models config"
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/config/models/add_provider",
        vol.Required("provider"): str,
        vol.Optional("display_name"): str,
        vol.Optional("description"): str,
        vol.Optional("allow_custom_model", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_config_models_add_provider(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a new provider to models_config.json.

    Provider key must be in VALID_PROVIDERS. Fails if provider already exists.
    """
    provider = msg["provider"]

    if provider not in VALID_PROVIDERS:
        connection.send_error(
            msg["id"],
            ERR_INVALID_INPUT,
            f"Provider '{provider}' is not in the list of valid providers",
        )
        return

    try:
        config = await hass.async_add_executor_job(load_models_config)

        if provider in config:
            connection.send_error(
                msg["id"],
                ERR_INVALID_INPUT,
                f"Provider '{provider}' already exists",
            )
            return

        new_provider: dict[str, Any] = {
            "display_name": msg.get("display_name", provider),
            "description": msg.get("description", ""),
            "models": [],
        }
        if msg.get("allow_custom_model"):
            new_provider["allow_custom_model"] = True

        config[provider] = new_provider
        await hass.async_add_executor_job(save_models_config, config)

        connection.send_result(
            msg["id"], {"provider": provider, "config": new_provider}
        )

    except Exception:
        _LOGGER.exception("Failed to add provider %s", provider)
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to add provider")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/config/models/remove_provider",
        vol.Required("provider"): str,
    }
)
@websocket_api.async_response
async def ws_config_models_remove_provider(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Remove a provider from models_config.json.

    Does not remove the HA config entry -- only the model definitions.
    """
    provider = msg["provider"]

    try:
        config = await hass.async_add_executor_job(load_models_config)

        if provider not in config:
            connection.send_error(
                msg["id"],
                ERR_INVALID_INPUT,
                f"Provider '{provider}' not found in config",
            )
            return

        del config[provider]
        await hass.async_add_executor_job(save_models_config, config)

        connection.send_result(msg["id"], {"success": True})

    except Exception:
        _LOGGER.exception("Failed to remove provider %s", provider)
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to remove provider")
