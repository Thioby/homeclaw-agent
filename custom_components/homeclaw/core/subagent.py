"""Subagent manager for Homeclaw.

Allows the main agent to delegate complex tasks to isolated background
workers.  Inspired by PicoClaw's ``SubagentManager.Spawn()`` and
OpenClaw's ``sessions_spawn`` tool.

Subagents:
- Run in ``asyncio.create_task`` with independent context.
- Have a reduced tool set (no scheduler, no spawn, read-only HA).
- Use a minimal system prompt (no identity, no memory recall).
- Cannot spawn further subagents (no recursion).
- Have a concurrency limit per user.
- Time out after ``TIMEOUT_SECONDS``.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Limits ---
MAX_CONCURRENT_PER_USER = 2
MAX_ITERATIONS = 5
TIMEOUT_SECONDS = 120
MAX_TASK_HISTORY = 50

# --- Events ---
EVENT_SUBAGENT_COMPLETE = f"{DOMAIN}_subagent_complete"
EVENT_SUBAGENT_STARTED = f"{DOMAIN}_subagent_started"

# Tools that subagents are NOT allowed to use
DENIED_TOOLS = frozenset(
    {
        "scheduler",
        "subagent_spawn",
        "subagent_status",
        "memory_store",
        "memory_forget",
        "identity_set",
        "create_automation",
        "create_dashboard",
        "update_dashboard",
        "call_service",
        "set_entity_state",
        "safe_shell_execute",
    }
)


@dataclass
class SubagentTask:
    """Represents a single subagent task."""

    task_id: str
    label: str
    prompt: str
    status: str = (
        "pending"  # "pending" | "running" | "completed" | "failed" | "cancelled"
    )
    result: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    parent_session_id: str = ""
    user_id: str = ""
    provider: str | None = None
    duration_ms: int = 0


class SubagentManager:
    """Manages subagent tasks — isolated background AI workers.

    Usage:
        manager = SubagentManager(hass)
        task_id = await manager.spawn("Analyze energy usage", "energy_check", user_id="abc")
        # Later...
        task = manager.get_task(task_id)
        if task and task.status == "completed":
            print(task.result)
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._tasks: dict[str, SubagentTask] = {}
        self._running_asyncio_tasks: dict[str, asyncio.Task[None]] = {}
        self._completed_history: list[dict[str, Any]] = []

    async def spawn(
        self,
        prompt: str,
        label: str = "background task",
        *,
        user_id: str = "",
        session_id: str = "",
        provider: str | None = None,
    ) -> str:
        """Spawn a new subagent task.

        Args:
            prompt: Detailed task description for the subagent.
            label: Short human-readable label.
            user_id: Owner user ID.
            session_id: Parent session for context.
            provider: AI provider to use (None for default).

        Returns:
            Task ID string.

        Raises:
            RuntimeError: If concurrency limit reached.
        """
        # Check concurrency limit
        active_for_user = sum(
            1
            for t in self._tasks.values()
            if t.user_id == user_id and t.status in ("pending", "running")
        )
        if active_for_user >= MAX_CONCURRENT_PER_USER:
            raise RuntimeError(
                f"Maximum concurrent subagents reached ({MAX_CONCURRENT_PER_USER}). "
                "Wait for existing tasks to complete."
            )

        task_id = str(uuid.uuid4())[:8]
        task = SubagentTask(
            task_id=task_id,
            label=label,
            prompt=prompt,
            status="pending",
            user_id=user_id,
            parent_session_id=session_id,
            provider=provider,
        )
        self._tasks[task_id] = task

        # Fire started event
        self._hass.bus.async_fire(
            EVENT_SUBAGENT_STARTED,
            {
                "task_id": task_id,
                "label": label,
                "user_id": user_id,
            },
        )

        # Launch in background
        asyncio_task = asyncio.create_task(
            self._run_subagent(task),
            name=f"homeclaw_subagent_{task_id}",
        )
        self._running_asyncio_tasks[task_id] = asyncio_task

        _LOGGER.info("Subagent spawned: '%s' (id=%s, user=%s)", label, task_id, user_id)
        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running subagent task.

        Args:
            task_id: Task to cancel.

        Returns:
            True if cancelled, False if not found or already done.
        """
        task = self._tasks.get(task_id)
        if not task or task.status not in ("pending", "running"):
            return False

        asyncio_task = self._running_asyncio_tasks.get(task_id)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()

        task.status = "cancelled"
        task.completed_at = time.time()
        self._move_to_history(task)

        _LOGGER.info("Subagent cancelled: %s", task_id)
        return True

    def get_task(self, task_id: str) -> SubagentTask | None:
        """Get a task by ID (active or from history)."""
        task = self._tasks.get(task_id)
        if task:
            return task

        # Check history
        for record in self._completed_history:
            if record.get("task_id") == task_id:
                return SubagentTask(
                    **{
                        k: v
                        for k, v in record.items()
                        if k in SubagentTask.__dataclass_fields__
                    }
                )
        return None

    def list_tasks(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List all active tasks, optionally filtered by user.

        Args:
            user_id: Filter by user (None for all).

        Returns:
            List of task dictionaries.
        """
        tasks = list(self._tasks.values())
        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]
        return [asdict(t) for t in tasks]

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return completed task history."""
        return self._completed_history[-limit:]

    # === Internal ===

    async def _run_subagent(self, task: SubagentTask) -> None:
        """Execute the subagent in an isolated context."""
        task.status = "running"
        start_time = time.monotonic()

        try:
            # Get agent
            agent = self._get_agent(task.provider)
            if not agent:
                task.status = "failed"
                task.error = "No AI agent available"
                return

            # Build subagent prompt with restricted tools
            from ..prompts import SUBAGENT_SYSTEM_PROMPT

            # Use the agent's process_query with isolated context and denied tools
            result = await asyncio.wait_for(
                agent.process_query(
                    user_query=task.prompt,
                    conversation_history=[],  # Clean — no history carry-over
                    denied_tools=DENIED_TOOLS,
                    system_prompt=SUBAGENT_SYSTEM_PROMPT,
                ),
                timeout=TIMEOUT_SECONDS,
            )

            task.result = result.get("answer", "") or result.get("response", "")
            task.status = "completed" if result.get("success") else "failed"
            if not result.get("success"):
                task.error = result.get("error", "Unknown error")

        except asyncio.TimeoutError:
            task.status = "failed"
            task.error = f"Timed out after {TIMEOUT_SECONDS}s"
            _LOGGER.warning("Subagent '%s' timed out", task.label)

        except asyncio.CancelledError:
            task.status = "cancelled"
            _LOGGER.info("Subagent '%s' was cancelled", task.label)

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            _LOGGER.error("Subagent '%s' failed: %s", task.label, e)

        finally:
            task.completed_at = time.time()
            task.duration_ms = int((time.monotonic() - start_time) * 1000)

            # Clean up asyncio task ref
            self._running_asyncio_tasks.pop(task.task_id, None)

            # Fire completion event
            self._hass.bus.async_fire(
                EVENT_SUBAGENT_COMPLETE,
                {
                    "task_id": task.task_id,
                    "label": task.label,
                    "status": task.status,
                    "result": (task.result or "")[:500],
                    "error": task.error,
                    "duration_ms": task.duration_ms,
                    "user_id": task.user_id,
                },
            )

            # Move to history
            self._move_to_history(task)

            _LOGGER.info(
                "Subagent '%s' finished: status=%s, %dms",
                task.label,
                task.status,
                task.duration_ms,
            )

    def _get_agent(self, provider: str | None = None) -> Any:
        """Get an AI agent instance."""
        domain_data = self._hass.data.get(DOMAIN, {})
        agents = domain_data.get("agents", {})
        if not agents:
            return None
        if provider and provider in agents:
            return agents[provider]
        return next(iter(agents.values()), None)

    def _move_to_history(self, task: SubagentTask) -> None:
        """Move a completed task from active to history."""
        self._tasks.pop(task.task_id, None)
        self._completed_history.append(asdict(task))
        if len(self._completed_history) > MAX_TASK_HISTORY:
            self._completed_history = self._completed_history[-MAX_TASK_HISTORY:]
