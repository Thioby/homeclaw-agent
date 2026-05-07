# Changelog

## v1.5.0 — Panel UI redesign and OpenRouter free models

### Added
- **Panel UI redesign** — paper-tone "warm" aesthetic by default, with `tech` (high-contrast) and `ambient` (always-dark, gold accent) alternates. New `--hc-*` design token layer (light/dark for each aesthetic), system fonts in place of Roboto.
- **Settings → Appearance** — theme selector (light / dark / system) and aesthetic selector with live color-swatch preview. Choice persists to `localStorage`.
- **Sidebar redesign** — brand mark, inline "New conversation" button, search field, sessions grouped by date (Today / Yesterday / Earlier), foot status pulse with smart entity count.
- **Topbar** — replaces Telegram-style header. Shows session title in display serif, `<model> · N entities` meta in mono.
- **Empty-state status rail** — derives a "RIGHT NOW" snapshot from `hass.states` (lights on, climate mode + temperature, locks, open covers). Time-based greeting using the user's RAG `user_name`. Suggestion cards in a 2×2 grid; clicking a card injects the prompt into the composer and focuses the textarea.
- **Per-message avatar + meta-row** — square avatar (home icon for bot, initial for user) with name + monospaced timestamp above each message, replacing inline float-right time.
- **Composer paper-card** — single paper-tone card with auto-growing textarea, chip-bar (Attach + Provider + Model + Debug), square Send button. Mono footer with keyboard hint.
- **Smart entity count helper** — `lib/utils/entities.ts` filters `hass.states` to real devices/sensors (light/switch/sensor/binary_sensor/climate/cover/lock/fan/media_player/camera/vacuum/lawn_mower/water_heater/humidifier/valve/button) instead of counting bookkeeping entries.
- **Centralized icon set** — `Icon.svelte` with 22 inline SVG glyphs; new components consume it instead of inlining SVG.
- **OpenRouter free tier** — Tencent Hy3 Preview as the default with tool-calling support, plus a lightweight free model option.
- **Unified provider adapter layer** — single normalization layer across Anthropic / OpenAI / Gemini / OpenRouter / Groq / Local for tool-use payloads.

### Changed
- **OpenRouter default** model bumped to free Tencent Hy3 Preview.
- **Per-request model override** is now honored by all OpenAI-compatible providers.
- **OpenAI-compatible requests** log the resolved model name for easier debugging.
- **Emoji generation** uses the user's default provider instead of a hard-coded one.
- **Tool name prefix (`mcp__homeclaw__<tool>`)** is now idempotent — no double-prefixing on retries.
- **OpenAI adapter** converts `function` role to the appropriate tool format on the fly.

### Fixed
- **Provider selector** can be changed before the first message in a new conversation (was incorrectly locked).
- **Provider list** uses the backend-configured list and hides RAG-only providers from the chat selector.
- **Provider reset on refresh** — selected provider is restored across page reloads.
- **Array tool params** are properly serialized when forwarded to providers.
- **Per-subclass logger** for tools so log lines carry the correct module name.
- **Mobile composer overflow** — provider/model chips truncate with ellipsis, debug toggle and second footer line move to Settings, Send button stays in viewport on narrow screens (≤380px).
- **Avatar overflow** — multi-emoji values are clipped to the first grapheme and capped in font-size; bot avatar always uses the home icon for visual consistency.
- **Greeting** sources the user's name from RAG `user_name` (was incorrectly using the bot's `agent_name`).
- **Custom-element constructor** — `data-aesthetic` / `data-theme` attributes are applied via microtask to comply with the DOM spec (HA's `createElement` rejects elements with attributes set in the constructor).

### Removed
- **Telegram-style chat bubbles** — replaced with paper-card messages; no more tail triangles or float-right timestamps.
- **Floating round "New chat" FAB** — replaced with an inline button at the top of the sidebar.

## v1.4.0 — Anthropic OAuth port from opencode-anthropic-auth v1.8.0

### Breaking
- **OAuth endpoints migrated** from `console.anthropic.com` to `platform.claude.com`. Existing OAuth refresh tokens may need re-authentication. Home Assistant will prompt automatically via the standard reauth flow if old tokens are rejected.
- **OAuth scopes expanded** from 3 to 6 (added `user:sessions:claude_code`, `user:mcp_servers`, `user:file_upload`). Re-authentication required on first refresh after upgrade.

### Added
- Server-side classifier mitigations: CCH (content-consistency-hash) billing header, system prompt sanitization pipeline, identity swap to "Claude agent / Claude Agent SDK".
- "Create API Key" OAuth flow for Console plan users — exchanges OAuth access token for a permanent API key, then configures a regular Anthropic provider entry.
- `ANTHROPIC_BASE_URL` env override for proxies/dev (with `ANTHROPIC_INSECURE=1` for local TLS bypass).
- Tool name namespacing (`mcp__homeclaw__<tool>`) — bidirectional, transparent to the agent code.

### Changed
- User-Agent bumped to `claude-cli/2.1.87 (external, cli)`.
- Refresh token network errors retried with exponential backoff (2 retries, 0.5s/1s).
- Concurrent token refreshes coalesce on a single in-flight task (prevents 401 cascades).
- Refresh token re-read from storage per attempt (prevents stale-snapshot races).

### Removed
- Old `oauth.py` and flat `providers/anthropic_oauth.py` files — replaced by `providers/anthropic_oauth/` subpackage.

### Provenance
Code patterns and reverse-engineered values (CCH salt, classifier-fingerprint phrases, tool prefix convention) ported from MIT-licensed opencode-anthropic-auth v1.8.0 by Ex Machina.

## v1.3.1 — Agent loop hardening and Discord auto-compaction

### Fixed
- **Agent loop reliability** — tool validation, circuit breaker, compaction, and truncation now cooperate correctly. Final response is guaranteed even when the tool loop hits its iteration limit.
- **`allowed_tool_names` propagation** — wired at both `detect` call sites in `process()` and `process_stream()`, and at the `repair_tool_history` call site, so tool-name filtering is consistently enforced throughout the multi-turn loop.
- **Function-call parser decoupled from query processor** — `function_call_parser.py` no longer depends on internal query-processor state, improving testability and preventing stale-state bugs.
- **`response_parser.py` and `conversation.py`** — edge cases in response classification and conversation reconstruction that caused the agent to loop unnecessarily are resolved.

### Added
- **Discord auto-compaction** — when a Discord session grows beyond the token budget, conversation history is automatically compacted (summary + tool-call pruning) before the next request, preventing context-overflow errors on long Discord threads.
- **`token_estimator.py`** — lightweight token counter used by the compaction trigger to decide when to compact without making an extra API call.
- **`compaction.py`** — standalone compaction module: summarise-and-prune strategy with configurable keep-last-N turns.

### Changed
- **`tool_executor.py`** — emits richer event payloads so the circuit breaker in `query_processor` can distinguish hard failures from soft retries.
- **`storage.py`** — extended to persist compaction metadata (summary text, compacted-at turn index) alongside existing session data.

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
