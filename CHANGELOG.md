# Changelog

## v1.2.1 — Progressive tool loading, Discord resilience, and OAuth reauth

### Added
- **Progressive tool loading** — tools are now split into CORE (always loaded) and ON_DEMAND tiers. Only CORE tool schemas are sent to the LLM by default (~5K fewer tokens per request). A new `load_tool` meta-tool lets the LLM activate additional tools on demand during a conversation.
- **`ToolTier` enum and `short_description` field** on the `Tool` base class — enables the two-tier loading system.
- **`ToolRegistry.get_core_tools()` and `list_on_demand_ids()`** — public API for the new tier system.
- **OAuth re-authentication flow** — when a refresh token becomes permanently invalid (`invalid_grant`), the integration now triggers HA's built-in reauth flow instead of silently failing. Covers both Anthropic and Gemini OAuth providers.
- **`config_flow.py` reauth steps** — `async_step_reauth` / `async_step_reauth_confirm` with full PKCE exchange for both Anthropic and Gemini OAuth.
- **YAML utilities extracted** — new `utils/yaml_io.py`, `utils/yaml_tags.py`, `utils/yaml_sections.py`, and `utils/yaml_writer.py` modules replace inline YAML handling in `integration_manager.py`. Includes `CONFIG_WRITE_LOCK`, atomic file writes, HA tag preservation (`!include`, `!secret`), and section-level merge/remove.
- **Tests** — `test_load_tool.py` (618 lines) and expanded `test_integration_manager.py` and `test_dashboard_manager.py`.

### Fixed
- **Discord gateway reconnect** — replaced fixed-delay reconnect with exponential backoff (5s → 120s max, 25% jitter) and a 50-attempt limit. Added HELLO timeout (30s) for zombie connection detection. Stale resume URLs are cleared and the aiohttp session is properly closed before reconnecting.
- **Discord pairing persistence** — `persist_pairing` now resolves the config entry via the lifecycle manager instead of blindly picking `entries[0]`, preventing writes to the wrong entry in multi-provider setups.
- **OAuth token refresh race condition** — both Anthropic and Gemini providers now re-read persisted tokens under the refresh lock, so a concurrent refresh by another task is picked up instead of triggering a duplicate refresh.
- **`OAuthRefreshError` / `GeminiOAuthRefreshError` now carry `is_permanent` flag** — callers can distinguish transient network errors from revoked tokens.
- **YAML merger bug** — fixed section merging in `integration_manager` that could corrupt `configuration.yaml` when HA-specific tags (`!include`, `!secret`) were present.
- **`integration_manager.py` reduced by ~310 lines** — YAML logic extracted to `utils/` modules, eliminating duplication with `dashboard_manager.py`.

### Changed
- **`agent_compat.py`** — `_get_tools_for_provider()` now calls `get_core_tools()` instead of `get_all_tools()`, and the system prompt includes short descriptions of available ON_DEMAND tools.
- **`query_processor.py`** — new `_expand_loaded_tools()` static method detects `load_tool` results and dynamically injects activated tool schemas into the multi-turn loop. Includes security checks (ON_DEMAND tier, enabled, not in `denied_tools`).
- **`dashboard_manager.py`** — refactored to use shared `utils/yaml_writer` instead of its own YAML helpers.

## v1.1.2 — Tool message persistence and history reconstruction

### Fixed
- **Tool call context was lost in non-streaming chat path** — tool events (`tool_call`, `tool_result`) are now persisted in storage during message processing, so later turns keep full context.
- **Conversation history dropped tool steps** — stored tool messages are now reconstructed into provider-ready history (`assistant` tool-call JSON + `function` tool-result entries).
- **Storage schema missing tool metadata** — added migration from data v2 to v3 with `content_blocks` and `tool_call_id` fields for all stored messages.

### Changed
- **Extended message roles in storage** — `Message.role` now supports `tool_use` and `tool_result` in addition to `user`, `assistant`, and `system`.
- **Test coverage updated** — storage and websocket tests now cover v3 migration and tool message persistence/rebuild behavior.

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
