"""Scheduler tool — lets the AI agent create and manage scheduled tasks.

The agent can use this tool to set reminders, periodic checks, and
scheduled prompts using cron expressions.  Under the hood, jobs are
managed by the ``SchedulerService`` and executed via HA native timers.

Cron quick-reference (5 fields: minute hour day-of-month month day-of-week):
    ``0 20 * * *``      — every day at 20:00
    ``*/30 * * * *``    — every 30 minutes
    ``0 8 * * 1``       — every Monday at 08:00
    ``0 9 1 * *``       — 1st of every month at 09:00
    ``0 7,19 * * *``    — every day at 07:00 and 19:00
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
        "periodic monitoring checks, or scheduled prompts. "
        "All schedules use cron expressions (minute hour day-of-month month day-of-week). "
        "Common patterns: '0 20 * * *' = daily at 20:00, '*/30 * * * *' = every 30 min, "
        "'0 8 * * 1' = Mondays at 08:00, '0 9 1 * *' = 1st of month at 09:00. "
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
            name="cron",
            type="string",
            description=(
                "Cron expression: 'minute hour day-of-month month day-of-week'. "
                "Examples: '0 20 * * *' (daily 20:00), '*/30 * * * *' (every 30 min), "
                "'0 8 * * 1' (Mondays 08:00). Required for 'add'."
            ),
            required=False,
        ),
        ToolParameter(
            name="one_shot",
            type="boolean",
            description="If true, the job runs once and is then disabled (default: false)",
            required=False,
            default=False,
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
        ToolParameter(
            name="provider",
            type="string",
            description="AI provider to use for this job (e.g. 'gemini_oauth', 'openai'). Default: use current provider.",
            required=False,
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
                    cron_expr = j.get("cron", "?")
                    one_shot = " (one-shot)" if j.get("one_shot") else ""
                    lines.append(
                        f"- [{j['job_id']}] {j['name']} "
                        f"(cron: {cron_expr}{one_shot}, {status}) "
                        f"next: {j.get('next_run', '?')}, "
                        f"last: {j.get('last_status', 'never')}"
                    )
                return ToolResult(
                    output=f"Scheduled jobs ({len(jobs)}):\n" + "\n".join(lines),
                    metadata={"jobs": jobs},
                )

            if action == "add":
                name = params.get("name")
                prompt = params.get("prompt")
                cron_expr = params.get("cron")

                if not name or not prompt:
                    return ToolResult(
                        output="Both 'name' and 'prompt' are required for 'add'.",
                        success=False,
                        error="Missing required parameters",
                    )

                if not cron_expr:
                    return ToolResult(
                        output=(
                            "A 'cron' expression is required. "
                            "Examples: '0 20 * * *' (daily 20:00), "
                            "'*/30 * * * *' (every 30 min), "
                            "'0 8 * * 1' (Mondays 08:00)."
                        ),
                        success=False,
                        error="Missing cron expression",
                    )

                notify = params.get("notify", True)
                one_shot = params.get("one_shot", False)

                # Get user_id from hass.data if available
                user_id = ""
                if self.hass:
                    user_id = self.hass.data.get(DOMAIN, {}).get("_current_user_id", "")

                provider = params.get("provider")

                job = await scheduler.add_job(
                    name=name,
                    prompt=prompt,
                    cron=cron_expr,
                    provider=provider,
                    notify=notify,
                    one_shot=one_shot,
                    created_by="agent",
                    user_id=user_id,
                )

                return ToolResult(
                    output=(
                        f"Scheduled job created: '{name}' (ID: {job.job_id}), "
                        f"cron: {cron_expr}, "
                        f"next run: {job.next_run}."
                    ),
                    metadata={"job_id": job.job_id, "next_run": job.next_run},
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
