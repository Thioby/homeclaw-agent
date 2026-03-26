# Dashboard Preview UI — Design Spec (v2)

**Status:** approved
**Created:** 2026-03-26

## Problem

Dashboard tools (`create_dashboard`, `update_dashboard`, `delete_dashboard`) with `dry_run=true`
return YAML previews, but the frontend has no way to display them as rich cards. Users see
raw YAML text in the AI response — no visual summary, no confirm/reject buttons.

Additionally, the backend does not forward `tool_result` events to the frontend via WebSocket —
it only persists them to storage. The frontend has `onToolResult` callbacks ready but they
are never triggered.

## Solution

1. Backend forwards `tool_result` events to frontend during streaming (via callback)
2. Dashboard tools include `ui_type` and `action` in tool output JSON
3. Frontend renders a `DashboardAction` card when it sees `ui_type: "dashboard_action"`
4. Card shows summary + collapsible YAML + confirm/reject buttons
5. "Confirm" calls a dedicated WS endpoint that replays the cached config with `dry_run=false`
6. AI is informed of the result via injected history message (no LLM in confirmation path)

## Design Decisions

- **No hardcoded tool name checks in frontend.** Backend includes `ui_type` in tool output JSON.
  Frontend maps `ui_type` to a renderer component. Extensible for future tools.
- **Tool result inline in MessageBubble.** Card is part of the assistant message, not a separate
  UI element. Scrolls with chat.
- **Server-side confirmation cache.** When `dry_run=true` returns, backend caches the full config
  keyed by `tool_call_id`. Frontend sends confirm with `tool_call_id`. Backend replays from cache
  with `dry_run=false`. No LLM involved — faster, cheaper, 100% reliable.
- **Callback pattern for WS forwarding.** `_run_agent_stream` gets `on_tool_result` callback
  matching existing `on_text`/`on_status` pattern. No `connection` passed directly.

## Serialization Path (critical context)

The tool result goes through multiple serialization layers:

1. Tool returns `ToolResult(output=json.dumps(result_dict), metadata=result_dict)`
2. `ToolExecutor` serializes: `result_str = json.dumps(result.to_dict())`
   - `to_dict()` returns `{"output": "<json string>", "metadata": {...}, "success": true, ...}`
3. `ToolResultEvent.tool_result` = the serialized string from step 2

To get `ui_type` to the frontend, we include it directly in the `result_dict` before step 1.
The `on_tool_result` callback must parse through the serialization:
- Parse outer JSON → get `output` field → parse inner JSON → has `ui_type`.

Alternatively (simpler): add `ui_type` and `action` fields to `ToolResultEvent` directly
from `ToolResult.metadata`, and forward those in the WS event alongside the result string.

**Chosen approach:** Include `ui_type`/`action` in the tool output dict (inside `output` JSON).
The `on_tool_result` callback parses the output JSON to extract a clean dict for the frontend.

## Backend Changes

### 1. Forward tool_result events to frontend (`ws_handlers/chat.py`)

Add `on_tool_result: Callable[[str, Any], None] | None = None` parameter to `_run_agent_stream()`,
matching the existing `on_text` and `on_status` callback pattern.

In the event loop (line ~444):

```python
elif event_type in ("tool_call", "tool_result"):
    await _persist_tool_messages(storage, session_id, event, timestamp_factory())
    # Forward tool_result to frontend
    if event_type == "tool_result" and on_tool_result:
        on_tool_result(event.tool_name, getattr(event, "tool_result", ""))
```

In `ws_send_message_stream()`, define the callback closure (like `_send_stream_chunk`):

```python
def _send_tool_result(tool_name: str, raw_result: Any) -> None:
    # Parse through serialization layers to extract clean result
    result_data = raw_result
    if isinstance(result_data, str):
        try:
            parsed = json.loads(result_data)
            # ToolResult.to_dict() wraps in {"output": "...", "metadata": {...}}
            if isinstance(parsed, dict) and "output" in parsed:
                try:
                    result_data = json.loads(parsed["output"])
                except (json.JSONDecodeError, TypeError):
                    result_data = parsed
            else:
                result_data = parsed
        except (json.JSONDecodeError, TypeError):
            pass
    # Only forward results that have ui_type (rich rendering)
    if isinstance(result_data, dict) and result_data.get("ui_type"):
        connection.send_message({
            "id": request_id,
            "type": "event",
            "event": {
                "type": "tool_result",
                "name": tool_name,
                "tool_call_id": ???,  # see below
                "result": result_data,
            },
        })
```

**Note:** `ToolResultEvent` has `tool_call_id` field. The callback needs it for cache correlation.
Update callback signature: `on_tool_result(tool_name, raw_result, tool_call_id)`.

### 2. Add `ui_type` to dashboard tool output JSON (`tools/ha_native.py`)

In all 3 dashboard tools, include `ui_type` and `action` in the result dict **before**
`json.dumps`:

