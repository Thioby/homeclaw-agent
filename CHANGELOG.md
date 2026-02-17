# Changelog

## v1.1.1 — Scheduler fix & lifecycle refactor

### Fixed
- **Scheduler jobs running multiple times** — with 3 config entries, every scheduled job ran 3× instead of once. Root cause: async race condition in `_initialize_proactive` where all concurrent `async_setup_entry` calls passed the boolean guard before any could set it to `True`.
- **Unloading one config entry killed all subsystems** — `async_unload_entry` used to wipe the entire `hass.data[DOMAIN]`, destroying the scheduler, RAG, and channels for all providers. Now it only removes the unloaded provider's agent and config; global subsystems stay alive until the last entry is removed.
- **Partial init failure leaked resources** — if the scheduler failed to start after the heartbeat was already running, the heartbeat was never stopped. Now the proactive group has proper rollback.

### Changed
- **New `SubsystemLifecycle` class** (`lifecycle.py`) — replaces 6 ad-hoc init/shutdown functions and 3 different guard mechanisms with one `asyncio.Lock`, entry refcounting, and ordered init/shutdown with rollback.
- **Extracted `services.py`** — moved 7 service handlers out of `__init__.py`, added shared `_get_agent()` helper to remove ~60 lines of copy-paste.
- **`__init__.py` reduced from 741 to 235 lines** (68% smaller).

## v1.1.0 — Discord Integration

### Added
- **Discord channel** — talk to HomeClaw from Discord DMs or server channels.
- **Pairing flow** — link your Discord account to your HA user via a one-time code.
- **Channel framework** — base classes, rate limiter, and registry for external channels. Future channels (Telegram, etc.) plug into the same system.
- **MessageIntake** — shared chat pipeline so all channels (web panel, Discord, voice) use the same AI logic.
- **`check_discord_connection` tool** — the agent can verify if Discord is online.
- **`history_limit` config** — caps how many messages are loaded from session history (default: 20 for Discord).

### Fixed
- Removed incorrect `mcp_` prefix from Anthropic OAuth tool names — tools now match between system prompt and function declarations.
- Fixed `ToolExecutor` not propagating `tool_call_id` in yielded events (caused Anthropic 400 errors).
- Fixed race condition where two `DiscordChannel` instances could start from a single config entry.
- Fixed message-ID dedup to prevent duplicate processing of the same Discord message.
- Fixed provider/model resolution — Discord now reads user preferences instead of falling back to hardcoded defaults.

## v1.0.0

Initial release.
