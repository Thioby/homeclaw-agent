# Changelog

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
