"""WebSocket handlers for user-confirmed actions."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from ..core.pending_actions import resolve_approval

_LOGGER = logging.getLogger(__name__)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/dashboard/confirm",
        vol.Required("tool_call_id"): str,
        vol.Optional("session_id"): str,
        vol.Optional("confirmed", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_confirm_dashboard(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Resolve a pending confirmable action so the suspended agent loop resumes.

    Approve executes the real action inline (back in the loop, with the result
    fed to the model); reject lets the model continue knowing it was declined.
    """
    request_id = msg["id"]
    tool_call_id = msg["tool_call_id"]
    confirmed = msg["confirmed"]

    resolved = resolve_approval(tool_call_id, confirmed)
    if not resolved:
        connection.send_error(
            request_id, "not_found", "Pending action expired or not found"
        )
        return

    connection.send_result(
        request_id, {"status": "accepted" if confirmed else "rejected"}
    )