```python
# CreateDashboard — dry_run=true result:
result = await manager.create_dashboard(config, dry_run=dry_run)
result["ui_type"] = "dashboard_action"
result["action"] = "create"
return ToolResult(output=json.dumps(result, default=str), metadata=result)
```

Same for `dry_run=false` results (success/error) — frontend uses them to update card status.

Same pattern for UpdateDashboard (`"action": "update"`) and DeleteDashboard (`"action": "delete"`).

### 3. Server-side confirmation cache

**New module:** `core/pending_actions.py`

```python
"""Cache for pending dashboard actions awaiting user confirmation."""

from __future__ import annotations

import time
from typing import Any

# In-memory cache: tool_call_id → {tool_name, params, timestamp}
_pending: dict[str, dict[str, Any]] = {}
_TTL_SECONDS = 600  # 10 minutes

def store_pending(tool_call_id: str, tool_name: str, params: dict[str, Any]) -> None:
    """Cache a dry_run result for later confirmation."""
    _cleanup_expired()
    _pending[tool_call_id] = {
        "tool_name": tool_name,
        "params": params,
        "timestamp": time.time(),
    }

def pop_pending(tool_call_id: str) -> dict[str, Any] | None:
    """Retrieve and remove a pending action. Returns None if expired or missing."""
    _cleanup_expired()
    return _pending.pop(tool_call_id, None)

def _cleanup_expired() -> None:
    """Remove entries older than TTL."""
    now = time.time()
    expired = [k for k, v in _pending.items() if now - v["timestamp"] > _TTL_SECONDS]
    for k in expired:
        del _pending[k]
```

**Store pending action in tool executor or WS handler:**

When a tool_result arrives with `ui_type: "dashboard_action"` and `dry_run: true`,
cache the original tool call params:

In `_run_agent_stream`, after the `tool_call` event (which has `tool_name` and `tool_args`):

```python
if event_type == "tool_call":
    # Cache params for potential confirmation
    from ..core.pending_actions import store_pending
    store_pending(event.tool_call_id, event.tool_name, event.tool_args)
```

### 4. New WS endpoint: `homeclaw/dashboard/confirm`

**File:** `ws_handlers/chat.py` (or new `ws_handlers/actions.py`)

```python
@websocket_api.websocket_command({
    vol.Required("type"): "homeclaw/dashboard/confirm",
    vol.Required("tool_call_id"): str,
    vol.Required("session_id"): str,
    vol.Optional("confirmed", default=True): bool,  # false = reject
})
@websocket_api.async_response
async def ws_confirm_dashboard(hass, connection, msg):
    """Confirm or reject a pending dashboard action."""
    tool_call_id = msg["tool_call_id"]
    confirmed = msg["confirmed"]

    pending = pop_pending(tool_call_id)
    if not pending:
        connection.send_error(msg["id"], "not_found", "Pending action expired or not found")
        return

    if not confirmed:
        connection.send_result(msg["id"], {"status": "rejected"})
        return

    # Execute the cached action with dry_run=false
    tool_name = pending["tool_name"]
    params = {**pending["params"], "dry_run": False}

    result = await ToolRegistry.execute_tool(tool_name, params, hass=hass, config={})
    result_dict = result.to_dict()

    # Inject into conversation history so AI knows what happened
    storage = _get_storage(hass, connection.user.id)
    session_id = msg["session_id"]
    # Add assistant-style message about the result
    await storage.add_message(session_id, Message(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=f"Dashboard action '{tool_name}' confirmed and executed.",
        timestamp=_now_iso(),
        status="completed",
    ))

    connection.send_result(msg["id"], {
        "status": "success" if result.success else "error",
        "result": json.loads(result.output) if result.output else {},
    })
```

## Frontend Changes

### 1. New type: `ToolResultData` (`types/message.ts`)

```typescript
export interface ToolResultData {
  toolName: string;
  toolCallId: string;
  result: any;
  status: 'preview' | 'confirmed' | 'success' | 'error' | 'rejected';
}
```

Add to `Message` interface:
```typescript
toolResults?: ToolResultData[];
```

### 2. Handle `onToolResult` in `InputArea.svelte`

Replace the empty stub. Note: WS event now includes `tool_call_id`:

```typescript
onToolResult: (name: string, result: any, toolCallId: string) => {
  if (result?.ui_type) {
    appState.update((s) => ({
      ...s,
      messages: s.messages.map((msg) =>
        msg.id === currentAssistantMsgId
          ? {
              ...msg,
              toolResults: [
                ...(msg.toolResults || []),
                { toolName: name, toolCallId, result, status: 'preview' as const },
              ],
            }
          : msg
      ),
    }));
  }
},
```

### 3. New component: `DashboardAction.svelte`

**Location:** `frontend/src/lib/components/Chat/DashboardAction.svelte`

**Props (Svelte 5 runes):**
```typescript
let {
  action,       // 'create' | 'update' | 'delete'
  status,       // 'preview' | 'confirmed' | 'success' | 'error' | 'rejected'
  toolResult,   // raw result from backend
  toolCallId,   // for confirmation WS call
  onStatusChange, // (newStatus: string) => void — updates parent store
} = $props();
```

