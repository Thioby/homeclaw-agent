# Dashboard Create/Update/Delete Tools — Design Spec

**Status:** approved
**Created:** 2026-03-26

## Problem

Agent has only read-only dashboard tools (`get_dashboards`, `get_dashboard_config`).
`DashboardManager` supports create and update, but these are not exposed as function-calling tools.
Delete is not implemented anywhere. Dashboard creation currently works via a prompt-based
`dashboard_suggestion` JSON hack — not real function calling.

## Solution

Add 3 new CORE tools with `dry_run` confirmation flow:

- `create_dashboard` — create new Lovelace dashboard
- `update_dashboard` — update existing dashboard
- `delete_dashboard` — delete dashboard (new backend method)

All tools default to `dry_run=true`. AI must first call with `dry_run=true` to show a YAML
preview to the user, wait for confirmation, then call again with `dry_run=false` to execute.

Frontend visualization is out of scope — AI presents changes as text/YAML in chat.

## Tool Definitions

All 3 tools use **flat parameters** (not a nested config dict) for consistent LLM usability.

### `create_dashboard`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | string | yes | — | Dashboard title |
| `url_path` | string | yes | — | URL path (e.g. `"security"`) |
| `icon` | string | no | `mdi:view-dashboard` | MDI icon |
| `show_in_sidebar` | bool | no | `true` | Show in HA sidebar |
| `views` | list | yes | — | List of views with cards |
| `dry_run` | bool | no | `true` | Preview without saving |

**dry_run=true:** check if `url_path` already exists (error if so), validate config via
`validate_dashboard_config()`, return YAML preview + warnings.
**dry_run=false:** write YAML file + update `configuration.yaml`, return status + `restart_required: true`.

**Edge case — duplicate url_path:** During both dry_run and real execution, check if
`ui-lovelace-{url_path}.yaml` already exists or if `url_path` is already registered in
`lovelace.dashboards`. Return error: `"Dashboard '{url_path}' already exists"`.

### `update_dashboard`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `dashboard_url` | string | yes | — | URL path of existing dashboard (cannot be empty) |
| `title` | string | no | — | New title |
| `icon` | string | no | — | New MDI icon |
| `show_in_sidebar` | bool | no | — | Show in HA sidebar |
| `views` | list | no | — | New list of views with cards |
| `dry_run` | bool | no | `true` | Preview without saving |

**dry_run=true:** check dashboard exists (error if not), validate new config, return old vs new
config as YAML diff.
**dry_run=false:** overwrite YAML file, return status.

**Edge case — default dashboard:** Reject empty or None `dashboard_url` with error:
`"Cannot modify the default dashboard through this tool"`.

**Note:** `update_dashboard` only updates the YAML file (views/cards). Metadata in
`configuration.yaml` (title, icon) is not updated — this is a known limitation matching
the existing `DashboardManager.update_dashboard()` behavior. Addressing this would require
changes to `_update_configuration_yaml` and is out of scope.

### `delete_dashboard`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `dashboard_url` | string | yes | — | URL path of dashboard to delete (cannot be empty) |
| `dry_run` | bool | no | `true` | Preview without deleting |

**dry_run=true:** check exists, return info about what will be deleted (YAML file path +
`configuration.yaml` entry details).
**dry_run=false:** delete YAML file + remove entry from `configuration.yaml`, return
`restart_required: true`.

**Edge case — not found:** Return `ToolResult(success=False, error="Dashboard '{dashboard_url}' not found")`.
**Edge case — default dashboard:** Reject empty or None `dashboard_url` with error:
`"Cannot delete the default dashboard"`.

## Backend Changes — DashboardManager

### Modified methods

**`create_dashboard(config, dashboard_id, dry_run=True)`**
- `dry_run=True`: check duplicate url_path, validate config, return preview dict (no file write)
- `dry_run=False`: existing behavior (write file + update `configuration.yaml`)

**`update_dashboard(dashboard_id, config, dry_run=True)`**
- `dry_run=True`: read current config from YAML file, validate new config, return both as preview
- `dry_run=False`: existing behavior (overwrite file)

### New methods

**`delete_dashboard(dashboard_id, dry_run=True)`**
1. Locate YAML file — search order: `ui-lovelace-{dashboard_id}.yaml` first, then
   `dashboards/{dashboard_id}.yaml` as fallback (matches existing `update_dashboard` pattern)
