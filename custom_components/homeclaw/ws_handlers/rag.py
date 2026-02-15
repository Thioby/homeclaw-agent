"""WebSocket handlers for RAG viewer, search, identity, and optimizer."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN, VALID_PROVIDERS
from ._common import (
    ERR_AI_ERROR,
    ERR_INVALID_INPUT,
    ERR_STORAGE_ERROR,
    _get_rag_manager,
    _get_user_id,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RAG Viewer endpoints
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/stats",
    }
)
@websocket_api.async_response
async def ws_rag_stats(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get RAG system statistics (entities, sessions, memories, identity)."""
    user_id = _get_user_id(connection)
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized:
        connection.send_result(msg["id"], {"initialized": False})
        return

    try:
        stats = await rag.get_stats()

        # Add memory stats for this user
        memory_stats = {}
        if rag._memory_manager:
            memory_stats = await rag._memory_manager.get_stats(user_id)

        # Add identity info
        identity_info = None
        if rag._identity_manager:
            identity = await rag._identity_manager.get_identity(user_id)
            if identity:
                identity_info = {
                    "agent_name": identity.agent_name,
                    "agent_personality": identity.agent_personality,
                    "agent_emoji": identity.agent_emoji,
                    "user_name": identity.user_name,
                    "language": identity.language,
                    "onboarding_completed": identity.onboarding_completed,
                }

        connection.send_result(
            msg["id"],
            {
                "initialized": True,
                "stats": stats,
                "memory_stats": memory_stats,
                "identity": identity_info,
            },
        )
    except Exception:
        _LOGGER.exception("Failed to get RAG stats")
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to get RAG stats")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/memories",
        vol.Optional("category"): str,
        vol.Optional("limit", default=50): int,
        vol.Optional("offset", default=0): int,
    }
)
@websocket_api.async_response
async def ws_rag_memories(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List user memories stored in the RAG system."""
    user_id = _get_user_id(connection)
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized or not rag._memory_manager:
        connection.send_result(msg["id"], {"memories": []})
        return

    try:
        memories = await rag._memory_manager.list_memories(
            user_id,
            category=msg.get("category"),
            limit=min(msg.get("limit", 50), 200),
            offset=msg.get("offset", 0),
        )

        connection.send_result(
            msg["id"],
            {
                "memories": [
                    {
                        "id": m.id,
                        "text": m.text,
                        "category": m.category,
                        "importance": round(m.importance, 2),
                        "source": m.source,
                        "session_id": m.session_id,
                        "created_at": m.created_at,
                        "updated_at": m.updated_at,
                        "expires_at": m.expires_at,
                    }
                    for m in memories
                ],
            },
        )
    except Exception:
        _LOGGER.exception("Failed to list memories")
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to list memories")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/memory/delete",
        vol.Required("memory_id"): str,
    }
)
@websocket_api.async_response
async def ws_rag_memory_delete(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a specific memory."""
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized or not rag._memory_manager:
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "RAG not initialized")
        return

    try:
        deleted = await rag._memory_manager.forget_memory(msg["memory_id"])
        connection.send_result(msg["id"], {"deleted": deleted})
    except Exception:
        _LOGGER.exception("Failed to delete memory %s", msg["memory_id"])
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to delete memory")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/sessions",
        vol.Optional("session_id"): str,
        vol.Optional("limit", default=50): int,
        vol.Optional("offset", default=0): int,
    }
)
@websocket_api.async_response
async def ws_rag_sessions(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List session chunks indexed in RAG."""
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized or not rag._store:
        connection.send_result(msg["id"], {"chunks": []})
        return

    try:
        chunks = await rag._store.list_session_chunks(
            session_id=msg.get("session_id"),
            limit=min(msg.get("limit", 50), 200),
            offset=msg.get("offset", 0),
        )
        connection.send_result(msg["id"], {"chunks": chunks})
    except Exception:
        _LOGGER.exception("Failed to list session chunks")
        connection.send_error(
            msg["id"], ERR_STORAGE_ERROR, "Failed to list session chunks"
        )


# ---------------------------------------------------------------------------
# RAG Identity endpoints
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/identity",
    }
)
@websocket_api.async_response
async def ws_rag_identity(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get agent identity for the current user."""
    user_id = _get_user_id(connection)
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized or not rag._identity_manager:
        connection.send_result(msg["id"], {"identity": None})
        return

    try:
        identity = await rag._identity_manager.get_identity(user_id)
        if identity:
            connection.send_result(
                msg["id"],
                {
                    "identity": {
                        "agent_name": identity.agent_name,
                        "agent_personality": identity.agent_personality,
                        "agent_emoji": identity.agent_emoji,
                        "user_name": identity.user_name,
                        "user_info": identity.user_info,
                        "language": identity.language,
                        "onboarding_completed": identity.onboarding_completed,
                    },
                },
            )
        else:
            connection.send_result(msg["id"], {"identity": None})
    except Exception:
        _LOGGER.exception("Failed to get identity")
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to get identity")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/identity/update",
        vol.Optional("agent_name"): vol.Any(str, None),
        vol.Optional("agent_personality"): vol.Any(str, None),
        vol.Optional("agent_emoji"): vol.Any(str, None),
        vol.Optional("user_name"): vol.Any(str, None),
        vol.Optional("user_info"): vol.Any(str, None),
        vol.Optional("language"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_rag_identity_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update agent identity fields for the current user.

    Accepts partial updates -- only fields present in the message are changed.
    """
    user_id = _get_user_id(connection)
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized or not rag._identity_manager:
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "RAG not initialized")
        return

    # Collect only the identity fields that were actually sent
    allowed_fields = {
        "agent_name",
        "agent_personality",
        "agent_emoji",
        "user_name",
        "user_info",
        "language",
    }
    updates = {k: v for k, v in msg.items() if k in allowed_fields}

    if not updates:
        connection.send_error(
            msg["id"], ERR_INVALID_INPUT, "No identity fields to update"
        )
        return

    try:
        await rag._identity_manager.save_identity(user_id, **updates)

        # Return the updated identity
        identity = await rag._identity_manager.get_identity(user_id)
        identity_data = None
        if identity:
            identity_data = {
                "agent_name": identity.agent_name,
                "agent_personality": identity.agent_personality,
                "agent_emoji": identity.agent_emoji,
                "user_name": identity.user_name,
                "user_info": identity.user_info,
                "language": identity.language,
                "onboarding_completed": identity.onboarding_completed,
            }

        connection.send_result(msg["id"], {"identity": identity_data, "success": True})
        _LOGGER.info(
            "Identity updated for user %s: %s", user_id[:8], list(updates.keys())
        )

    except Exception:
        _LOGGER.exception("Failed to update identity for user %s", user_id)
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to update identity")


# ---------------------------------------------------------------------------
# RAG Search endpoint
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/search",
        vol.Required("query"): str,
        vol.Optional("top_k", default=5): int,
    }
)
@websocket_api.async_response
async def ws_rag_search(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Test RAG search -- returns what context would be generated for a query."""
    user_id = _get_user_id(connection)
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized:
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "RAG not initialized")
        return

    try:
        context = await rag.get_relevant_context(
            msg["query"],
            top_k=min(msg.get("top_k", 5), 20),
            user_id=user_id,
        )
        connection.send_result(
            msg["id"],
            {
                "query": msg["query"],
                "context": context or "(no relevant context found)",
                "context_length": len(context) if context else 0,
            },
        )
    except Exception:
        _LOGGER.exception("RAG search failed")
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "RAG search failed")


