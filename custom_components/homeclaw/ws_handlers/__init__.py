"""WebSocket handlers package for Homeclaw.

Organizes WS command handlers into domain-specific modules:
- sessions: session CRUD (list, get, create, delete, rename)
- chat: messaging (send, stream) + RAG post-conversation
- models: model listing, provider config, user preferences, config CRUD
- rag: RAG viewer, search, identity, optimizer
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components import websocket_api

from .chat import ws_send_message, ws_send_message_stream
from .models import (
    ws_config_models_add_provider,
    ws_config_models_get,
    ws_config_models_remove_provider,
    ws_config_models_update,
    ws_get_available_models,
    ws_get_preferences,
    ws_get_providers_config,
    ws_set_preferences,
)
from .rag import (
    ws_rag_identity,
    ws_rag_identity_update,
    ws_rag_memories,
    ws_rag_memory_delete,
    ws_rag_optimize_analyze,
    ws_rag_optimize_run,
    ws_rag_search,
    ws_rag_sessions,
    ws_rag_stats,
)
from .sessions import (
    ws_create_session,
    ws_delete_session,
    ws_get_session,
    ws_list_sessions,
    ws_rename_session,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket API commands.

    This function should only be called once per Home Assistant instance.
    Use the guard in __init__.py to prevent multiple registrations.
    """
    # Session management
    websocket_api.async_register_command(hass, ws_list_sessions)
    websocket_api.async_register_command(hass, ws_get_session)
    websocket_api.async_register_command(hass, ws_create_session)
    websocket_api.async_register_command(hass, ws_delete_session)
    websocket_api.async_register_command(hass, ws_rename_session)
    # Chat / messaging
    websocket_api.async_register_command(hass, ws_send_message)
    websocket_api.async_register_command(hass, ws_send_message_stream)
    # Model listing / provider config
    websocket_api.async_register_command(hass, ws_get_available_models)
    websocket_api.async_register_command(hass, ws_get_providers_config)
    # User preferences
    websocket_api.async_register_command(hass, ws_get_preferences)
    websocket_api.async_register_command(hass, ws_set_preferences)
    # Models config CRUD
    websocket_api.async_register_command(hass, ws_config_models_get)
    websocket_api.async_register_command(hass, ws_config_models_update)
    websocket_api.async_register_command(hass, ws_config_models_add_provider)
    websocket_api.async_register_command(hass, ws_config_models_remove_provider)
    # RAG Viewer
    websocket_api.async_register_command(hass, ws_rag_stats)
    websocket_api.async_register_command(hass, ws_rag_memories)
    websocket_api.async_register_command(hass, ws_rag_memory_delete)
    websocket_api.async_register_command(hass, ws_rag_sessions)
    websocket_api.async_register_command(hass, ws_rag_identity)
    websocket_api.async_register_command(hass, ws_rag_identity_update)
    websocket_api.async_register_command(hass, ws_rag_search)
    # RAG Optimizer
    websocket_api.async_register_command(hass, ws_rag_optimize_analyze)
    websocket_api.async_register_command(hass, ws_rag_optimize_run)