2. `dry_run=True`: return `{"exists": true, "file": "<path>", "title": "..."}`
3. `dry_run=False`: delete YAML file + call `_remove_from_configuration_yaml(dashboard_id)`

**`_remove_from_configuration_yaml(url_path)`** — line-based removal algorithm:

```
1. Acquire CONFIG_WRITE_LOCK
2. backup_file(configuration.yaml)
3. Read configuration.yaml lines
4. Find the dashboard entry line: scan for line matching /^\s{4}{url_path}:/ that appears
   after a /^\s{2}dashboards:/ line (which itself appears after /^lovelace:/)
5. If not found → return False
6. Delete the entry line and all following lines at deeper indentation (>4 spaces)
   until hitting a sibling key (4-space indent) or dedent (≤2 spaces) or EOF
7. If dashboards: section is now empty (no children), optionally leave it as-is
8. atomic_write_file(configuration.yaml, new_content)
9. Return True
```

Uses same `CONFIG_WRITE_LOCK`, `backup_file()`, `atomic_write_file()` as `_update_configuration_yaml`.
Implemented as `@staticmethod _do_remove_from_configuration_yaml(config_file, url_path)` run via
`hass.async_add_executor_job()` — same pattern as `_do_update_configuration_yaml`.

### Existing callsite updates

All existing callers must pass `dry_run=False` explicitly to preserve current behavior:

- `services.py` — HA service handlers for `homeclaw.create_dashboard` and `homeclaw.update_dashboard`
- `agent_compat.py` — both `create_dashboard()` (line ~526) and `update_dashboard()` (line ~534)
- `core/agent.py` — `create_dashboard()` method (line ~304)

## Tool Registration — ha_native.py

3 new classes at end of file (after `GetDashboardConfig`):

- `CreateDashboard` — `@ToolRegistry.register`, tier `CORE`, id `create_dashboard`
- `UpdateDashboard` — `@ToolRegistry.register`, tier `CORE`, id `update_dashboard`
- `DeleteDashboard` — `@ToolRegistry.register`, tier `CORE`, id `delete_dashboard`

Each tool:
1. Imports `DashboardManager` from managers
2. Assembles flat params into config dict for Manager call
3. Calls the corresponding method with `dry_run` param
4. On `dry_run=true` — formats result as YAML preview in `ToolResult.output`
5. On `dry_run=false` — returns operation status

## Prompt Changes — prompts.py

Replace existing `dashboard_suggestion` JSON format instruction in **both** `BASE_SYSTEM_PROMPT`
and `SYSTEM_PROMPT_LOCAL` with:

```
DASHBOARD MANAGEMENT:
- ALWAYS use dry_run=true first, show the YAML preview to user
- Wait for user confirmation before calling with dry_run=false
- Available: create_dashboard, update_dashboard, delete_dashboard
```

Remove the old `dashboard_suggestion` response format from both prompts.

## Blocklist Updates

Add `delete_dashboard` to:
- `core/subagent.py` — `DENIED_TOOLS` frozenset
- `proactive/heartbeat.py` — `HEARTBEAT_DENIED_TOOLS` frozenset

(`create_dashboard` and `update_dashboard` are already in both blocklists.)

## Known Limitations

- **Race condition:** Between `dry_run=true` preview and `dry_run=false` execution, dashboard state
  could change. Acceptable for home environment; no staleness detection in v1.
- **update_dashboard metadata:** Only updates YAML file, not `configuration.yaml` metadata
  (title, icon). Matches existing behavior.

## Files Changed

| File | Change |
|------|--------|
| `managers/dashboard_manager.py` | Add `dry_run` to create/update, new `delete_dashboard`, new `_remove_from_configuration_yaml` |
| `tools/ha_native.py` | 3 new tool classes: `CreateDashboard`, `UpdateDashboard`, `DeleteDashboard` |
| `prompts.py` | Replace `dashboard_suggestion` with `DASHBOARD MANAGEMENT` dry_run flow in both prompts |
| `services.py` | Add `dry_run=False` to existing create/update calls |
| `agent_compat.py` | Add `dry_run=False` to both create_dashboard (~L526) and update_dashboard (~L534) calls |
| `core/agent.py` | Add `dry_run=False` to `create_dashboard` call |
| `core/subagent.py` | Add `delete_dashboard` to `DENIED_TOOLS` |
| `proactive/heartbeat.py` | Add `delete_dashboard` to `HEARTBEAT_DENIED_TOOLS` |
| `tests/` | Tests for new tools, delete method, and `_remove_from_configuration_yaml` |
