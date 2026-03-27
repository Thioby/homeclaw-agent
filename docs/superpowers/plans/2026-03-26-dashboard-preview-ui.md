# Dashboard Preview UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render rich dashboard action cards in chat with confirm/reject flow, backed by server-side action cache.

**Architecture:** Backend forwards `tool_result` events to frontend via WS callback, dashboard tools include `ui_type` in output JSON, frontend renders `DashboardAction.svelte` cards inside `MessageBubble`. Confirmation goes through a dedicated WS endpoint that replays cached params — no LLM involvement.

**Tech Stack:** Python 3.12+, Svelte 5, TypeScript, highlight.js, Home Assistant WebSocket API

**Spec:** `docs/superpowers/specs/2026-03-26-dashboard-preview-ui-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `custom_components/homeclaw/core/pending_actions.py` | Create | In-memory cache for pending dashboard confirmations |
| `custom_components/homeclaw/tools/ha_native.py` | Modify | Add `ui_type`/`action` to dashboard tool output dicts |
| `custom_components/homeclaw/ws_handlers/chat.py` | Modify | Add `on_tool_result` callback, cache tool_call params, forward events |
| `custom_components/homeclaw/ws_handlers/actions.py` | Create | New `homeclaw/dashboard/confirm` WS endpoint |
| `custom_components/homeclaw/ws_handlers/__init__.py` | Modify | Import and register new endpoint |
| `frontend/src/lib/types/message.ts` | Modify | Add `ToolResultData`, extend `Message` |
| `frontend/src/lib/services/websocket.service.ts` | Modify | Update callback signature, add `confirmDashboardAction` |
| `frontend/src/lib/components/Input/InputArea.svelte` | Modify | Handle `onToolResult` with `ui_type` check |
| `frontend/src/lib/components/Chat/MessageBubble.svelte` | Modify | Render `DashboardAction` for matching tool results |
| `frontend/src/lib/components/Chat/DashboardAction.svelte` | Create | Dashboard action card component |
| `tests/test_core/test_pending_actions.py` | Create | Tests for pending_actions cache |
| `tests/test_ws_handlers/test_actions.py` | Create | Tests for confirm endpoint |

---

### Task 1: Create pending_actions cache module

**Files:**
- Create: `custom_components/homeclaw/core/pending_actions.py`
- Create: `tests/test_core/test_pending_actions.py`

- [ ] **Step 1: Write tests**

Create `tests/test_core/test_pending_actions.py`:

```python
"""Tests for pending_actions cache."""

from __future__ import annotations

import time

import pytest
from unittest.mock import patch

from custom_components.homeclaw.core.pending_actions import (
    store_pending,
    pop_pending,
    _pending,
)


class TestPendingActions:

    def setup_method(self):
        _pending.clear()

    def test_store_and_pop(self):
        store_pending("call-1", "create_dashboard", {"title": "Test"})
        result = pop_pending("call-1")
        assert result is not None
        assert result["tool_name"] == "create_dashboard"
        assert result["params"] == {"title": "Test"}

    def test_pop_removes_entry(self):
        store_pending("call-1", "create_dashboard", {"title": "Test"})
        pop_pending("call-1")
        assert pop_pending("call-1") is None

    def test_pop_missing_returns_none(self):
        assert pop_pending("nonexistent") is None

    def test_expired_entries_cleaned(self):
        store_pending("old", "create_dashboard", {"title": "Old"})
        # Manually expire
        _pending["old"]["timestamp"] = time.time() - 700
        store_pending("new", "create_dashboard", {"title": "New"})
        assert "old" not in _pending
        assert "new" in _pending

    def test_pop_expired_returns_none(self):
        store_pending("old", "create_dashboard", {"title": "Old"})
        _pending["old"]["timestamp"] = time.time() - 700
        assert pop_pending("old") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_core/test_pending_actions.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement pending_actions module**

Create `custom_components/homeclaw/core/pending_actions.py`:

```python
"""Cache for pending dashboard actions awaiting user confirmation."""

from __future__ import annotations

import time
from typing import Any

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_core/test_pending_actions.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/core/pending_actions.py tests/test_core/test_pending_actions.py
git commit -m "add pending_actions cache for dashboard confirmations"
```

