# Dashboard Preview UI — Design Spec

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

1. Backend sends `tool_result` events to frontend during streaming
2. Backend includes `ui_type` metadata in dashboard tool results
3. Frontend renders a `DashboardAction` card when it sees `ui_type: "dashboard_action"`
4. Card shows summary + collapsible YAML + confirm/reject buttons
5. "Confirm" sends a chat message on behalf of the user, triggering `dry_run=false`

## Design Decisions

- **No hardcoded tool name checks in frontend.** Backend declares `ui_type` in `ToolResult.metadata`.
  Frontend maps `ui_type` to a renderer component. Extensible for future tools.
- **Tool result inline in MessageBubble.** Card is part of the assistant message, not a separate
  UI element. Scrolls with chat.
- **Confirm = send chat message.** No new WS endpoints. "Confirm" sends a user message like
  "Tak, zatwierdź dashboard" through the normal chat pipeline. AI sees it and calls the tool
  with `dry_run=false`.

## Backend Changes

### 1. Forward tool_result events to frontend (`ws_handlers/chat.py`)

In `_run_agent_stream()` (line ~444), after persisting tool events, also send them
to the frontend via WebSocket:

```python
elif event_type in ("tool_call", "tool_result"):
    await _persist_tool_messages(storage, session_id, event, timestamp_factory())
    # NEW: Forward to frontend
    if event_type == "tool_result":
        result_data = getattr(event, "tool_result", "")
        # Parse JSON string if needed
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except (json.JSONDecodeError, TypeError):
                pass
        connection.send_message({
            "id": request_id,
            "type": "event",
            "event": {
                "type": "tool_result",
                "name": event.tool_name,
                "result": result_data,
            },
        })
```

This requires passing `connection` and `request_id` to `_run_agent_stream()` or providing
a callback. Recommended: add `on_tool_result: Callable | None = None` callback parameter,
matching the existing `on_text` and `on_status` pattern.

### 2. Add `ui_type` to dashboard tool results (`tools/ha_native.py`)

In all 3 dashboard tools (`CreateDashboard`, `UpdateDashboard`, `DeleteDashboard`),
add `ui_type` and `action` to metadata when returning results:

```python
# In CreateDashboard.execute(), for both dry_run and real execution:
return ToolResult(
    output=json.dumps(result, default=str),
    metadata={**result, "ui_type": "dashboard_action", "action": "create"},
)
```

Same pattern for update (`"action": "update"`) and delete (`"action": "delete"`).

### 3. Include metadata in tool_result event

The `ToolResultEvent` carries `tool_result` (the output string) but not `metadata`.
The `tool_result` field is the JSON string from `ToolResult.output`. The `ui_type` is
in `ToolResult.metadata`. Two options:

**Option A (simpler):** Include `ui_type` and `action` directly in the tool output JSON
(already inside `result` dict before `json.dumps`). Frontend parses `result.ui_type`.

**Option B:** Add `metadata` field to `ToolResultEvent` and forward it separately.

**Chosen: Option A.** The tool output JSON already contains the full result dict.
We add `ui_type` and `action` to the result dict before `json.dumps`:

```python
if dry_run:
    result = {
        "dry_run": True,
        "ui_type": "dashboard_action",
        "action": "create",
        "title": config["title"],
        ...
    }
    return ToolResult(output=json.dumps(result, default=str), metadata=result)
```

For `dry_run=false` (success/error), also include `ui_type` and `action` so the
frontend can update the card status.

## Frontend Changes

### 1. New type: `ToolResultData` (`types/message.ts`)

```typescript
export interface ToolResultData {
  toolName: string;
  result: any;
  status: 'preview' | 'confirmed' | 'success' | 'error';
}
```

Add to `Message` interface:
```typescript
toolResults?: ToolResultData[];
```

### 2. Handle `onToolResult` in `InputArea.svelte`

In the `sendMessageStream()` callbacks, replace the empty stub:

