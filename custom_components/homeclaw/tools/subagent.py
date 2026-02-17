"""Subagent tools — spawn and monitor background AI workers.

Provides two tools:
- ``subagent_spawn``: Delegate a task to a background subagent.
- ``subagent_status``: Check status/results of running subagents.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, List

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier

_LOGGER = logging.getLogger(__name__)


@ToolRegistry.register
class SubagentSpawnTool(Tool):
    """Delegate a complex task to a background subagent."""

    id: ClassVar[str] = "subagent_spawn"
    description: ClassVar[str] = (
        "Spawn a background subagent to handle a complex, independent task. "
        "The subagent runs asynchronously and has read-only access to Home Assistant. "
        "Use this for: analysis tasks, multi-step research, data gathering that would "
        "take too long in the main conversation. "
        "The result will be available via subagent_status tool."
    )
    short_description: ClassVar[str] = (
        "Spawn a background AI worker for complex independent tasks"
    )
    category: ClassVar[ToolCategory] = ToolCategory.UTILITY
    parameters: ClassVar[List[ToolParameter]] = [
        ToolParameter(
            name="task",
            type="string",
            description="Detailed task description for the subagent. Be specific about what to do and what to return.",
            required=True,
        ),
        ToolParameter(
            name="label",
            type="string",
            description="Short label for tracking (e.g. 'energy_analysis', 'room_audit')",
            required=False,
            default="background task",
        ),
    ]

    async def execute(self, **params: Any) -> ToolResult:
        """Spawn a subagent task."""
        from ..const import DOMAIN

        task_desc = params.get("task", "")
        label = params.get("label", "background task")

        if not task_desc:
            return ToolResult(
                output="Task description is required.",
                success=False,
                error="Missing task parameter",
            )

        manager = (
            self.hass.data.get(DOMAIN, {}).get("subagent_manager")
            if self.hass
            else None
        )
        if not manager:
            return ToolResult(
                output="Subagent system is not available.",
                success=False,
                error="SubagentManager not initialized",
            )

        # Get user_id from tool execution context
        user_id = params.get("_user_id", "")

        try:
            task_id = await manager.spawn(
                prompt=task_desc,
                label=label,
                user_id=user_id,
            )

            return ToolResult(
                output=(
                    f"Subagent spawned successfully.\n"
                    f"- Task ID: {task_id}\n"
                    f"- Label: {label}\n"
                    f"- Status: running\n\n"
                    f"Use subagent_status(action='get', task_id='{task_id}') to check results."
                ),
                metadata={"task_id": task_id, "label": label},
            )
        except RuntimeError as e:
            return ToolResult(
                output=str(e),
                success=False,
                error="Concurrency limit reached",
            )
        except Exception as e:
            _LOGGER.error("Subagent spawn error: %s", e)
            return ToolResult(
                output=f"Failed to spawn subagent: {e}",
                success=False,
                error=str(e),
            )


@ToolRegistry.register
class SubagentStatusTool(Tool):
    """Check status and results of background subagent tasks."""

    id: ClassVar[str] = "subagent_status"
    description: ClassVar[str] = (
        "Check the status and results of background subagent tasks. "
        "Actions: list (show all tasks), get (get specific task result), cancel (stop a running task)."
    )
    short_description: ClassVar[str] = (
        "Check status and results of background subagent tasks"
    )
    category: ClassVar[ToolCategory] = ToolCategory.UTILITY
    parameters: ClassVar[List[ToolParameter]] = [
        ToolParameter(
            name="action",
            type="string",
            description="Action: list (all tasks), get (specific task), cancel (stop task)",
            required=True,
            enum=["list", "get", "cancel"],
        ),
        ToolParameter(
            name="task_id",
            type="string",
            description="Task ID (required for 'get' and 'cancel')",
            required=False,
        ),
    ]

    async def execute(self, **params: Any) -> ToolResult:
        """Check subagent status."""
        from ..const import DOMAIN

        action = params.get("action", "")
        task_id = params.get("task_id")

        manager = (
            self.hass.data.get(DOMAIN, {}).get("subagent_manager")
            if self.hass
            else None
        )
        if not manager:
            return ToolResult(
                output="Subagent system is not available.",
                success=False,
                error="SubagentManager not initialized",
            )

        # Get user_id from tool execution context
        user_id = params.get("_user_id", "")

        try:
            if action == "list":
                tasks = manager.list_tasks(user_id=user_id)
                if not tasks:
                    return ToolResult(output="No active subagent tasks.")

                lines = []
                for t in tasks:
                    status_icon = {
                        "pending": "...",
                        "running": ">>>",
                        "completed": "OK",
                        "failed": "ERR",
                        "cancelled": "X",
                    }.get(t["status"], "?")
                    lines.append(
                        f"- [{status_icon}] {t['task_id']}: {t['label']} ({t['status']})"
                    )
                return ToolResult(
                    output=f"Subagent tasks ({len(tasks)}):\n" + "\n".join(lines),
                    metadata={"tasks": tasks},
                )

            if action == "get":
                if not task_id:
                    return ToolResult(
                        output="'task_id' is required for 'get' action.",
                        success=False,
                        error="Missing task_id",
                    )
                task = manager.get_task(task_id)
                if not task:
                    return ToolResult(
                        output=f"Task {task_id} not found.",
                        success=False,
                        error="Task not found",
                    )

                if task.status == "running":
                    return ToolResult(
                        output=f"Task '{task.label}' is still running. Check back later.",
                        metadata={"status": "running"},
                    )

                if task.status == "completed":
                    return ToolResult(
                        output=(
                            f"Task '{task.label}' completed ({task.duration_ms}ms):\n\n"
                            f"{task.result or 'No output'}"
                        ),
                        metadata={
                            "status": "completed",
                            "duration_ms": task.duration_ms,
                        },
                    )

                # Failed or cancelled
                return ToolResult(
                    output=(
                        f"Task '{task.label}' {task.status}: "
                        f"{task.error or 'Unknown error'}"
                    ),
                    success=False,
                    error=task.error,
                )

            if action == "cancel":
                if not task_id:
                    return ToolResult(
                        output="'task_id' is required for 'cancel' action.",
                        success=False,
                        error="Missing task_id",
                    )
                cancelled = await manager.cancel_task(task_id)
                if cancelled:
                    return ToolResult(output=f"Task {task_id} cancelled.")
                return ToolResult(
                    output=f"Task {task_id} not found or already completed.",
                    success=False,
                    error="Cannot cancel",
                )

            return ToolResult(
                output=f"Unknown action: {action}",
                success=False,
                error="Invalid action",
            )

        except Exception as e:
            _LOGGER.error("Subagent status error: %s", e)
            return ToolResult(
                output=f"Error: {e}",
                success=False,
                error=str(e),
            )
