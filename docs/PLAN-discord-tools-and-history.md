# PLAN: Discord Tool Execution & History Fix

**Date:** 2026-02-16
**Status:** Research complete, implementation pending

---

## Problem Statement

When chatting via Discord, the LLM frequently claims it used a tool (e.g. "I turned off the light")
but the tool was **never actually executed** — no evidence in logs. This works correctly via Web UI.

---

## Root Cause Analysis

### Problem 1: History doesn't contain tool call evidence (CRITICAL)

**Discord `_save_message()`** saves only:
- `user: "turn off the kitchen light"`
- `assistant: "I turned off the kitchen light"`

It does **NOT** save intermediate tool messages:
- `assistant: {functionCall: call_service(light.turn_off, ...)}`
- `tool: {result: "success"}`

On the **next turn**, the LLM sees a pattern in history where it previously "claimed" to use tools
via plain text, without any evidence of actual function calls. After 20-30 exchanges, the LLM
learns from context that it should just respond with text — and stops issuing real `functionCall`
responses entirely. It **hallucinates** tool usage.

**Web UI** has the same storage limitation, but sessions are shorter and users create new sessions
more often, so the pattern doesn't accumulate as aggressively.

**Key code locations:**
- `channels/discord/__init__.py` lines 305-332 (`_process_and_respond`) — saves only user + assistant text
- `channels/discord/__init__.py` lines 375-401 (`_run_stream`) — only captures `TextEvent`, ignores `ToolCallEvent`/`ToolResultEvent`
- `channels/discord/__init__.py` lines 444-451 (`_load_history`) — loads only `{role, content}`, no tool metadata
- `core/query_processor.py` lines 316-684 — tool execution loop works correctly, yields `ToolCallEvent`/`ToolResultEvent` events that Discord ignores

### Problem 2: Too many tools (MEDIUM)

**39 enabled tools** are sent on every Discord call (~3,000-4,500 tokens of JSON schema).
Many are irrelevant for Discord context:
- `create_yaml_integration`, `list_available_integrations`, `read_yaml_config`
- `context7_resolve`, `context7_docs`
- `subagent_spawn`, `subagent_status`
- `get_dashboard_config`, `get_dashboards`

While 39 tools at 128K context is only ~3-4% of budget, fewer tools = better function calling quality.

### Problem 3: `history_limit` is dead config (LOW-MEDIUM)

`discord/defaults.json` has `history_limit: 20` but `_load_history()` ignores it and loads ALL
messages (up to 500 per session). Combined with perpetual Discord sessions (one per user, never
rotated), this means massive history accumulation.

### Problem 4: Tool schemas invisible to compaction (LOW)

`estimate_messages_tokens()` in `core/token_estimator.py` doesn't count tool definition tokens.
The ~3-4.5K tokens of tool schemas are never included in the compaction budget calculation.

---

## Research: How OpenClaw Handles Tools

OpenClaw project at `/Users/anowak/Projects/homeAssistant/openclaw/` was analyzed for reference.

### Key findings:

1. **Tool Profiles** — static presets per use-case:
   - `minimal`: 1 tool (session_status)
   - `coding`: ~15 tools (fs + runtime + sessions + memory)
   - `messaging`: ~6 tools (message + sessions)
   - `full`: ~30 tools (everything)
   Profile selected per session/agent, not per message.

2. **10-layer policy cascade** — tools filtered through:
   profile → global → per-provider → per-agent → per-channel → sandbox → subagent
   Each layer can allow/deny individual tools or groups.

3. **Tool Groups** — logical groupings:
   ```
   group:memory   → [memory_search, memory_get]
   group:web      → [web_search, web_fetch]
   group:fs       → [read, write, edit]
   group:runtime  → [exec, process]
   group:sessions → [sessions_list, sessions_history, ...]
   group:ui       → [browser, canvas]
   ```

4. **Dynamic system prompt** — synchronized with filtered tools.
   When a tool is filtered out, its description section is also removed from the system prompt.
   The LLM never sees instructions for tools it can't use.

5. **Skills ≠ tools** — Skills are markdown instruction files injected into the system prompt.
   LLM reads the skill list, and if one matches, uses `read` tool to load the full SKILL.md.
   This is a **prompt-driven lazy loading** mechanism, not programmatic.

6. **NO per-query routing** — OpenClaw does NOT analyze intent before selecting tools.
   All filtering is configuration-driven (same config = same tools every time).

---

## Proposed Solution

### Phase 1: Fix History (CRITICAL — solves hallucination)

**Goal:** Store tool call/result messages in session history so the LLM sees evidence of real
tool usage on subsequent turns.

**Changes in `channels/discord/__init__.py`:**
1. In `_run_stream()`: capture `ToolCallEvent` and `ToolResultEvent` alongside `TextEvent`
2. In `_process_and_respond()`: save tool call/result messages to storage between user and assistant messages
3. In `_load_history()`: reconstruct tool messages with appropriate roles (`assistant` with function_call metadata, `tool`/`function` with results)

