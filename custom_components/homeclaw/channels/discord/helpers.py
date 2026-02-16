"""Helper utilities for Discord channel implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ...storage import SessionStorage

_STORAGE_CACHE_PREFIX = f"{DOMAIN}_storage_"


def chunk_text(text: str, max_len: int) -> list[str]:
    """Chunk *text* into <= ``max_len`` pieces."""
    if not text:
        return [""]
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]


def normalize_id_list(raw: Any) -> set[str]:
    """Normalize IDs config value (list/string/newline) to set[str]."""
    if raw is None:
        return set()
    if isinstance(raw, str):
        values = [
            line.strip() for line in raw.replace(",", "\n").splitlines() if line.strip()
        ]
    else:
        values = [str(v).strip() for v in raw if str(v).strip()]
    return set(values)


def is_group_allowed(config: dict[str, Any], sender_id: str, channel_id: str) -> bool:
    """Check Discord guild message access under group_policy."""
    policy = str(config.get("group_policy", "open")).lower()
    if policy == "disabled":
        return False
    if policy == "open":
        return True

    raw = config.get("allowed_ids", [])
    if isinstance(raw, str):
        raw = [raw]
    allowed = {str(v) for v in raw if str(v).strip()}
    if not allowed:
        return False
    return str(sender_id) in allowed or str(channel_id) in allowed


def is_dm_allowed(config: dict[str, Any], sender_id: str, channel_id: str) -> bool:
    """Check Discord DM access under dm_policy."""
    policy = str(config.get("dm_policy", "pairing")).lower()
    if policy == "disabled":
        return False
    if policy == "open":
        return True

    # pairing/allowlist fallback: allow only explicit IDs.
    raw = config.get("allowed_ids", [])
    if isinstance(raw, str):
        raw = [raw]
    allowed = {str(v) for v in raw if str(v).strip()}
    if not allowed:
        return False
    return str(sender_id) in allowed or str(channel_id) in allowed


def get_storage(hass: HomeAssistant, user_id: str) -> SessionStorage:
    """Return cached SessionStorage instance for given user."""
    cache_key = f"{_STORAGE_CACHE_PREFIX}{user_id}"
    if cache_key not in hass.data:
        from ...storage import SessionStorage

        hass.data[cache_key] = SessionStorage(hass, user_id)
    return hass.data[cache_key]
