"""External chat channels subsystem.

Provides:
- ``MessageIntake`` — shared message entry point (Phase 1)
- ``Channel`` ABC, ``ChannelTarget``, ``MessageEnvelope`` — channel contract (Phase 2)
- ``ChannelRateLimiter`` — per-user rate limiting (Phase 2)
- ``ChannelRegistry`` — decorator-based channel registration (Phase 2)
- ``ChannelManager`` — lifecycle owner for all channels (Phase 2)
"""

from __future__ import annotations

from .base import (
    Channel,
    ChannelRateLimiter,
    ChannelRegistry,
    ChannelTarget,
    MessageEnvelope,
)
from .discord import DiscordChannel
from .intake import MessageIntake
from .manager import ChannelManager

__all__ = [
    "Channel",
    "ChannelManager",
    "ChannelRateLimiter",
    "ChannelRegistry",
    "ChannelTarget",
    "DiscordChannel",
    "MessageEnvelope",
    "MessageIntake",
]
