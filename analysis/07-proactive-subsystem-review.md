# Code Review: Homeclaw Proactive Subsystem

**Date:** 2026-02-10
**Reviewer:** Gemini CLI
**Scope:** Proactive Subsystem (Heartbeat, Scheduler, Subagents) and Core Integration

## Executive Summary

The new proactive subsystem introduces powerful capabilities (heartbeat monitoring, scheduled tasks, background subagents). However, the implementation contains **Critical** security and concurrency flaws that must be addressed before deployment. The most severe issues allow "read-only" agents to perform state-changing actions and allow concurrent users to corrupt each other's session context.

## Critical Issues (Must Fix)

### 1. Unrestricted Tool Access in Subagents & Heartbeat (Security)
**Severity:** Critical
**Files:** `core/subagent.py`, `proactive/heartbeat.py`

**Description:**
The documentation and docstrings state that Subagents and Heartbeat have "read-only" access and a reduced toolset. However, the implementation simply calls `agent.process_query()` without any mechanism to enforce these restrictions. The `DENIED_TOOLS` list in `subagent.py` is defined but never used.

**Impact:**
- A subagent (prompted by a user) can use *any* tool, including `call_service`, `create_automation`, or `subagent_spawn`.
- A malicious prompt could cause a subagent recursion bomb (fork bomb) by having a subagent spawn more subagents.
- The Heartbeat agent could hallucinate and decide to "fix" a problem by turning off devices, unlocking doors, etc.

**Fix:**
Modify `Agent.process_query` and `QueryProcessor.process` to accept an `allowed_tools` or `denied_tools` argument. Pass this argument from `SubagentManager` and `HeartbeatService`.

```python
# In custom_components/homeclaw/core/agent.py
async def process_query(self, query: str, allowed_tools: list[str] | None = None, ...):
    # ... pass to QueryProcessor ...

# In custom_components/homeclaw/core/query_processor.py
# Filter the tools list sent to the provider based on allowed_tools
```

### 2. Global State Race Condition for User Context (Concurrency)
**Severity:** Critical
**Files:** `ws_handlers/chat.py`, `tools/scheduler.py`, `tools/subagent.py`

**Description:**
The system uses a global variable `hass.data[DOMAIN]["_current_user_id"]` to pass the user ID from the WebSocket handler to the Tool execution logic. Since `ws_send_message` is async and awaits LLM responses, concurrent requests will overwrite this global variable.

**Impact:**
- **Cross-user data leakage:** If User A and User B chat simultaneously, User A's tool calls might execute with User B's ID.
- **Incorrect ownership:** Scheduled jobs or subagents may be created under the wrong user ID.

**Fix:**
Remove `_current_user_id`. Pass `user_id` explicitly through the call stack:
1.  `ws_handlers/chat.py` passes `user_id` to `agent.process_query`.
2.  `agent.process_query` passes it to `QueryProcessor`.
3.  `QueryProcessor` passes it to `ToolExecutor`.
4.  `ToolExecutor` passes it to the `Tool.execute` method (requires updating `Tool` base class signature or `kwargs`).

## High Priority Issues

### 3. Blocking I/O in Event Loop
**Severity:** High
**File:** `proactive/heartbeat.py` (Line ~227)

**Description:**
`_build_entity_snapshot` iterates over `hass.states.async_all(domain)` and builds a large string inside the asyncio event loop. While capped at `MAX_ENTITIES_IN_SNAPSHOT`, this is synchronous CPU work that could block the loop on lower-end hardware (RPi).

**Fix:**
Run the snapshot construction in a thread executor:
```python
snapshot = await self._hass.async_add_executor_job(self._build_entity_snapshot)
```

### 4. Missing Error Handling for "at" Scheduling
**Severity:** Medium
**File:** `proactive/scheduler.py`

**Description:**
In `_register_job_timer` for `schedule_type="at"`, if the time has passed, it logs a debug message and skips. However, if the system was down during the scheduled time, the job is effectively lost/stuck in "pending" forever.

**Fix:**
Implement "missed job" logic on startup. If a job's `run_at` is in the past (within a reasonable window, e.g., 1 hour), execute it immediately or mark it as "missed" depending on policy.

## Medium/Low Issues

### 5. Prompt Security Fallacy
**Severity:** Medium
**File:** `prompts.py`

**Description:**
`SUBAGENT_SYSTEM_PROMPT` relies on telling the LLM "You have read-only access...". This is "security by prompting" and is ineffective against jailbreaks or strong hallucinations. It must be paired with the technical fix in Issue #1.

### 6. Code Style / Type Hinting
**Severity:** Low
**File:** `proactive/scheduler.py`

**Description:**
`interval_seconds` is typed as `int | None`, but used in `timedelta(seconds=job.interval_seconds)` where `None` would raise a TypeError. The code guards against this with `if job.schedule_type == "interval" and job.interval_seconds:`, but explicit type narrowing or a default of 0 would be cleaner.

## Recommendations

1.  **Refactor Context Passing:** Immediately remove the global `_current_user_id` hack. Refactor the `Tool` interface to accept a `context` dictionary containing `user_id`, `session_id`, etc.
2.  **Enforce Tool Restrictions:** Implement strict allow-listing for tools at the `QueryProcessor` level.
3.  **Add Tests:** Add concurrency tests that simulate two users sending messages simultaneously to verify context isolation.

## Conclusion

The architecture is sound, but the implementation has two fatal flaws (Security #1, Concurrency #2) that make it unsafe for production use. These must be fixed before merging.
