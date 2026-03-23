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
from datetime import datetime, timedelta
from typing import Any, ClassVar, List

from homeassistant.util import dt as dt_util

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier

_LOGGER = logging.getLogger(__name__)


def _check_one_shot_not_in_past(cron_expr: str) -> str | None:
    """Check if a one-shot cron expression targets a time in the past.

    Builds the intended datetime from cron fields + current year.
    If that datetime is more than 7 days in the past, the LLM likely
    used a stale date.  The 7-day grace window handles cross-year
    scheduling (e.g. Dec 30 → Jan 2).

    Returns an error message string if blocked, None if OK.
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return None  # Let normal validation handle bad cron

    minute_s, hour_s, day_s, month_s, _ = parts

    # Only check crons with specific day AND month (one-shot pattern)
    if day_s == "*" or month_s == "*":
        return None

    try:
        now = dt_util.now()
        target = now.replace(
            month=int(month_s),
            day=int(day_s),
            hour=int(hour_s),
            minute=int(minute_s),
            second=0,
            microsecond=0,
        )
        # If intended date is more than 7 days in the past → stale date error
        if now - target > timedelta(days=7):
            now_str = now.strftime("%Y-%m-%d %H:%M %Z")
            return (
                f"The cron '{cron_expr}' targets a time that already passed. "
                f"Current time is {now_str}. "
                f"Please recalculate using the correct date and time."
            )
    except (ValueError, OverflowError):
        return None  # Bad date fields — let croniter validation handle it

    return None


@ToolRegistry.register
class SchedulerTool(Tool):
    """Manage scheduled tasks and reminders."""

    id: ClassVar[str] = "scheduler"
    description: ClassVar[str] = (
        "Create, list, or remove scheduled tasks. Use this to set reminders, "
        "periodic monitoring checks, or scheduled prompts. "
        "All schedules use cron expressions (minute hour day-of-month month day-of-week). "
        "IMPORTANT: For one-shot tasks ('in 5 min', 'at 3pm today'), use FULL date cron "
        "with specific day and month (e.g. '35 14 10 2 *' for 14:35 on Feb 10) and one_shot=true. "
        "Do NOT use wildcard day/month for one-shot tasks or they will fire on the wrong day. "
        "Recurring patterns: '0 20 * * *' = daily 20:00, '*/30 * * * *' = every 30 min, "
        "'0 8 * * 1' = Mondays 08:00. "
        "Modes: 'agent' (default) runs an AI prompt, 'tool' executes a tool directly "
        "(faster, no LLM needed). For 'tool' mode, specify tool_id and tool_params instead of prompt. "
        "Actions: list (show all jobs), add (create new), remove (delete by ID), status (summary)."
    )
    category: ClassVar[ToolCategory] = ToolCategory.HOME_ASSISTANT
    tier: ClassVar[ToolTier] = ToolTier.CORE
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
            description="What the agent should do when the job runs (required for 'add' with mode='agent')",
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
            name="mode",
            type="string",
            description=(
                "Execution mode: 'agent' (default) runs a prompt through the AI agent, "
                "'tool' calls a specific tool directly without LLM inference."
            ),
            required=False,
            default="agent",
            enum=["agent", "tool"],
        ),
        ToolParameter(
            name="tool_id",
            type="string",
            description=(
                "Tool ID to execute when mode='tool' (e.g. 'call_service', 'get_entity_state'). "
                "Required when mode='tool'."
            ),
            required=False,
        ),
        ToolParameter(
            name="tool_params",
            type="object",
            description="Parameters dict to pass to the tool when mode='tool'.",
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
                    mode_info = ""
                    if j.get("mode") == "tool":
                        mode_info = f" [tool:{j.get('tool_id', '?')}]"
                    lines.append(
                        f"- [{j['job_id']}] {j['name']}{mode_info} "
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
                prompt = params.get("prompt", "")
                cron_expr = params.get("cron")
                mode = params.get("mode", "agent")
                tool_id_param = params.get("tool_id", "")
                tool_params_val = params.get("tool_params") or {}

                if not name:
                    return ToolResult(
                        output="'name' is required for 'add'.",
                        success=False,
                        error="Missing name",
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

                if mode == "tool" and not tool_id_param:
                    return ToolResult(
                        output="'tool_id' is required when mode='tool'.",
                        success=False,
                        error="Missing tool_id",
                    )

                if mode == "agent" and not prompt:
                    return ToolResult(
                        output="'prompt' is required when mode='agent'.",
                        success=False,
                        error="Missing prompt",
                    )

                one_shot = params.get("one_shot", False)

                # Guard: prevent one-shot tasks targeting a time in the past
                if one_shot:
                    past_error = _check_one_shot_not_in_past(cron_expr)
                    if past_error:
                        return ToolResult(
                            output=past_error,
                            success=False,
                            error="One-shot task targets past time",
                        )

                notify = params.get("notify", True)
                user_id = params.get("_user_id", "")
                provider = params.get("provider")

                job = await scheduler.add_job(
                    name=name,
                    prompt=prompt,
                    cron=cron_expr,
                    mode=mode,
                    tool_id=tool_id_param,
                    tool_params=tool_params_val,
                    provider=provider,
                    notify=notify,
                    one_shot=one_shot,
                    created_by="agent",
                    user_id=user_id,
                )

                if mode == "tool":
                    output = (
                        f"Scheduled tool job created: '{name}' (ID: {job.job_id}), "
                        f"tool: {tool_id_param}, cron: {cron_expr}, "
                        f"next run: {job.next_run}."
                    )
                else:
                    output = (
                        f"Scheduled job created: '{name}' (ID: {job.job_id}), "
                        f"cron: {cron_expr}, "
                        f"next run: {job.next_run}."
                    )

                return ToolResult(
                    output=output,
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