**States:**

| Status | Rendering |
|--------|-----------|
| `preview` | Full card: summary header + collapsible YAML + Confirm/Reject buttons |
| `confirmed` | Collapsed: "Dashboard 'X' — confirming..." with spinner |
| `success` | Collapsed: "Dashboard 'X' created/updated/deleted ✓" green |
| `error` | Collapsed: "Error: ..." red |
| `rejected` | Collapsed: "Dashboard 'X' — cancelled" gray |

**Summary header** (always visible):
- Icon based on action (CSS, no emojis): create (+), update (pencil), delete (trash)
- Title: "Create/Update/Delete Dashboard: '{title}'"
- Stats: "Views: N · Cards: N · Sidebar: yes/no"

**Collapsible YAML:**
- `<details>` element, open by default in `preview` state
- YAML with syntax highlighting (highlight.js already in project)
- For `update`: two sections — "Current" and "New" config (tabs or stacked)

**Buttons:**
- "Zatwierdź" / "Odrzuć"
- For `delete`: "Zatwierdź" is red (destructive action)

**Confirm handler inside component:**
```typescript
async function handleConfirm() {
  onStatusChange('confirmed');
  try {
    const result = await confirmDashboardAction(toolCallId, sessionId, true);
    onStatusChange(result.status === 'success' ? 'success' : 'error');
  } catch {
    onStatusChange('error');
  }
}
```

### 4. New WS helper: `confirmDashboardAction` (`websocket.service.ts`)

```typescript
export async function confirmDashboardAction(
  toolCallId: string,
  sessionId: string,
  confirmed: boolean
): Promise<{ status: string; result?: any }> {
  return hass.callWS({
    type: 'homeclaw/dashboard/confirm',
    tool_call_id: toolCallId,
    session_id: sessionId,
    confirmed,
  });
}
```

### 5. Render in `MessageBubble.svelte`

After the markdown content, check for `toolResults`. Use callback to update store
(solves Svelte 5 reactivity — parent updates store, not deep mutation):

```svelte
{#if message.toolResults?.length}
  {#each message.toolResults as tr}
    {#if tr.result?.ui_type === 'dashboard_action'}
      <DashboardAction
        action={tr.result.action}
        status={tr.status}
        toolResult={tr.result}
        toolCallId={tr.toolCallId}
        onStatusChange={(newStatus) => updateToolResultStatus(message.id, tr.toolCallId, newStatus)}
      />
    {/if}
  {/each}
{/if}
```

`updateToolResultStatus` is a function prop passed from the parent (`ChatArea`) that
updates `appState` with a new message object (proper Svelte 5 reactivity).

### 6. WebSocket callback signature update

`onToolResult` callback in `websocket.service.ts` needs `toolCallId`:

```typescript
onToolResult?: (name: string, result: any, toolCallId: string) => void;
```

WS event parsing:
```typescript
case 'tool_result':
  callbacks.onToolResult?.(event.name, event.result, event.tool_call_id);
  break;
```

## Styling

- Card background: slightly different from bubble (`--bubble-code-bg` or similar)
- Border: 1px solid with accent color (green for create, blue for update, red for delete)
- Border-radius matching chat bubbles
- YAML block: same styling as code blocks in markdown
- Buttons: consistent with HA button styling
- Responsive: works on mobile (768px breakpoint)
- Dark/light theme support via CSS variables

## Files Changed

| File | Change |
|------|--------|
| `ws_handlers/chat.py` | Add `on_tool_result` callback to `_run_agent_stream`, forward events; new `ws_confirm_dashboard` endpoint |
| `websocket_api.py` | Register new `ws_confirm_dashboard` command |
| `core/pending_actions.py` | New module — in-memory cache for pending confirmations |
| `tools/ha_native.py` | Add `ui_type`/`action` to all dashboard tool result dicts |
| `frontend/src/lib/types/message.ts` | Add `ToolResultData` type, extend `Message` |
| `frontend/src/lib/services/websocket.service.ts` | Update `onToolResult` callback signature, add `confirmDashboardAction`, parse `tool_call_id` |
| `frontend/src/lib/components/Input/InputArea.svelte` | Handle `onToolResult` with `ui_type` check |
| `frontend/src/lib/components/Chat/ChatArea.svelte` | Pass `updateToolResultStatus` callback to MessageBubble |
| `frontend/src/lib/components/Chat/MessageBubble.svelte` | Render `DashboardAction` for matching tool results |
| `frontend/src/lib/components/Chat/DashboardAction.svelte` | New component — dashboard action card |

## Known Limitations

- **Card state is in-memory only.** Refreshing the page loses card state. Messages from history
  show the AI's text response (which includes YAML in markdown). Future improvement: reconstruct
  cards from persisted `tool_result` content_blocks on history load.
- **Pending action cache is in-memory.** HA restart clears it. 10-minute TTL. Acceptable for
  interactive use — user confirms within seconds.
- **No animation** on card state transitions in v1.
