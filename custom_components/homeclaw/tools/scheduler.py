"""Scheduler tool — lets the AI agent create and manage scheduled tasks.

The agent can use this tool to set reminders, periodic checks, and
one-shot scheduled prompts.  Under the hood, jobs are managed by the
``SchedulerService`` and executed via HA native scheduling primitives.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, List

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)


@ToolRegistry.register
class SchedulerTool(Tool):
    """Manage scheduled tasks and reminders."""

    id: ClassVar[str] = "scheduler"
    description: ClassVar[str] = (
        "Create, list, or remove scheduled tasks. Use this to set reminders, "
        "periodic monitoring checks, or one-shot timed prompts. "
        "Actions: list (show all jobs), add (create new), remove (delete by ID), status (summary)."
    )
    category: ClassVar[ToolCategory] = ToolCategory.HOME_ASSISTANT
    parameters: ClassVar[List[ToolParameter]] = [
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform: list, add, remove, or status",
            required=True,
            enum=["list", "add", "remove", "status"],
        ),
        ToolParameter(
            name="name",
            type="string",
            description="Human-readable name for the job (required for 'add')",
            required=False,
        ),
        ToolParameter(
            name="prompt",
            type="string",
            description="What the agent should do when the job runs (required for 'add')",
            required=False,
        ),
        ToolParameter(
            name="interval_minutes",
            type="integer",
            description="Run every N minutes. Use for periodic/recurring jobs (min 1).",
            required=False,
        ),
        ToolParameter(
            name="run_at",
            type="string",
            description="ISO datetime (e.g. 2026-02-11T08:00:00) for one-shot jobs",
            required=False,
        ),
        ToolParameter(
            name="job_id",
            type="string",
            description="Job ID (required for 'remove')",
            required=False,
        ),
        ToolParameter(
            name="notify",
            type="boolean",
            description="Whether to notify the user when the job runs (default: true)",
            required=False,
            default=True,
        ),
    ]

    async def execute(self, **params: Any) -> ToolResult:
        """Execute the scheduler tool."""
        from ..const import DOMAIN

        action = params.get("action", "")
        scheduler = (
            self.hass.data.get(DOMAIN, {}).get("scheduler") if self.hass else None
        )

        if not scheduler:
            return ToolResult(
                output="Scheduler service is not available.",
                success=False,
                error="Scheduler not initialized",
            )

        try:
            if action == "status":
                return ToolResult(
                    output=str(scheduler.get_status()),
                    metadata=scheduler.get_status(),
                )

            if action == "list":
                jobs = scheduler.list_jobs(include_disabled=True)
                if not jobs:
                    return ToolResult(output="No scheduled jobs found.")
                lines = []
                for j in jobs:
                    status = "enabled" if j["enabled"] else "disabled"
                    sched = j["schedule_type"]
                    if sched == "interval":
                        interval_min = (j.get("interval_seconds") or 0) // 60
                        sched_str = f"every {interval_min}m"
                    else:
                        sched_str = f"at {j.get('run_at', '?')}"
                    lines.append(
                        f"- [{j['job_id']}] {j['name']} ({sched_str}, {status}) "
                        f"last: {j.get('last_status', 'never')}"
                    )
                return ToolResult(
                    output=f"Scheduled jobs ({len(jobs)}):\n" + "\n".join(lines),
                    metadata={"jobs": jobs},
                )

            if action == "add":
                name = params.get("name")
                prompt = params.get("prompt")
                if not name or not prompt:
                    return ToolResult(
                        output="Both 'name' and 'prompt' are required for 'add'.",
                        success=False,
                        error="Missing required parameters",
                    )

                interval_min = params.get("interval_minutes")
                run_at = params.get("run_at")
                notify = params.get("notify", True)

                if interval_min:
                    schedule_type = "interval"
                    interval_seconds = max(60, int(interval_min) * 60)
                elif run_at:
                    schedule_type = "at"
                    interval_seconds = None
                else:
                    return ToolResult(
                        output="Provide 'interval_minutes' (recurring) or 'run_at' (one-shot).",
                        success=False,
                        error="No schedule specified",
                    )

                # Get user_id from hass.data if available
                user_id = ""
                if self.hass:
                    user_id = self.hass.data.get(DOMAIN, {}).get("_current_user_id", "")

                job = await scheduler.add_job(
                    name=name,
                    prompt=prompt,
                    schedule_type=schedule_type,
                    interval_seconds=interval_seconds,
                    run_at=run_at,
                    notify=notify,
                    delete_after_run=(schedule_type == "at"),
                    created_by="agent",
                    user_id=user_id,
                )

                sched_desc = (
                    f"every {interval_min} minutes"
                    if schedule_type == "interval"
                    else f"at {run_at}"
                )
                return ToolResult(
                    output=(
                        f"Scheduled job created: '{name}' (ID: {job.job_id}), "
                        f"runs {sched_desc}."
                    ),
                    metadata={"job_id": job.job_id},
                )

            if action == "remove":
                job_id = params.get("job_id")
                if not job_id:
                    return ToolResult(
                        output="'job_id' is required for 'remove'.",
                        success=False,
                        error="Missing job_id",
                    )
                removed = await scheduler.remove_job(job_id)
                if removed:
                    return ToolResult(output=f"Job {job_id} removed.")
                return ToolResult(
                    output=f"Job {job_id} not found.",
                    success=False,
                    error="Job not found",
                )

            return ToolResult(
                output=f"Unknown action: {action}",
                success=False,
                error="Invalid action",
            )

        except ValueError as e:
            return ToolResult(output=str(e), success=False, error=str(e))
        except Exception as e:
            _LOGGER.error("Scheduler tool error: %s", e)
            return ToolResult(
                output=f"Scheduler error: {e}",
                success=False,
                error=str(e),
            )
