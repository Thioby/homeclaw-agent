"""Channel ABC and supporting dataclasses for external chat channels.

Provides the base contract that all channels (Telegram, Discord, etc.) must
implement, plus shared helpers: user resolution, session keying, allowlist
check, and per-user rate limiting.

Usage:
    @ChannelRegistry.register("telegram")
    class TelegramChannel(Channel):
        id = "telegram"
        name = "Telegram"
        ...
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .intake import MessageIntake

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ChannelTarget:
    """Identifies where to send a response back.

    Attributes:
        channel_id: Channel identifier (e.g. "telegram", "discord").
        target_id: Platform-specific target (chat_id, channel_id).
        extra: Optional extra routing data (guild_id, thread info, etc.).
    """

    channel_id: str
    target_id: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageEnvelope:
    """Normalized inbound message from any channel.

    Every channel converts its raw platform event into this format
    before passing it to the AI pipeline via ``MessageIntake``.

    Attributes:
        text: Message content.
        channel: Channel identifier (matches ``Channel.id``).
        sender_id: Platform-specific sender ID.
        sender_name: Human-readable display name.
        target: Where to route the response.
        ha_user_id: Resolved HA user ID (or shadow user, never "default").
        is_group: True if the message came from a group chat.
        thread_id: Thread or topic ID if applicable.
        attachments: File attachments (platform-specific dicts).
        metadata: Additional platform-specific data.
    """

    text: str
    channel: str
    sender_id: str
    sender_name: str
    target: ChannelTarget
    ha_user_id: str
    is_group: bool = False
    thread_id: str | None = None
    attachments: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class ChannelRateLimiter:
    """Per-user sliding-window rate limiter for external channels.

    Tracks request timestamps per user over two windows (minute / hour)
    and rejects requests that exceed either limit.

    To prevent unbounded memory growth from many unique senders, the
    limiter caps the number of tracked users and evicts the oldest
    entries when the cap is reached.

    Args:
        max_per_minute: Maximum requests allowed per 60-second window.
        max_per_hour: Maximum requests allowed per 3600-second window.
        max_tracked_users: Maximum number of unique users to track.
            When exceeded, the oldest half of users are evicted.
    """

    _DEFAULT_MAX_USERS = 10_000

    def __init__(
        self,
        max_per_minute: int = 10,
        max_per_hour: int = 60,
        max_tracked_users: int = _DEFAULT_MAX_USERS,
    ) -> None:
        self._max_minute = max_per_minute
        self._max_hour = max_per_hour
        self._max_tracked_users = max_tracked_users
        self._minute_buckets: dict[str, list[float]] = {}
        self._hour_buckets: dict[str, list[float]] = {}

    def allow(self, user_id: str) -> bool:
        """Check whether *user_id* is within rate limits.

        Returns ``True`` if the request is allowed, ``False`` otherwise.
        As a side-effect, records the current timestamp for the user.
        """
        now = time.monotonic()

        # --- evict stale users if we hit the cap ---
        if len(self._hour_buckets) >= self._max_tracked_users:
            self._evict_stale(now)

        # --- minute window ---
        minute_ts = self._minute_buckets.setdefault(user_id, [])
        cutoff_minute = now - 60.0
        minute_ts[:] = [t for t in minute_ts if t > cutoff_minute]
        if len(minute_ts) >= self._max_minute:
            return False

        # --- hour window ---
        hour_ts = self._hour_buckets.setdefault(user_id, [])
        cutoff_hour = now - 3600.0
        hour_ts[:] = [t for t in hour_ts if t > cutoff_hour]
        if len(hour_ts) >= self._max_hour:
            return False

        # Both windows OK — record and allow
        minute_ts.append(now)
        hour_ts.append(now)
        return True

    def _evict_stale(self, now: float) -> None:
        """Remove users with no recent activity from the buckets.

        First removes users with no timestamps in the hour window.
        If still over cap, drops the oldest half by last-seen time.
        """
        cutoff_hour = now - 3600.0
        stale_users = [
            uid
            for uid, ts in self._hour_buckets.items()
            if not ts or ts[-1] <= cutoff_hour
        ]
        for uid in stale_users:
            self._minute_buckets.pop(uid, None)
            self._hour_buckets.pop(uid, None)

        # If still over cap, evict oldest half
        if len(self._hour_buckets) >= self._max_tracked_users:
            by_last_seen = sorted(
                self._hour_buckets.items(),
                key=lambda item: item[1][-1] if item[1] else 0.0,
            )
            evict_count = len(by_last_seen) // 2
            for uid, _ in by_last_seen[:evict_count]:
                self._minute_buckets.pop(uid, None)
                self._hour_buckets.pop(uid, None)

    def reset(self, user_id: str | None = None) -> None:
        """Reset rate limit state.

        Args:
            user_id: If given, reset only that user. Otherwise reset all.
        """
        if user_id:
            self._minute_buckets.pop(user_id, None)
            self._hour_buckets.pop(user_id, None)
        else:
            self._minute_buckets.clear()
            self._hour_buckets.clear()


# ---------------------------------------------------------------------------
# Channel registry (decorator-based, same pattern as ToolRegistry)
# ---------------------------------------------------------------------------


class ChannelRegistry:
    """Registry for channel implementations.

    Usage::

        @ChannelRegistry.register("telegram")
        class TelegramChannel(Channel):
            ...

        # Later:
        cls = ChannelRegistry.get("telegram")
        all_channels = ChannelRegistry.all()
    """

    _channels: ClassVar[dict[str, type[Channel]]] = {}

    @classmethod
    def register(cls, channel_id: str):
        """Decorator that registers a Channel subclass under *channel_id*."""

        def decorator(channel_cls: type[Channel]):
            if channel_id in cls._channels:
                _LOGGER.warning(
                    "Channel %s already registered, overwriting with %s",
                    channel_id,
                    channel_cls.__name__,
                )
            cls._channels[channel_id] = channel_cls
            return channel_cls

        return decorator

    @classmethod
    def get(cls, channel_id: str) -> type[Channel] | None:
        """Return the channel class for *channel_id*, or None."""
        return cls._channels.get(channel_id)

    @classmethod
    def all(cls) -> dict[str, type[Channel]]:
        """Return a copy of all registered channels."""
        return dict(cls._channels)

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (used in tests)."""
        cls._channels.clear()


