"""WebSocket handlers for session management (list, get, create, delete, rename, emoji)."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN, VALID_PROVIDERS
from ._common import (
    ERR_AI_ERROR,
    ERR_SESSION_NOT_FOUND,
    ERR_STORAGE_ERROR,
    _get_storage,
    _get_user_id,
    _validate_session_id,
    _validate_title,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Regex to extract the first emoji from AI response
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\U00002702-\U000027B0"
    r"\U0000FE00-\U0000FE0F"
    r"\U0001F000-\U0001F02F"
    r"\U00002600-\U000026FF"
    r"\U0000200D"
    r"\U00002764]",
    re.UNICODE,
)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/sessions/list",
    }
)
@websocket_api.async_response
async def ws_list_sessions(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List all sessions for current user."""
    user_id = _get_user_id(connection)

    try:
        storage = _get_storage(hass, user_id)
        sessions = await storage.list_sessions()
        connection.send_result(msg["id"], {"sessions": [asdict(s) for s in sessions]})
    except Exception as err:
        _LOGGER.exception("Failed to list sessions for user %s", user_id)
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to load sessions")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/sessions/get",
        vol.Required("session_id"): _validate_session_id,
    }
)
@websocket_api.async_response
async def ws_get_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get a session with all messages."""
    user_id = _get_user_id(connection)
    session_id = msg["session_id"]

    try:
        storage = _get_storage(hass, user_id)
        session = await storage.get_session(session_id)
        if session is None:
            connection.send_error(msg["id"], ERR_SESSION_NOT_FOUND, "Session not found")
            return

        messages = await storage.get_session_messages(session_id)
        connection.send_result(
            msg["id"],
            {
                "session": asdict(session),
                "messages": [asdict(m) for m in messages],
            },
        )
    except ValueError:
        connection.send_error(msg["id"], ERR_SESSION_NOT_FOUND, "Session not found")
    except Exception as err:
        _LOGGER.exception("Failed to get session %s for user %s", session_id, user_id)
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to load session")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/sessions/create",
        vol.Required("provider"): vol.In(VALID_PROVIDERS),
        vol.Optional("title"): _validate_title,
    }
)
@websocket_api.async_response
async def ws_create_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new session."""
    user_id = _get_user_id(connection)
    provider = msg["provider"]

    _LOGGER.info("Creating new session for user %s, provider: %s", user_id, provider)

    try:
        storage = _get_storage(hass, user_id)
        session = await storage.create_session(
            provider=provider, title=msg.get("title")
        )
        _LOGGER.info("Session created: %s for user %s", session.session_id, user_id)
        connection.send_result(msg["id"], asdict(session))

        # Async: sanitize and index the user's previous session into RAG
        hass.async_create_task(
            _sanitize_previous_session(hass, user_id, storage, session.session_id)
        )
    except Exception as err:
        _LOGGER.exception("Failed to create session for user %s", user_id)
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to create session")


async def _sanitize_previous_session(
    hass: HomeAssistant,
    user_id: str,
    storage: Any,
    new_session_id: str,
) -> None:
    """Sanitize and index the user's previous session into RAG.

    Called as a background task after creating a new session.
    Finds the most recent session before the new one, sanitizes it
    via LLM to remove ephemeral state data, and indexes the cleaned
    version into the RAG session store.

    Args:
        hass: Home Assistant instance.
        user_id: The user's ID.
        storage: SessionStorage instance for the user.
        new_session_id: The newly created session ID (to exclude it).
    """
    if DOMAIN not in hass.data:
        return

    rag_manager = hass.data[DOMAIN].get("rag_manager")
    if not rag_manager or not rag_manager.is_initialized:
        return

    try:
        # Find the previous session (most recent that isn't the new one)
        sessions = await storage.list_sessions()
        previous = None
        for s in sessions:
            if s.session_id != new_session_id:
                previous = s
                break  # list_sessions returns sorted by updated_at desc

        if not previous:
            _LOGGER.debug("No previous session to sanitize for user %s", user_id)
            return

        # Load messages from the previous session
        messages = await storage.get_session_messages(previous.session_id)
        msg_dicts = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant") and m.status == "completed"
        ]

        if len(msg_dicts) < 4:
            _LOGGER.debug(
                "Previous session %s has only %d messages, skipping sanitization",
                previous.session_id,
                len(msg_dicts),
            )
            return

        # Get provider/model for sanitization from user preferences
        provider, model = await _get_sanitization_provider(hass, storage)
        if not provider:
            _LOGGER.debug("No AI provider available for session sanitization")
            return

        chunks = await rag_manager.sanitize_and_index_session(
            session_id=previous.session_id,
            messages=msg_dicts,
            provider=provider,
            model=model,
        )

        _LOGGER.info(
            "Sanitized and indexed previous session %s: %d chunks (user %s)",
            previous.session_id,
            chunks,
            user_id,
        )

        # Check if we need to archive old sessions (auto-compression)
        try:
            archive_result = await rag_manager.archive_old_sessions(
                provider=provider, model=model
            )
            if archive_result:
                _LOGGER.info(
                    "Auto-archived %d old sessions (%d chunks) into summary",
                    archive_result.get("sessions_archived", 0),
                    archive_result.get("chunks_removed", 0),
                )
        except Exception as archive_err:
            _LOGGER.debug("Auto-archival check failed (non-critical): %s", archive_err)

    except Exception as e:
        _LOGGER.warning("Background session sanitization failed: %s", e)


