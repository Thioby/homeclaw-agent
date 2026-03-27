"""WebSocket handlers for user-confirmed actions."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from ..core.pending_actions import pop_pending
from ..storage import Message
from ..tools.base import ToolRegistry
from ._common import CONFIRMABLE_TOOLS, ERR_STORAGE_ERROR, _get_storage, _now_iso

_LOGGER = logging.getLogger(__name__)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/dashboard/confirm",
        vol.Required("tool_call_id"): str,
        vol.Required("session_id"): str,
        vol.Optional("confirmed", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_confirm_dashboard(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Confirm or reject a pending dashboard action."""
    request_id = msg["id"]
    tool_call_id = msg["tool_call_id"]
    confirmed = msg["confirmed"]

    pending = pop_pending(tool_call_id)
    if not pending:
        connection.send_error(
            request_id, "not_found", "Pending action expired or not found"
        )
        return

    if not confirmed:
        connection.send_result(request_id, {"status": "rejected"})
        return

    try:
        tool_name = pending["tool_name"]
        if tool_name not in CONFIRMABLE_TOOLS:
            connection.send_error(
                request_id, "invalid_tool", f"Tool '{tool_name}' cannot be confirmed"
            )
            return
        params = {**pending["params"], "dry_run": False}

        result = await ToolRegistry.execute_tool(
            tool_name, params, hass=hass, config={}
        )

        result_output = {}
        if result.output:
            try:
                result_output = json.loads(result.output)
            except (json.JSONDecodeError, TypeError):
                result_output = {"message": result.output}

        user_id = connection.user.id if connection.user else "unknown"
        storage = _get_storage(hass, user_id)
        session_id = msg["session_id"]
        await storage.add_message(
            session_id,
            Message(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=f"Dashboard action confirmed: {result_output.get('message', 'done')}",
                timestamp=_now_iso(),
                status="completed",
            ),
        )

        connection.send_result(
            request_id,
            {
                "status": "success" if result.success else "error",
                "result": result_output,
            },
        )
    except Exception as exc:
        _LOGGER.exception("Error confirming dashboard action: %s", exc)
        connection.send_error(request_id, ERR_STORAGE_ERROR, str(exc))