```typescript
onToolResult: (name: string, result: any) => {
  // Check if result has ui_type (rich rendering)
  if (result?.ui_type) {
    appState.update((s) => ({
      ...s,
      messages: s.messages.map((msg) =>
        msg.id === currentAssistantMsgId
          ? {
              ...msg,
              toolResults: [
                ...(msg.toolResults || []),
                { toolName: name, result, status: 'preview' },
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

**Props:**
```typescript
let {
  action,      // 'create' | 'update' | 'delete'
  status,      // 'preview' | 'confirmed' | 'success' | 'error'
  toolResult,  // raw result from backend
  onConfirm,   // () => void
  onReject,    // () => void
} = $props();
```

**States:**

| Status | Rendering |
|--------|-----------|
| `preview` | Full card: summary header + collapsible YAML + Confirm/Reject buttons |
| `confirmed` | Collapsed: "Dashboard 'X' — confirming..." with spinner |
| `success` | Collapsed: "Dashboard 'X' created/updated/deleted ✓" green |
| `error` | Collapsed: "Error: ..." red |

**Summary header** (always visible):
- Icon based on action: create (➕), update (✏️), delete (🗑️)
- Title: "Create/Update/Delete Dashboard: '{title}'"
- Stats: "Views: N · Cards: N · Sidebar: yes/no"

**Collapsible YAML:**
- `<details>` element, open by default in `preview` state
- YAML with syntax highlighting (highlight.js already in project)
- For `update`: two sections — "Current" and "New" config

**Buttons:**
- "Zatwierdź" — green/primary, calls `onConfirm()`
- "Odrzuć" — gray/secondary, calls `onReject()`
- For `delete`: "Zatwierdź" is red (destructive action)

### 4. Render in `MessageBubble.svelte`

After the markdown content, check for `toolResults`:

```svelte
{#if message.toolResults?.length}
  {#each message.toolResults as tr}
    {#if tr.result?.ui_type === 'dashboard_action'}
      <DashboardAction
        action={tr.result.action}
        status={tr.status}
        toolResult={tr.result}
        onConfirm={() => handleDashboardConfirm(tr)}
        onReject={() => handleDashboardReject(tr)}
      />
    {/if}
  {/each}
{/if}
```

**`handleDashboardConfirm`:**
1. Update `tr.status` to `'confirmed'`
2. Send message via `sendMessageFromUI("Tak, zatwierdź dashboard")`

**`handleDashboardReject`:**
1. Update `tr.status` to `'error'` (or a new `'rejected'` status)
2. Send message via `sendMessageFromUI("Nie, odrzuć zmiany")`

### 5. Update card status on subsequent tool_result

When the AI calls the tool with `dry_run=false` and succeeds, a new `tool_result` event
arrives with `ui_type: "dashboard_action"` and `success: true`. The `onToolResult` handler
should find the existing card (matching `action` type) and update its status to `'success'`.

### 6. `sendMessageFromUI` helper

New function in `InputArea.svelte` or `websocket.service.ts` that programmatically sends
a chat message as if the user typed it. Reuses the existing `sendMessageStream()` flow.

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
| `ws_handlers/chat.py` | Forward tool_result events to frontend via WS |
| `tools/ha_native.py` | Add `ui_type`/`action` to dashboard tool result dicts |
| `frontend/src/lib/types/message.ts` | Add `ToolResultData` type, extend `Message` |
| `frontend/src/lib/components/Input/InputArea.svelte` | Handle `onToolResult`, add `sendMessageFromUI` |
| `frontend/src/lib/components/Chat/MessageBubble.svelte` | Render `DashboardAction` for matching tool results |
| `frontend/src/lib/components/Chat/DashboardAction.svelte` | New component — dashboard action card |
| `frontend/src/app.css` | Dashboard action card styles (or scoped in component) |

## Known Limitations

- Card state is in-memory only — refreshing the page loses card status (falls back to
  text-only view from message history). Could persist in future via message metadata.
- "Confirm" message is in Polish ("Tak, zatwierdź dashboard"). Should be configurable
  or use a generic pattern the AI recognizes regardless of language.
- No animation on card state transitions in v1.