**Expected history after fix:**
```
user: "turn off the kitchen light"
assistant: [function_call: call_service(light.turn_off, entity_id=light.kitchen)]
tool: [result: {"success": true}]
assistant: "I turned off the kitchen light"
```

### Phase 2: Respect `history_limit` (IMPORTANT)

**Changes in `channels/discord/__init__.py`:**
1. `_load_history()` reads `history_limit` from channel config (default: 20)
2. Truncates to last N messages (keeping pairs intact)

### Phase 3: Tool Profiles per Channel (NICE-TO-HAVE)

**Goal:** Reduce tool count for Discord from 39 to ~20-25.

**Approach — Tool Groups + channel deny list:**

Define groups in `tools/base.py` or new `tools/profiles.py`:
```python
TOOL_GROUPS = {
    "ha_control":    ["call_service", "get_entity_state", "get_entities", ...],
    "ha_query":      ["get_history", "get_statistics", "get_weather_data", ...],
    "ha_registry":   ["get_entity_registry", "get_device_registry", "get_area_registry", ...],
    "ha_automation": ["get_automations", "get_scenes", "get_calendar_events"],
    "dashboard":     ["get_dashboards", "get_dashboard_config"],
    "admin":         ["create_yaml_integration", "list_available_integrations", "read_yaml_config"],
    "web":           ["web_search", "web_fetch"],
    "memory":        ["memory_store", "memory_recall", "memory_forget"],
    "discord":       ["check_discord_connection", "send_discord_message", "confirm_discord_pairing", "get_discord_last_target"],
    "identity":      ["identity_set"],
    "scheduler":     ["scheduler"],
    "dev":           ["context7_resolve", "context7_docs", "subagent_spawn", "subagent_status"],
}

CHANNEL_DENY = {
    "discord": ["group:admin", "group:dashboard", "group:dev"],
    "telegram": ["group:admin", "group:dashboard", "group:dev"],
    "panel": [],  # full access
}
```

**Changes needed:**
- `agent_compat.py` `_get_tools_for_provider()` → accept `channel_source` param → filter by deny list
- `build_query_kwargs()` → pass `channel_source` to tool getter
- System prompt builder → exclude tool descriptions for denied tools

### Phase 4: Session Rotation (OPTIONAL)

Auto-create new Discord session after 2h inactivity gap. Prevents unbounded history growth.

---

## RLM Approach Notes (from user research)

The user has been researching **Recursive Language Models (RLM)** from MIT CSAIL — a paradigm
where the LLM treats large text as an external variable and uses a `llm_query` tool to
examine fragments recursively instead of reading everything into context.

### Relevance to our tool problem:
The RLM concept maps to a potential "meta-tool" approach where:
1. LLM gets a lightweight base tool set
2. One special tool (like `llm_query` or `request_skill`) lets the LLM "load" additional
   tool groups on demand
3. The LLM probes what's available, requests what it needs, and operates on chunks

### Why NOT to implement full RLM for tools (for now):
- Our tool set is 39 tools (~3-4K tokens) — well within context limits
- RLM adds latency (extra LLM round-trip to "discover" tools)
- Risk of LLM not requesting the right tool group → worse UX than sending all tools
- Tool Profiles (Phase 3) achieves 80% of the benefit with 0% of the complexity

### When RLM WOULD make sense:
- If tool count grows to 100+ (e.g., per-device tools, plugin ecosystem)
- For very long conversation histories (RLM-style summarization/chunking)
- For RAG context (already partially implemented via compaction)

---

## Implementation Priority

| Phase | What                    | Impact   | Effort | Priority   |
|-------|-------------------------|----------|--------|------------|
| 1     | Fix history (tool calls)| Critical | Medium | DO FIRST   |
| 2     | Respect history_limit   | Medium   | Low    | DO SECOND  |
| 3     | Tool profiles per chan  | Medium   | Medium | NICE-TO-HAVE |
| 4     | Session rotation        | Low      | Low    | OPTIONAL   |

---

## Files to Modify

### Phase 1 (History fix):
- `custom_components/homeclaw/channels/discord/__init__.py` — `_run_stream()`, `_process_and_respond()`, `_load_history()`
- `custom_components/homeclaw/storage.py` — may need new message role support or metadata field for tool calls

### Phase 2 (History limit):
- `custom_components/homeclaw/channels/discord/__init__.py` — `_load_history()`

### Phase 3 (Tool profiles):
- `custom_components/homeclaw/tools/profiles.py` (new file)
- `custom_components/homeclaw/agent_compat.py` — `_get_tools_for_provider()`, `build_query_kwargs()`
- `custom_components/homeclaw/core/query_processor.py` — pass channel_source through

### Phase 4 (Session rotation):
- `custom_components/homeclaw/channels/base.py` — `_get_or_create_session_id()`
