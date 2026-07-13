# create_automation tool — design

Date: 2026-07-13
Status: approved for implementation (autonomous run, user-delegated)

## Problem

The system prompt (`prompts.py:15,81,263`) advertises a `create_automation(automation)`
tool, but no tool with that id is registered in `ToolRegistry`. The model calls it,
gets nothing, and tells the user "I can't create automations."

Worse: `AutomationManager.create_automation` is a stub — it generates an id and calls
`automation.reload`, but never persists the config anywhere. Even the
`homeclaw.create_automation` HA service silently does nothing.

## Hard requirement

**Never corrupt the Home Assistant configuration.** The live instance
(192.168.1.109, HA 2026.7.2) has `automation: !include automations.yaml` and a
107-line `automations.yaml` (fetched as `tests/fixtures/live_automations.yaml`).

## Approaches considered

**A. Append to `automations.yaml` in-process, reusing `utils/yaml_writer`** — chosen.
Mirrors what HA's own UI config API does (rewrite automations.yaml + reload), but
safer: append-only preserves existing file bytes and comments verbatim.

**B. Import HA's internal `config` component write path**
(`homeassistant.components.config.automation`). Version-fragile private API, needs the
`config` integration's HTTP views. Rejected.

**C. Call the REST/WS config API.** Requires an auth token from inside the process
that already has direct `hass` access. Rejected.

## Design

### 1. `AutomationManager.create_automation(config, *, dry_run=False)` — real implementation

Flow:

1. **Validate** via extended `validate_automation` (see §3). Invalid → error, no I/O.
2. **Preconditions**:
   - `hass.services.has_service("automation", "reload")` — if the automation
     integration is not loaded, writing the file would do nothing; abort.
   - `configuration.yaml` must map `automation` to `!include automations.yaml`
     (split configs like `!include_dir_merge_list automations/` would silently
     ignore our file — abort with a clear "unsupported layout" error instead).
3. **Load** `hass.config.path("automations.yaml")` — resolved through
   `os.path.realpath` so a symlinked file is edited in place and the symlink
   survives — in an executor job, parsed with the same HA-tag-aware SafeLoader
   as `safe_load_yaml` but accepting a **top-level list**.
   - Unparseable file → abort, never touch it.
   - Top-level parses but is not a list → abort (unexpected shape).
   - Missing or empty file → treat as empty list.
4. **Id**: generate `uuid4` hex if absent; duplicate id in existing list → error.
5. **`dry_run=True`** → return `{dry_run, preview (YAML), validation, id}`; zero writes.
6. **Write** under `CONFIG_WRITE_LOCK`:
   - `backup_file(path)` → `automations.yaml.backup`
   - Build new content **append-only**: existing raw text (with trailing newline
     ensured) + `yaml.dump([new_item], sort_keys=False, allow_unicode=True,
     default_flow_style=False)`. Existing bytes/comments stay byte-identical.
     Special cases: empty/missing file → new content is just the dumped item;
     file containing literal `[]`/`null` as sole content → replace with dumped item.
   - **Pre-write round-trip check**: parse the complete new content with the same
     loader; it must be a list of length n+1. Fails → abort, file untouched.
   - `atomic_write_file` (temp + fsync + replace, permissions preserved).
7. **Reload**: `automation.reload`. Reload failure → report in result; the file on
   disk is already verified-parseable, so HA state stays consistent.

### 2. `CreateAutomation` tool in `tools/ha_native.py`

- `id = "create_automation"`, `requires_confirmation = True` (generic suspend/resume
  approval gate in `ToolExecutor` picks this up on the panel path).
- `category = HOME_ASSISTANT`, `tier = CORE`.
- Parameters: `automation` (object, required — full HA automation config:
  alias, triggers, conditions, actions, mode…), `dry_run` (boolean, default true —
  same contract as `create_dashboard`).
- Delegates to `AutomationManager.create_automation(automation, dry_run=...)`.

### 3. `validate_automation` — accept both key formats

Live HA 2026.7 writes the modern format (`triggers:`/`conditions:`/`actions:` with
inner `trigger:`/`action:` keys); the legacy singular format (`trigger:`/`action:`,
inner `platform:`/`service:`) is still valid. Current validator only accepts legacy —
it would reject exactly what HA itself writes. Extended rules:

- `use_blueprint` present → structural trigger/action rules are skipped
  (blueprint automations carry neither; the live fixture contains such entries)
- otherwise: exactly one of `trigger`/`triggers` present and non-empty (dict or
  list; inner keys not inspected — HA accepts both `platform:` and `trigger:`)
- and exactly one of `action`/`actions` present and non-empty
- each action entry (dict) must carry one of `service`, `action`, or another
  recognized action key (`delay`, `wait_template`, `wait_for_trigger`, `choose`,
  `if`, `repeat`, `parallel`, `sequence`, `stop`, `event`, `scene`, `device_id`,
  `variables`, `set_conversation_response`)
- top-level must be a dict; `id` if present must be a string/number

### 4. Call-path compatibility

- `core/agent.py: create_automation` gains a pass-through `dry_run` keyword
  (default `False` — the `homeclaw.create_automation` HA service keeps its
  "create immediately" semantics).
- The tool calls with `dry_run` defaulting to `True`, so the LLM path always
  previews first and real execution happens after user approval
  (`requires_confirmation` gate) with `dry_run=false`.
- `core/subagent.py` and `proactive/heartbeat.py` already list
  `create_automation` in their blocked-tool sets — correct once the tool exists.
- `prompts.py` already advertises the tool; only the description of the
  dry_run/confirm contract gets aligned with the dashboard wording.

## Safety guarantees (mapping to the hard requirement)

| Risk | Mitigation |
|------|-----------|
| Partial/corrupt write | `atomic_write_file` (temp + fsync + rename) |
| Losing existing automations | append-only: existing bytes never re-serialized |
| Concurrent writers | `CONFIG_WRITE_LOCK` |
| Writing into a broken file | parse-before-touch; unparseable → abort |
| Producing a broken file | round-trip parse of full new content before write |
| No rollback path | `.backup` copy before every write |
| `configuration.yaml` damage | never touched (include already present) |
| Model creating without consent | `requires_confirmation` + dry_run-first contract |

## Testing

Unit tests (`tests/test_managers/test_automation_manager.py` extension + tool test):

- fixture = **real production `automations.yaml`** (`tests/fixtures/live_automations.yaml`)
- create appends: existing content byte-identical prefix, new item parses, count n+1
- dry_run: zero filesystem writes, preview parses
- duplicate id rejected; generated id returned
- unparseable existing file → error, file untouched, no backup clobber
- missing file / empty file / literal `[]` file
- validation: modern format accepted, legacy accepted, missing triggers/actions rejected
- reload service missing → error before any write
- configuration.yaml without `!include automations.yaml` → error before any write
- blueprint automation (`use_blueprint`, no triggers/actions) validates and writes
- symlinked automations.yaml: target updated, symlink preserved
- concurrent create_automation calls: both land, file stays parseable
- backup created on real write
- tool: registered in ToolRegistry, `requires_confirmation` is True, dry_run default true

Full suite (`pytest`) must stay green.
