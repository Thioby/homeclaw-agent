"""Approval gate for confirmable tool actions (human-in-the-loop).

The agent loop registers a Future keyed by tool_call_id, emits an approval
request to the UI, then awaits the Future. A separate websocket command
resolves it with the user's decision, resuming the loop in place. This mirrors
the suspend/resume pattern used by sibling agents (opencode, openclaw).
"""

from __future__ import annotations

import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

_pending: dict[str, asyncio.Future[bool]] = {}


def register_approval(tool_call_id: str) -> asyncio.Future[bool]:
    """Create and store a Future the agent loop will await for this tool call."""
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bool] = loop.create_future()
    _pending[tool_call_id] = future
    return future


def resolve_approval(tool_call_id: str, approved: bool) -> bool:
    """Resolve a waiting approval with the user's decision.

    Returns True if a live waiter was found and resolved, False otherwise.
    """
    future = _pending.get(tool_call_id)
    if future is None or future.done():
        return False
    future.set_result(approved)
    return True


def discard_approval(tool_call_id: str) -> None:
    """Remove a pending approval (after it resolves, times out, or is abandoned)."""
    _pending.pop(tool_call_id, None)