---

### Task 2: Add `ui_type`/`action` to dashboard tool output JSON

**Files:**
- Modify: `custom_components/homeclaw/tools/ha_native.py:1405-1547`

- [ ] **Step 1: Modify CreateDashboard.execute()**

In `ha_native.py`, in `CreateDashboard.execute()` (line ~1419-1426), after getting `result`
from `manager.create_dashboard()`, inject `ui_type` and `action` before returning:

```python
result = await manager.create_dashboard(config, dry_run=dry_run)

if "error" in result:
    return ToolResult(
        output=json.dumps(result), error=result["error"], success=False
    )

result["ui_type"] = "dashboard_action"
result["action"] = "create"
return ToolResult(output=json.dumps(result, default=str), metadata=result)
```

- [ ] **Step 2: Modify UpdateDashboard.execute()**

Same pattern (line ~1489-1498):

```python
result["ui_type"] = "dashboard_action"
result["action"] = "update"
```

- [ ] **Step 3: Modify DeleteDashboard.execute()**

Same pattern (line ~1536-1543):

```python
result["ui_type"] = "dashboard_action"
result["action"] = "delete"
```

- [ ] **Step 4: Run existing tool tests to verify no regression**

Run: `.venv/bin/python -m pytest tests/test_tools/test_dashboard_tools.py -v`
Expected: ALL PASS (tests check `result.success` and JSON parse, `ui_type` is just extra data)

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/tools/ha_native.py
git commit -m "add ui_type and action to dashboard tool results"
```

---

### Task 3: Forward tool_result events to frontend + cache tool_call params

**Files:**
- Modify: `custom_components/homeclaw/ws_handlers/chat.py:400-460,660-710`

- [ ] **Step 1: Add `on_tool_result` callback to `_run_agent_stream`**

Add two new parameters to `_run_agent_stream()` signature (line 400-414):

```python
async def _run_agent_stream(
    hass: HomeAssistant,
    *,
    storage: SessionStorage,
    user_text: str,
    user_id: str,
    session_id: str,
    provider: str,
    model: str | None,
    conversation_history: list[dict[str, Any]],
    attachments: list[Any],
    on_text: Callable[[str], None] | None = None,
    on_status: Callable[[str], None] | None = None,
    on_tool_result: Callable[[str, Any, str], None] | None = None,  # NEW: name, result, tool_call_id
    tool_timestamp_factory: Callable[[], str] | None = None,
    error_log_prefix: str = "AI streaming error",
) -> tuple[str, str | None, list[dict[str, Any]]]:
```

- [ ] **Step 2: Cache tool_call params and forward tool_result events**

In the event loop (line ~444), modify the tool event handling:

```python
elif event_type in ("tool_call", "tool_result"):
    await _persist_tool_messages(
        storage,
        session_id,
        event,
        timestamp_factory(),
    )
    # Cache tool_call params for potential confirmation
    if event_type == "tool_call":
        from ..core.pending_actions import store_pending
        store_pending(event.tool_call_id, event.tool_name, event.tool_args)
    # Forward tool_result to frontend
    if event_type == "tool_result" and on_tool_result:
        on_tool_result(
            event.tool_name,
            getattr(event, "tool_result", ""),
            event.tool_call_id,
        )
```

- [ ] **Step 3: Wire callback in `ws_send_message_stream`**

In `ws_send_message_stream()`, add the callback closure (after `_send_status`, around line 683):

```python
def _send_tool_result(tool_name: str, raw_result: Any, tool_call_id: str) -> None:
    """Forward tool_result to frontend for rich rendering."""
    result_data = raw_result
    if isinstance(result_data, str):
        try:
            parsed = json.loads(result_data)
            # ToolResult.to_dict() wraps: {"output": "<json>", ...}
            if isinstance(parsed, dict) and "output" in parsed:
                try:
                    result_data = json.loads(parsed["output"])
                except (json.JSONDecodeError, TypeError):
                    result_data = parsed
            else:
                result_data = parsed
        except (json.JSONDecodeError, TypeError):
            pass
    # Only forward results with ui_type
    if isinstance(result_data, dict) and result_data.get("ui_type"):
        connection.send_message(
            {
                "id": request_id,
                "type": "event",
                "event": {
                    "type": "tool_result",
                    "name": tool_name,
                    "tool_call_id": tool_call_id,
                    "result": result_data,
                },
            }
        )
