"""Discord pairing flow helpers."""

from __future__ import annotations

import logging
import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import build_channel_runtime_config
from ...const import DOMAIN
from .helpers import normalize_id_list

_LOGGER = logging.getLogger(__name__)

_PAIRING_KEY = f"{DOMAIN}_discord_pairing_requests"
_PAIR_CODE_RE = re.compile(r"(?:^|\s)(?:pair\s+)?(\d{6})(?:\s|$)", re.IGNORECASE)


def create_pairing_request(
    hass: Any,
    *,
    sender_id: str,
    target_id: str,
    ttl_seconds: int = 600,
) -> dict[str, Any]:
    """Create or refresh a pairing request for a Discord sender."""
    _expire_requests(hass)
    existing = _find_request_by_sender(hass, sender_id)
    if existing:
        existing["expires_at"] = _expires_iso(ttl_seconds)
        return existing

    request = {
        "code": _generate_code(),
        "sender_id": sender_id,
        "target_id": target_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": _expires_iso(ttl_seconds),
    }
    store = hass.data.setdefault(_PAIRING_KEY, {})
    store[request["code"]] = request
    return request


def get_request_by_code(hass: Any, code: str) -> dict[str, Any] | None:
    """Get active pairing request by code."""
    _expire_requests(hass)
    value = hass.data.get(_PAIRING_KEY, {}).get(code)
    return value if isinstance(value, dict) else None


def consume_request(hass: Any, code: str) -> dict[str, Any] | None:
    """Remove and return active pairing request by code."""
    _expire_requests(hass)
    store = hass.data.get(_PAIRING_KEY, {})
    value = store.pop(code, None)
    return value if isinstance(value, dict) else None


async def persist_pairing(
    hass: Any,
    *,
    ha_user_id: str,
    sender_id: str,
) -> dict[str, Any]:
    """Persist Discord pairing into Homeclaw options and runtime config."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise RuntimeError("Homeclaw config entry not found")

    entry = entries[0]
    options = dict(getattr(entry, "options", {}) or {})
    channel_cfg = dict(options.get("channel_discord", {}) or {})

    allowed = normalize_id_list(channel_cfg.get("allowed_ids", []))
    allowed.add(str(sender_id))
    channel_cfg["allowed_ids"] = sorted(allowed)

    mapping = dict(options.get("external_user_mapping", {}) or {})
    mapping[str(sender_id)] = ha_user_id

    channel_mapping = dict(channel_cfg.get("user_mapping", {}) or {})
    channel_mapping[str(sender_id)] = ha_user_id
    channel_cfg["user_mapping"] = channel_mapping
    channel_cfg["external_user_mapping"] = channel_mapping

    options["channel_discord"] = channel_cfg
    options["external_user_mapping"] = mapping
    hass.config_entries.async_update_entry(entry, options=options)

    runtime = await build_channel_runtime_config(hass, {**entry.data, **options})
    manager = hass.data.get(DOMAIN, {}).get("channel_manager")
    channel = (
        manager.get_channel("discord") if hasattr(manager, "get_channel") else None
    )
    if channel and hasattr(channel, "_config"):
        channel._config.update(runtime.get("channel_discord", {}))
        channel._config["user_mapping"] = channel_mapping
        channel._config["external_user_mapping"] = channel_mapping
        _LOGGER.debug(
            "persist_pairing: runtime config updated for sender=%s", sender_id
        )
    else:
        _LOGGER.warning(
            "persist_pairing: could not update runtime config — "
            "channel_manager=%s channel=%s. "
            "Config entry was updated but in-memory config is stale until restart.",
            "found" if manager else "missing",
            "found" if channel else "missing",
        )

    return {
        "sender_id": str(sender_id),
        "ha_user_id": ha_user_id,
        "allowed_ids": channel_cfg["allowed_ids"],
    }


def _find_request_by_sender(hass: Any, sender_id: str) -> dict[str, Any] | None:
    store = hass.data.get(_PAIRING_KEY, {})
    for value in store.values():
        if isinstance(value, dict) and value.get("sender_id") == sender_id:
            return value
    return None


def _expire_requests(hass: Any) -> None:
    store = hass.data.get(_PAIRING_KEY, {})
    if not isinstance(store, dict):
        hass.data[_PAIRING_KEY] = {}
        return

    now = datetime.now(timezone.utc)
    stale_codes = []
    for code, request in store.items():
        if not isinstance(request, dict):
            stale_codes.append(code)
            continue
        expires_at = request.get("expires_at", "")
        try:
            expires = datetime.fromisoformat(expires_at)
        except Exception:
            stale_codes.append(code)
            continue
        if expires <= now:
            stale_codes.append(code)

    for code in stale_codes:
        store.pop(code, None)


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _expires_iso(ttl_seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()


def extract_pairing_code(text: str) -> str | None:
    """Extract 6-digit pairing code from message text."""
    match = _PAIR_CODE_RE.search(text.strip())
    if match:
        return match.group(1)
    return None
