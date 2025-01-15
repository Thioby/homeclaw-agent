"""Shared helpers, validators, and constants for WebSocket handlers."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN
from ..storage import MAX_MESSAGE_LENGTH, SessionStorage

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Error codes
ERR_SESSION_NOT_FOUND = "session_not_found"
ERR_INVALID_INPUT = "invalid_input"
ERR_STORAGE_ERROR = "storage_error"
ERR_AI_ERROR = "ai_error"
ERR_RATE_LIMITED = "rate_limited"

# Validation constants
MAX_TITLE_LENGTH = 200
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

# Storage cache key prefix
_STORAGE_CACHE_PREFIX = f"{DOMAIN}_storage_"


def _validate_session_id(value: Any) -> str:
    """Validate that session_id is a valid UUID format."""
    if not isinstance(value, str):
        raise vol.Invalid("Session ID must be a string")
    if not UUID_PATTERN.match(value):
        raise vol.Invalid("Session ID must be a valid UUID format")
    return value


def _validate_title(value: Any) -> str:
    """Validate and truncate title to max length."""
    if not isinstance(value, str):
        raise vol.Invalid("Title must be a string")
    if len(value) == 0:
        raise vol.Invalid("Title cannot be empty")
    # Truncate to max length
    return value[:MAX_TITLE_LENGTH]


def _validate_message(value: Any) -> str:
    """Validate message content with length limit."""
    if not isinstance(value, str):
        raise vol.Invalid("Message must be a string")
    if len(value) == 0:
        raise vol.Invalid("Message cannot be empty")
    if len(value) > MAX_MESSAGE_LENGTH:
        raise vol.Invalid(f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH}")
    return value


def _get_user_id(connection: websocket_api.ActiveConnection) -> str:
    """Extract user ID from WebSocket connection."""
    if connection.user and connection.user.id:
        return connection.user.id
    return "default"


def _get_storage(hass: HomeAssistant, user_id: str) -> SessionStorage:
    """Get or create a cached SessionStorage instance for a user.

    Caching storage instances improves performance by avoiding repeated
    migration and cleanup checks, and ensures consistent state across requests.
    """
    cache_key = f"{_STORAGE_CACHE_PREFIX}{user_id}"
    if cache_key not in hass.data:
        _LOGGER.info("Creating NEW SessionStorage for user: %s", user_id)
        hass.data[cache_key] = SessionStorage(hass, user_id)
    else:
        _LOGGER.debug("Using CACHED SessionStorage for user: %s", user_id)

    storage_instance = hass.data[cache_key]
    _LOGGER.debug("Storage instance id: %s", id(storage_instance))
    return storage_instance


def _get_rag_manager(hass: HomeAssistant) -> Any:
    """Get the RAG manager or None."""
    if DOMAIN not in hass.data:
        return None
    return hass.data[DOMAIN].get("rag_manager")