async def _get_sanitization_provider(
    hass: HomeAssistant,
    storage: Any,
) -> tuple[Any, str | None]:
    """Get the AI provider and model for session sanitization.

    Priority:
    1. rag_optimizer_provider/model from user preferences
    2. default_provider/model from user preferences
    3. First available provider from configured agents

    Args:
        hass: Home Assistant instance.
        storage: SessionStorage for reading preferences.

    Returns:
        Tuple of (provider_instance, model_name) or (None, None).
    """
    agents = hass.data.get(DOMAIN, {}).get("agents", {})
    if not agents:
        return None, None

    # Read user preferences
    try:
        prefs = await storage.get_preferences()
    except Exception:
        prefs = {}

    # Priority 1: RAG optimizer config
    provider_name = prefs.get("rag_optimizer_provider")
    model = prefs.get("rag_optimizer_model")

    # Priority 2: Default provider
    if not provider_name:
        provider_name = prefs.get("default_provider")
        model = prefs.get("default_model")

    # Priority 3: First available
    if not provider_name or provider_name not in agents:
        provider_name = next(iter(agents))
        model = None

    agent_compat = agents.get(provider_name)
    if not agent_compat:
        return None, None

    # Access the raw AIProvider from the agent wrapper
    provider = getattr(agent_compat, "_provider", None)
    if not provider:
        provider = getattr(getattr(agent_compat, "_agent", None), "_provider", None)

    return provider, model


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/sessions/delete",
        vol.Required("session_id"): _validate_session_id,
    }
)
@websocket_api.async_response
async def ws_delete_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a session."""
    user_id = _get_user_id(connection)

    try:
        storage = _get_storage(hass, user_id)
        await storage.delete_session(msg["session_id"])

        # Clean up uploaded files for this session (if any)
        try:
            from ..file_processor import cleanup_session_uploads

            await cleanup_session_uploads(hass, msg["session_id"])
        except Exception:
            pass  # Non-critical -- don't fail the delete

        # Remove session from RAG index (if available)
        try:
            if DOMAIN in hass.data:
                rag_manager = hass.data[DOMAIN].get("rag_manager")
                if rag_manager and rag_manager.is_initialized:
                    await rag_manager.remove_session_index(msg["session_id"])
        except Exception:
            pass  # Non-critical -- don't fail the delete

        connection.send_result(msg["id"], {"success": True})
    except Exception as err:
        _LOGGER.exception(
            "Failed to delete session %s for user %s", msg["session_id"], user_id
        )
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to delete session")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/sessions/rename",
        vol.Required("session_id"): _validate_session_id,
        vol.Required("title"): _validate_title,
    }
)
@websocket_api.async_response
async def ws_rename_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Rename a session."""
    user_id = _get_user_id(connection)

    try:
        storage = _get_storage(hass, user_id)
        success = await storage.rename_session(msg["session_id"], msg["title"])
        if success:
            connection.send_result(msg["id"], {"success": True})
        else:
            connection.send_error(msg["id"], ERR_SESSION_NOT_FOUND, "Session not found")
    except Exception as err:
        _LOGGER.exception(
            "Failed to rename session %s for user %s", msg["session_id"], user_id
        )
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to rename session")


def _extract_emoji(text: str) -> str:
    """Extract the first emoji from a text string.

    Args:
        text: The text to search for emoji.

    Returns:
        The first emoji found, or empty string if none.
    """
    match = _EMOJI_RE.search(text)
    return match.group(0) if match else ""


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/sessions/generate_emoji",
        vol.Required("session_id"): _validate_session_id,
        vol.Required("title"): _validate_title,
    }
)
@websocket_api.async_response
async def ws_generate_emoji(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Generate an emoji for a session title using the first available AI provider.

    This is a fire-and-forget call from the frontend. It asks the AI for a single
    emoji that represents the session title, saves it, and returns the result.
    """
    user_id = _get_user_id(connection)
    session_id = msg["session_id"]
    title = msg["title"]

    try:
        # Find the first available AI provider
        agents = hass.data.get(DOMAIN, {}).get("agents", {})
        if not agents:
            _LOGGER.debug("No AI agents configured, skipping emoji generation")
            connection.send_result(msg["id"], {"emoji": ""})
            return

        # Pick the first available provider
        provider_name = next(iter(agents))
        agent = agents[provider_name]
        provider = agent._provider

        # Simple one-shot prompt — ask for a single emoji
        prompt = (
            "Respond with exactly ONE emoji that best represents this chat conversation title. "
            "Only output the emoji, nothing else. No text, no explanation.\n\n"
            f"Title: {title}"
        )

        response = await provider.get_response(
            [{"role": "user", "content": prompt}],
        )

        emoji = _extract_emoji(response.strip())
        if not emoji:
            # Fallback: use the raw response if it looks like a single character
            cleaned = response.strip()
            if len(cleaned) <= 4:  # Emoji can be up to 4 bytes
                emoji = cleaned
            else:
                emoji = ""

        if emoji:
            storage = _get_storage(hass, user_id)
            await storage.update_session_emoji(session_id, emoji)
            _LOGGER.debug("Generated emoji '%s' for session %s", emoji, session_id)

        connection.send_result(msg["id"], {"emoji": emoji})

    except Exception:
        _LOGGER.exception("Failed to generate emoji for session %s", session_id)
        # Non-critical — return empty emoji, don't fail the request
        connection.send_result(msg["id"], {"emoji": ""})