# ---------------------------------------------------------------------------
# Channel ABC
# ---------------------------------------------------------------------------


class Channel(ABC):
    """Base class for all external message channels.

    Subclasses must set ``id`` and ``name`` class attributes, and implement
    the three abstract methods: ``async_setup``, ``async_teardown``, and
    ``send_response``.

    The constructor wires up ``hass``, ``MessageIntake``, per-channel config,
    and a ``ChannelRateLimiter`` with configurable limits.
    """

    id: str = ""
    name: str = ""

    def __init__(
        self,
        hass: HomeAssistant,
        intake: MessageIntake,
        config: dict[str, Any],
    ) -> None:
        self._hass = hass
        self._intake = intake
        self._config = config
        self._rate_limiter = ChannelRateLimiter(
            max_per_minute=config.get("rate_limit", 10),
            max_per_hour=config.get("rate_limit_hour", 60),
        )

    # --- Abstract interface ---

    @abstractmethod
    async def async_setup(self) -> None:
        """Start listening for inbound messages."""

    @abstractmethod
    async def async_teardown(self) -> None:
        """Stop listening and clean up resources."""

    @abstractmethod
    async def send_response(self, target: ChannelTarget, text: str) -> None:
        """Send a text response back to the originating channel."""

    # --- Optional overrides ---

    async def send_typing_indicator(self, target: ChannelTarget) -> None:
        """Show a typing indicator. Override if the platform supports it."""

    async def send_media(self, target: ChannelTarget, data: bytes, mime: str) -> None:
        """Send binary media back. Override if supported."""

    @property
    def is_available(self) -> bool:
        """Whether this channel is connected and operational."""
        return True

    # --- Shared helpers ---

    def _resolve_user_id(self, sender_id: str) -> str:
        """Map an external sender to an HA user or create an isolated shadow user.

        Looks up ``user_mapping`` in channel config first.  If no mapping
        exists, returns ``"{channel_id}_{sender_id}"`` so external users
        never share storage with real HA users or with each other across
        channels.

        Args:
            sender_id: Platform-specific sender identifier.

        Returns:
            HA user ID string (mapped or shadow).
        """
        mapping = self._config.get("user_mapping")
        if not isinstance(mapping, dict):
            mapping = self._config.get("external_user_mapping", {})
        mapped = mapping.get(str(sender_id)) if isinstance(mapping, dict) else None
        if mapped:
            return mapped
        return f"{self.id}_{sender_id}"

    def _session_key(self, envelope: MessageEnvelope) -> str:
        """Deterministic session key based on channel context.

        Strategy:
          - Thread: ``"{channel}_thread_{thread_id}"``
          - Group:  ``"{channel}_group_{target_id}"``
          - DM:     ``"{channel}_{sender_id}"``

        Args:
            envelope: Normalized inbound message.

        Returns:
            Session key string.
        """
        if envelope.thread_id:
            return f"{self.id}_thread_{envelope.thread_id}"
        if envelope.is_group:
            return f"{self.id}_group_{envelope.target.target_id}"
        return f"{self.id}_{envelope.sender_id}"

    def _is_allowed(self, sender_id: str, target_id: str) -> bool:
        """Check if sender or target is in the channel's allowlist.

        If no ``allowed_ids`` are configured, all senders are allowed
        (opt-in security model).  The allowlist is normalized to a set
        of strings so that a misconfigured scalar value (e.g. ``"12345"``
        instead of ``["12345"]``) does not cause substring matching.

        Args:
            sender_id: Platform sender identifier.
            target_id: Platform target (chat/channel) identifier.

        Returns:
            True if allowed, False if blocked.
        """
        raw = self._config.get("allowed_ids", [])
        # Normalize: string → single-element list, then coerce all to str
        if isinstance(raw, str):
            raw = [raw]
        allowed = {str(v) for v in raw} if raw else set()
        if not allowed:
            return True
        return str(sender_id) in allowed or str(target_id) in allowed