# ---------------------------------------------------------------------------
# RAG Optimizer endpoints
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/optimize/analyze",
    }
)
@websocket_api.async_response
async def ws_rag_optimize_analyze(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Analyze RAG database size and estimate optimization potential."""
    user_id = _get_user_id(connection)
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized:
        connection.send_result(msg["id"], {"initialized": False})
        return

    try:
        from ..rag.optimizer import RAGOptimizer

        optimizer = RAGOptimizer(
            store=rag._store,
            embedding_provider=rag._embedding_provider,
            memory_manager=rag._memory_manager,
        )
        analysis = await optimizer.analyze(user_id=user_id)
        connection.send_result(msg["id"], {"initialized": True, **analysis.to_dict()})

    except Exception:
        _LOGGER.exception("RAG optimization analysis failed")
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Analysis failed")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/rag/optimize/run",
        vol.Required("provider"): vol.In(VALID_PROVIDERS),
        vol.Required("model"): str,
        vol.Optional("scope", default="all"): vol.In(["all", "sessions", "memories"]),
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_rag_optimize_run(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Run RAG optimization using a selected AI provider.

    Streams progress events back to the frontend, then sends the final result.
    """
    user_id = _get_user_id(connection)
    request_id = msg["id"]
    rag = _get_rag_manager(hass)

    if not rag or not rag.is_initialized:
        connection.send_error(request_id, ERR_STORAGE_ERROR, "RAG not initialized")
        return

    provider_name = msg["provider"]
    model = msg["model"]
    scope = msg.get("scope", "all")
    force = msg.get("force", False)

    # Get the AI provider instance
    agents = hass.data.get(DOMAIN, {}).get("agents", {})
    agent_compat = agents.get(provider_name)
    if not agent_compat:
        connection.send_error(
            request_id, ERR_AI_ERROR, f"Provider '{provider_name}' not configured"
        )
        return

    # Access the raw AIProvider from the agent wrapper
    provider = getattr(agent_compat, "_provider", None)
    if not provider:
        provider = getattr(getattr(agent_compat, "_agent", None), "_provider", None)
    if not provider:
        connection.send_error(
            request_id, ERR_AI_ERROR, f"Cannot access provider '{provider_name}'"
        )
        return

    try:
        from ..rag.optimizer import RAGOptimizer

        optimizer = RAGOptimizer(
            store=rag._store,
            embedding_provider=rag._embedding_provider,
            memory_manager=rag._memory_manager,
        )

        # Progress callback sends streaming events to the frontend
        async def progress_callback(event: dict[str, Any]) -> None:
            connection.send_message(
                {
                    "id": request_id,
                    "type": "event",
                    "event": event,
                }
            )

        # Send start event
        await progress_callback({"type": "start", "message": "Optimization started"})

        # Run optimization based on scope
        if scope == "sessions":
            result = await optimizer.optimize_sessions(
                provider, model, progress_callback, force=force
            )
        elif scope == "memories":
            result = await optimizer.optimize_memories(
                provider, model, user_id, progress_callback
            )
        else:
            result = await optimizer.optimize_all(
                provider, model, user_id, progress_callback, force=force
            )

        result_data = {"success": True, **result.to_dict()}

        # Send result as an event so subscribeMessage receives it
        await progress_callback({"type": "result", "data": result_data})

        connection.send_result(request_id, result_data)

    except Exception as err:
        _LOGGER.exception("RAG optimization failed")
        connection.send_error(request_id, ERR_AI_ERROR, f"Optimization failed: {err}")