```

And pass it to `_run_agent_stream()` call (around line 695):

```python
accumulated_text, stream_error, completion_messages = await _run_agent_stream(
    hass,
    storage=prepared.storage,
    ...
    on_text=_send_stream_chunk,
    on_status=_send_status,
    on_tool_result=_send_tool_result,  # NEW
)
```

- [ ] **Step 4: Run existing tests**

Run: `.venv/bin/python -m pytest tests/test_managers/test_dashboard_manager.py tests/test_tools/test_dashboard_tools.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/ws_handlers/chat.py
git commit -m "forward tool_result events to frontend, cache tool_call params"
```

---

### Task 4: Create WS confirm endpoint

**Files:**
- Create: `custom_components/homeclaw/ws_handlers/actions.py`
- Modify: `custom_components/homeclaw/ws_handlers/__init__.py`

- [ ] **Step 1: Create `ws_handlers/actions.py`**

```python
"""WebSocket handlers for user-confirmed actions."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from ..core.pending_actions import pop_pending
from ..tools.base import ToolRegistry
from ._common import _get_storage, _now_iso, ERR_STORAGE_ERROR
from ..storage import Message

_LOGGER = logging.getLogger(__name__)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/dashboard/confirm",
        vol.Required("tool_call_id"): str,
        vol.Required("session_id"): str,
        vol.Optional("confirmed", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_confirm_dashboard(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Confirm or reject a pending dashboard action."""
    request_id = msg["id"]
    tool_call_id = msg["tool_call_id"]
    confirmed = msg["confirmed"]

    pending = pop_pending(tool_call_id)
    if not pending:
        connection.send_error(
            request_id, "not_found", "Pending action expired or not found"
        )
        return

    if not confirmed:
        connection.send_result(request_id, {"status": "rejected"})
        return

    try:
        tool_name = pending["tool_name"]
        params = {**pending["params"], "dry_run": False}

        result = await ToolRegistry.execute_tool(
            tool_name, params, hass=hass, config={}
        )

        result_output = {}
        if result.output:
            try:
                result_output = json.loads(result.output)
            except (json.JSONDecodeError, TypeError):
                result_output = {"message": result.output}

        # Persist result to conversation history
        user_id = connection.user.id if connection.user else "unknown"
        storage = _get_storage(hass, user_id)
        session_id = msg["session_id"]
        await storage.add_message(
            session_id,
            Message(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=f"Dashboard action confirmed: {result_output.get('message', 'done')}",
                timestamp=_now_iso(),
                status="completed",
            ),
        )

        connection.send_result(
            request_id,
            {
                "status": "success" if result.success else "error",
                "result": result_output,
            },
        )
    except Exception as exc:
        _LOGGER.exception("Error confirming dashboard action: %s", exc)
        connection.send_error(request_id, ERR_STORAGE_ERROR, str(exc))
```

- [ ] **Step 2: Register in `ws_handlers/__init__.py`**

Add import at top of file (with other chat imports):

```python
from .actions import ws_confirm_dashboard
```

Add registration in `async_register_websocket_commands()`:

```python
    # Dashboard actions
    websocket_api.async_register_command(hass, ws_confirm_dashboard)
```

- [ ] **Step 3: Check `_now_iso` is available in `_common.py`**

Read `ws_handlers/_common.py` to verify `_now_iso` is exported. If not, check `chat.py`
for the helper and import from there or duplicate.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/ -k "pending_actions or dashboard" -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/ws_handlers/actions.py custom_components/homeclaw/ws_handlers/__init__.py
git commit -m "add WS endpoint for dashboard action confirmation"
```

---

### Task 5: Frontend — types and WebSocket service updates

**Files:**
- Modify: `frontend/src/lib/types/message.ts`
- Modify: `frontend/src/lib/services/websocket.service.ts`

- [ ] **Step 1: Add `ToolResultData` type to `message.ts`**

Add after `DashboardSuggestion` interface:

```typescript
/**
 * Rich tool result for UI rendering
 */
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

Add to `MessageMetadata` if needed, and export from `index.ts`.

- [ ] **Step 2: Update `onToolResult` callback signature in `websocket.service.ts`**

Change line 67:

```typescript
onToolResult?: (name: string, result: any, toolCallId: string) => void;
```

Update the event case (line 127-128):

```typescript
case 'tool_result':
  callbacks.onToolResult?.(event.name, event.result, event.tool_call_id);
  break;
```

- [ ] **Step 3: Add `confirmDashboardAction` function to `websocket.service.ts`**

Add at the end of the file:

```typescript
/**
 * Confirm or reject a pending dashboard action.
 */
export async function confirmDashboardAction(
  hass: HomeAssistant,
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

- [ ] **Step 4: Commit**

```bash
cd custom_components/homeclaw/frontend
git add src/lib/types/message.ts src/lib/services/websocket.service.ts
git commit -m "add tool result types and confirm WS helper"
```

---

### Task 6: Frontend — handle `onToolResult` in InputArea

**Files:**
- Modify: `frontend/src/lib/components/Input/InputArea.svelte:211-212`

- [ ] **Step 1: Replace empty `onToolResult` stub**

Replace lines 211-212:

```typescript
onToolCall: (_name: string, _args: any) => {},
onToolResult: (_name: string, _result: any) => {},
```

With:

```typescript
onToolCall: (_name: string, _args: any) => {},
onToolResult: (name: string, result: any, toolCallId: string) => {
  if (result?.ui_type) {
    appState.update((s) => ({
      ...s,
      messages: s.messages.map((msg) =>
        msg.id === assistantMessageId
          ? {
              ...msg,
              toolResults: [
                ...(msg.toolResults || []),
                {
                  toolName: name,
                  toolCallId,
                  result,
                  status: 'preview' as const,
                },
              ],
            }
          : msg
      ),
    }));
  }
},
```

- [ ] **Step 2: Verify `assistantMessageId` is in scope**

Check that `assistantMessageId` (created during `onStart`) is accessible in the
`onToolResult` closure. It's declared in the same `sendMessageStream` block scope,
so it should be available.

- [ ] **Step 3: Build frontend to check for TS errors**

Run: `cd custom_components/homeclaw/frontend && npm run check`

- [ ] **Step 4: Commit**

```bash
git add src/lib/components/Input/InputArea.svelte
git commit -m "handle tool_result events for rich UI rendering"
```

---

### Task 7: Frontend — DashboardAction.svelte component

**Files:**
- Create: `frontend/src/lib/components/Chat/DashboardAction.svelte`

- [ ] **Step 1: Create the component**

Create `frontend/src/lib/components/Chat/DashboardAction.svelte`:

```svelte
<script lang="ts">
  import { get } from 'svelte/store';
  import { sessionState } from '$lib/stores/sessions';
  import { confirmDashboardAction } from '$lib/services/websocket.service';

  let {
    action,
    status = 'preview',
    toolResult,
    toolCallId,
    hass,
    onStatusChange,
  }: {
    action: 'create' | 'update' | 'delete';
    status: 'preview' | 'confirmed' | 'success' | 'error' | 'rejected';
    toolResult: any;
    toolCallId: string;
    hass: any;
    onStatusChange: (newStatus: string) => void;
  } = $props();

  const title = $derived(toolResult?.title || toolResult?.dashboard_url || 'Dashboard');
  const viewCount = $derived(toolResult?.preview
    ? (toolResult.preview.match(/^  - title:/gm) || []).length
    : (toolResult?.views?.length || 0));

  const actionLabels: Record<string, string> = {
    create: 'Create Dashboard',
    update: 'Update Dashboard',
    delete: 'Delete Dashboard',
  };

  const actionIcons: Record<string, string> = {
    create: '+',
    update: '✎',
    delete: '✕',
  };

  const statusMessages: Record<string, string> = {
    confirmed: 'Confirming...',
    success: action === 'delete' ? 'Deleted' : action === 'update' ? 'Updated' : 'Created',
    error: 'Error',
    rejected: 'Cancelled',
  };

  async function handleConfirm() {
    onStatusChange('confirmed');
    try {
      const sessionId = get(sessionState).activeSessionId || '';
      const res = await confirmDashboardAction(hass, toolCallId, sessionId, true);
      onStatusChange(res.status === 'success' ? 'success' : 'error');
    } catch (e) {
      console.error('Dashboard confirm failed:', e);
      onStatusChange('error');
    }
  }

  function handleReject() {
    const sessionId = get(sessionState).activeSessionId || '';
    confirmDashboardAction(hass, toolCallId, sessionId, false).catch(() => {});
    onStatusChange('rejected');
  }
</script>

<div class="dashboard-action" class:delete={action === 'delete'} class:collapsed={status !== 'preview'}>
  <div class="da-header">
    <span class="da-icon">{actionIcons[action]}</span>
    <span class="da-title">{actionLabels[action]}: "{title}"</span>
    {#if status !== 'preview'}
      <span class="da-status" class:success={status === 'success'} class:error={status === 'error'}>
        {statusMessages[status] || status}
        {#if status === 'success'}✓{/if}
        {#if status === 'confirmed'}<span class="da-spinner"></span>{/if}
      </span>
    {/if}
  </div>

  {#if status === 'preview'}
    {#if viewCount > 0}
      <div class="da-stats">Views: {viewCount}</div>
    {/if}

    {#if toolResult?.preview || toolResult?.new_config}
      <details open>
        <summary>Show YAML preview</summary>
        <div class="da-yaml">
          {#if action === 'update' && toolResult?.current_config}
            <div class="da-yaml-label">Current:</div>
            <pre><code>{toolResult.current_config}</code></pre>
            <div class="da-yaml-label">New:</div>
          {/if}
          <pre><code>{toolResult.preview || toolResult.new_config}</code></pre>
        </div>
      </details>
    {/if}

    <div class="da-buttons">
      <button class="da-btn da-btn-confirm" class:da-btn-danger={action === 'delete'} onclick={handleConfirm}>
        Zatwierdź
      </button>
      <button class="da-btn da-btn-reject" onclick={handleReject}>
        Odrzuć
      </button>
    </div>
  {/if}
</div>

<style>
  .dashboard-action {
    margin-top: 8px;
    border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--bubble-code-bg, rgba(0, 0, 0, 0.04));
    font-size: 13px;
  }
  .dashboard-action.delete {
    border-color: rgba(244, 67, 54, 0.4);
  }
  .dashboard-action.collapsed {
    padding: 8px 12px;
  }
  .da-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
  }
  .da-icon {
    font-size: 14px;
    opacity: 0.7;
  }
  .da-title {
    flex: 1;
  }
  .da-status {
    font-size: 12px;
    opacity: 0.8;
  }
  .da-status.success {
    color: #4caf50;
  }
  .da-status.error {
    color: #f44336;
  }
  .da-stats {
    margin-top: 4px;
    font-size: 12px;
    opacity: 0.7;
  }
  details {
    margin-top: 8px;
  }
  summary {
    cursor: pointer;
    font-size: 12px;
    opacity: 0.7;
    user-select: none;
  }
  .da-yaml {
    margin-top: 6px;
    max-height: 300px;
    overflow-y: auto;
  }
  .da-yaml pre {
    margin: 0;
    padding: 8px;
    background: var(--bubble-code-bg, rgba(0, 0, 0, 0.06));
    border-radius: 4px;
    font-size: 12px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .da-yaml-label {
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
    margin-bottom: 2px;
    opacity: 0.6;
  }
  .da-buttons {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }
  .da-btn {
    padding: 6px 16px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    font-weight: 500;
  }
  .da-btn-confirm {
    background: #4caf50;
    color: white;
  }
  .da-btn-confirm:hover {
    background: #43a047;
  }
  .da-btn-danger {
    background: #f44336;
  }
  .da-btn-danger:hover {
    background: #e53935;
  }
  .da-btn-reject {
    background: var(--divider-color, rgba(0, 0, 0, 0.08));
    color: var(--primary-text-color, #333);
  }
  .da-btn-reject:hover {
    background: rgba(0, 0, 0, 0.15);
  }
  .da-spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: da-spin 0.6s linear infinite;
    vertical-align: middle;
    margin-left: 4px;
  }
  @keyframes da-spin {
    to { transform: rotate(360deg); }
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/lib/components/Chat/DashboardAction.svelte
git commit -m "add DashboardAction card component"
```

---

### Task 8: Frontend — render DashboardAction in MessageBubble

**Files:**
- Modify: `frontend/src/lib/components/Chat/MessageBubble.svelte`
- Modify: `frontend/src/lib/components/Chat/ChatArea.svelte`

- [ ] **Step 1: Add props and import to MessageBubble**

In `MessageBubble.svelte`, add import and update props (lines 1-8):

```svelte
<script lang="ts">
  import type { Message } from '$lib/types';
  import { get } from 'svelte/store';
  import { renderMarkdown } from '$lib/services/markdown.service';
  import { sessionState } from '$lib/stores/sessions';
  import { appState } from '$lib/stores/appState';
  import DashboardAction from './DashboardAction.svelte';

  let { message, hass }: { message: Message; hass: any } = $props();
```

- [ ] **Step 2: Add status change handler**

Add a function to update tool result status via store (proper Svelte 5 reactivity):

```typescript
function updateToolResultStatus(toolCallId: string, newStatus: string) {
  appState.update((s) => ({
    ...s,
    messages: s.messages.map((msg) =>
      msg.id === message.id
        ? {
            ...msg,
            toolResults: (msg.toolResults || []).map((tr) =>
              tr.toolCallId === toolCallId ? { ...tr, status: newStatus as any } : tr
            ),
          }
        : msg
    ),
  }));
}
```

- [ ] **Step 3: Add DashboardAction rendering in template**

After the streaming cursor (line ~117), before the timestamp, add:

```svelte
    {#if message.isStreaming}
      <span class="streaming-cursor">&#9611;</span>
    {/if}

    {#if message.toolResults?.length}
      {#each message.toolResults as tr (tr.toolCallId)}
        {#if tr.result?.ui_type === 'dashboard_action'}
          <DashboardAction
            action={tr.result.action}
            status={tr.status}
            toolResult={tr.result}
            toolCallId={tr.toolCallId}
            {hass}
            onStatusChange={(s) => updateToolResultStatus(tr.toolCallId, s)}
          />
        {/if}
      {/each}
    {/if}

    {#if formattedTime}
```

- [ ] **Step 4: Pass `hass` from ChatArea to MessageBubble**

In `ChatArea.svelte`, the `hass` prop needs to reach `MessageBubble`. Add prop:

```svelte
<script lang="ts">
  ...
  let { hass }: { hass: any } = $props();
</script>
```

Update the message rendering:

```svelte
<MessageBubble {message} {hass} />
```

Then check where `ChatArea` is used (likely `HomeclawPanel.svelte`) and pass `hass` there too.

- [ ] **Step 5: Build and check**

Run: `cd custom_components/homeclaw/frontend && npm run check && npm run build`

- [ ] **Step 6: Commit**

```bash
git add src/lib/components/Chat/MessageBubble.svelte src/lib/components/Chat/ChatArea.svelte src/lib/components/Chat/DashboardAction.svelte
git commit -m "render DashboardAction cards in chat messages"
```

---

### Task 9: Build frontend and final verification

- [ ] **Step 1: Build frontend**

Run: `cd custom_components/homeclaw/frontend && npm run build`
Expected: Build succeeds with homeclaw-panel.js output.

- [ ] **Step 2: Run all Python tests**

Run: `.venv/bin/python -m pytest tests/test_core/test_pending_actions.py tests/test_managers/test_dashboard_manager.py tests/test_tools/test_dashboard_tools.py -v`
Expected: ALL PASS

- [ ] **Step 3: Run linting**

Run: `.venv/bin/python -m black --check custom_components/homeclaw/core/pending_actions.py custom_components/homeclaw/ws_handlers/actions.py custom_components/homeclaw/ws_handlers/chat.py custom_components/homeclaw/tools/ha_native.py && .venv/bin/python -m isort --check custom_components/homeclaw/core/pending_actions.py custom_components/homeclaw/ws_handlers/actions.py`

Fix any issues, commit if needed.

- [ ] **Step 4: Commit build output**

```bash
git add custom_components/homeclaw/frontend/homeclaw-panel.js custom_components/homeclaw/frontend/homeclaw-panel.css
git commit -m "build frontend with dashboard action cards"
```
