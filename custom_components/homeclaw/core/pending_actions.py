"""Cache for pending dashboard actions awaiting user confirmation."""

from __future__ import annotations

import time
from typing import Any

_pending: dict[str, dict[str, Any]] = {}
_TTL_SECONDS = 600  # 10 minutes


def store_pending(tool_call_id: str, tool_name: str, params: dict[str, Any]) -> None:
    """Cache a dry_run result for later confirmation."""
    _cleanup_expired()
    _pending[tool_call_id] = {
        "tool_name": tool_name,
        "params": params,
        "timestamp": time.time(),
    }


def pop_pending(tool_call_id: str) -> dict[str, Any] | None:
    """Retrieve and remove a pending action. Returns None if expired or missing."""
    _cleanup_expired()
    return _pending.pop(tool_call_id, None)


def _cleanup_expired() -> None:
    """Remove entries older than TTL."""
    now = time.time()
    expired = [k for k, v in _pending.items() if now - v["timestamp"] > _TTL_SECONDS]
    for k in expired:
        del _pending[k]
