"""Helper utilities for Discord channel implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ...storage import SessionStorage

_STORAGE_CACHE_PREFIX = f"{DOMAIN}_storage_"
_LAST_TARGETS_KEY = f"{DOMAIN}_discord_last_targets"


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
    """Check Discord DM access under dm_policy.

    A sender is allowed when ANY of these are true:
    - dm_policy is ``"open"``
    - sender_id is in ``allowed_ids``
    - sender_id exists as a key in ``user_mapping`` or ``external_user_mapping``
      (meaning they completed pairing)
    """
    policy = str(config.get("dm_policy", "pairing")).lower()
    if policy == "disabled":
        return False
    if policy == "open":
        return True

    sid = str(sender_id)

    # Check user_mapping / external_user_mapping — paired users are always allowed.
    for mapping_key in ("user_mapping", "external_user_mapping"):
        mapping = config.get(mapping_key)
        if isinstance(mapping, dict) and sid in mapping:
            return True

    # pairing/allowlist fallback: allow only explicit IDs.
    raw = config.get("allowed_ids", [])
    if isinstance(raw, str):
        raw = [raw]
    allowed = {str(v) for v in raw if str(v).strip()}
    if not allowed:
        return False
    return sid in allowed or str(channel_id) in allowed


def get_storage(hass: HomeAssistant, user_id: str) -> SessionStorage:
    """Return cached SessionStorage instance for given user."""
    cache_key = f"{_STORAGE_CACHE_PREFIX}{user_id}"
    if cache_key not in hass.data:
        from ...storage import SessionStorage

        hass.data[cache_key] = SessionStorage(hass, user_id)
    return hass.data[cache_key]


def set_last_target(
    hass: HomeAssistant,
    *,
    ha_user_id: str,
    target_id: str,
    sender_id: str,
    is_group: bool,
) -> None:
    """Cache the most recent Discord target for a Homeclaw user."""
    cache = hass.data.setdefault(_LAST_TARGETS_KEY, {})
    cache[ha_user_id] = {
        "target_id": target_id,
        "sender_id": sender_id,
        "is_group": is_group,
    }


def get_last_target(hass: HomeAssistant, ha_user_id: str) -> dict[str, Any] | None:
    """Get cached most recent Discord target for a Homeclaw user."""
    cache = hass.data.get(_LAST_TARGETS_KEY, {})
    value = cache.get(ha_user_id)
    if isinstance(value, dict):
        return value
    return None
