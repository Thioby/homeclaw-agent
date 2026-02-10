"""Scheduled task service for Homeclaw.

Manages user- and agent-created scheduled prompts. Uses HA native
scheduling primitives (``async_track_time_interval``,
``async_track_point_in_time``) for execution, and HA ``Store`` for
persistence across restarts.

The agent can create jobs via the ``scheduler`` tool.  Users can also
create HA automations that call ``homeclaw.run_scheduled_prompt``.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_time,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Storage ---
SCHEDULER_STORAGE_KEY = f"{DOMAIN}_scheduler"
SCHEDULER_STORAGE_VERSION = 1

# --- Limits ---
MAX_JOBS = 50
MAX_JOB_HISTORY = 100


@dataclass
class ScheduledJob:
    """Definition of a scheduled job."""

    job_id: str
    name: str
    enabled: bool
    schedule_type: str  # "interval" | "at"
    interval_seconds: int | None = None  # for "interval"
    run_at: str | None = None  # ISO datetime, for "at" (one-shot)
    prompt: str = ""
    provider: str | None = None  # None = use default
    notify: bool = True
    delete_after_run: bool = False  # One-shot jobs
    created_by: str = "user"  # "user" | "agent"
    user_id: str = ""
    # State
    last_run: str | None = None
    next_run: str | None = None
    last_status: str = "pending"  # "ok" | "error" | "pending"
    last_error: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class JobRun:
    """Record of a single job execution."""

    job_id: str
    job_name: str
    timestamp: float
    status: str  # "ok" | "error"
    response: str = ""
    error: str = ""
    duration_ms: int = 0


class SchedulerService:
    """Manages scheduled prompts with HA native scheduling.

    Lifecycle:
        1. ``async_initialize()`` — loads persisted jobs from HA Store.
        2. ``async_start()`` — re-registers timers for all enabled jobs.
        3. ``async_stop()`` — cancels all timers and persists state.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store = Store[dict[str, Any]](
            hass, SCHEDULER_STORAGE_VERSION, SCHEDULER_STORAGE_KEY
        )
        self._jobs: dict[str, ScheduledJob] = {}
        self._cancel_callbacks: dict[str, CALLBACK_TYPE] = {}
        self._run_history: list[dict[str, Any]] = []
        self._initialized = False

    # === Lifecycle ===

    async def async_initialize(self) -> None:
        """Load persisted jobs."""
        data = await self._store.async_load()
        if data:
            for job_data in data.get("jobs", []):
                try:
                    job = ScheduledJob(
                        **{
                            k: v
                            for k, v in job_data.items()
                            if k in ScheduledJob.__dataclass_fields__
                        }
                    )
                    self._jobs[job.job_id] = job
                except (TypeError, ValueError) as e:
                    _LOGGER.warning("Skipping invalid job: %s", e)

            self._run_history = data.get("run_history", [])[-MAX_JOB_HISTORY:]

        self._initialized = True
        _LOGGER.info("Scheduler initialized with %d jobs", len(self._jobs))

    async def async_start(self) -> None:
        """Register timers for all enabled jobs."""
        if not self._initialized:
            await self.async_initialize()

        for job in self._jobs.values():
            if job.enabled:
                self._register_job_timer(job)

        _LOGGER.info(
            "Scheduler started: %d enabled jobs",
            sum(1 for j in self._jobs.values() if j.enabled),
        )

    async def async_stop(self) -> None:
        """Cancel all timers and persist state."""
        for cancel in self._cancel_callbacks.values():
            cancel()
        self._cancel_callbacks.clear()
        await self._async_save()
        _LOGGER.info("Scheduler stopped")

    # === Job Management ===

    async def add_job(
        self,
        name: str,
        prompt: str,
        *,
        schedule_type: str = "at",
        interval_seconds: int | None = None,
        run_at: str | None = None,
        provider: str | None = None,
        notify: bool = True,
        delete_after_run: bool = False,
        created_by: str = "user",
        user_id: str = "",
    ) -> ScheduledJob:
        """Create and register a new scheduled job.

        Args:
            name: Human-readable job name.
            prompt: The AI prompt to execute when the job runs.
            schedule_type: "interval" (recurring) or "at" (one-shot).
            interval_seconds: Interval in seconds (for "interval" type).
            run_at: ISO datetime string (for "at" type).
            provider: AI provider to use (None for default).
            notify: Whether to notify the user.
            delete_after_run: Auto-delete after first run (for "at" type).
            created_by: "user" or "agent".
            user_id: Owner user ID.

        Returns:
            The created ScheduledJob.

        Raises:
            ValueError: If max jobs reached or invalid parameters.
        """
        if len(self._jobs) >= MAX_JOBS:
            raise ValueError(f"Maximum number of scheduled jobs reached ({MAX_JOBS})")

        if schedule_type == "interval" and (
            not interval_seconds or interval_seconds < 60
        ):
            raise ValueError("Interval must be at least 60 seconds")

        if schedule_type == "at" and not run_at:
            raise ValueError("run_at is required for 'at' schedule type")

        job = ScheduledJob(
            job_id=str(uuid.uuid4())[:8],
            name=name,
            enabled=True,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            run_at=run_at,
            prompt=prompt,
            provider=provider,
            notify=notify,
            delete_after_run=delete_after_run if schedule_type == "at" else False,
            created_by=created_by,
            user_id=user_id,
        )

        # Compute next_run
        if schedule_type == "interval" and interval_seconds:
            next_dt = dt_util.utcnow() + timedelta(seconds=interval_seconds)
            job.next_run = next_dt.isoformat()
        elif schedule_type == "at" and run_at:
            job.next_run = run_at

        self._jobs[job.job_id] = job
        self._register_job_timer(job)
        await self._async_save()

        _LOGGER.info(
            "Scheduled job added: '%s' (type=%s, id=%s, by=%s)",
            name,
            schedule_type,
            job.job_id,
            created_by,
        )
        return job

    async def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: ID of the job to remove.

        Returns:
            True if removed, False if not found.
        """
        if job_id not in self._jobs:
            return False

        # Cancel timer
        cancel = self._cancel_callbacks.pop(job_id, None)
        if cancel:
            cancel()

        del self._jobs[job_id]
        await self._async_save()
        _LOGGER.info("Scheduled job removed: %s", job_id)
        return True

    async def enable_job(self, job_id: str, enabled: bool) -> ScheduledJob | None:
        """Enable or disable a job.

        Args:
            job_id: Job ID.
            enabled: New enabled state.

        Returns:
            Updated job, or None if not found.
        """
        job = self._jobs.get(job_id)
        if not job:
            return None

        job.enabled = enabled

        if enabled:
            self._register_job_timer(job)
        else:
            cancel = self._cancel_callbacks.pop(job_id, None)
            if cancel:
                cancel()

        await self._async_save()
        return job

    def list_jobs(self, include_disabled: bool = True) -> list[dict[str, Any]]:
        """List all jobs as dicts.

        Args:
            include_disabled: Whether to include disabled jobs.

        Returns:
            List of job dictionaries.
        """
        jobs = list(self._jobs.values())
        if not include_disabled:
            jobs = [j for j in jobs if j.enabled]
        return [asdict(j) for j in jobs]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get a specific job by ID."""
        job = self._jobs.get(job_id)
        return asdict(job) if job else None

    def get_run_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent job execution history."""
        return self._run_history[-limit:]

    def get_status(self) -> dict[str, Any]:
        """Return scheduler status summary."""
        enabled_count = sum(1 for j in self._jobs.values() if j.enabled)
        return {
            "total_jobs": len(self._jobs),
            "enabled_jobs": enabled_count,
            "active_timers": len(self._cancel_callbacks),
            "recent_runs": len(self._run_history),
        }

    # === Execution ===

    async def run_job(self, job_id: str) -> JobRun | None:
        """Manually run a specific job now.

        Args:
            job_id: Job ID to execute.

        Returns:
            JobRun result, or None if job not found.
        """
        job = self._jobs.get(job_id)
        if not job:
            return None
        return await self._execute_job(job)

    async def run_prompt(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        notify: bool = True,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Run an ad-hoc prompt (called by homeclaw.run_scheduled_prompt service).

        Args:
            prompt: The AI prompt to execute.
            provider: AI provider to use.
            notify: Whether to fire events.
            user_id: User context.

        Returns:
            Dict with response or error.
        """
        start_time = time.monotonic()

        agent = self._get_agent(provider)
        if not agent:
            return {"success": False, "error": "No AI agent available"}

        try:
            result = await agent.process_query(
                user_query=prompt,
                conversation_history=[],
                user_id=user_id,
            )

            response = result.get("response", "")
            duration_ms = int((time.monotonic() - start_time) * 1000)

            if notify:
                self._hass.bus.async_fire(
                    f"{DOMAIN}_scheduled_result",
                    {
                        "prompt": prompt[:200],
                        "response": response[:500],
                        "success": result.get("success", False),
                        "duration_ms": duration_ms,
                    },
                )

            return {
                "success": result.get("success", False),
                "response": response,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            _LOGGER.error("Scheduled prompt execution failed: %s", e)
            return {"success": False, "error": str(e)}

    # === Internal Helpers ===

    def _register_job_timer(self, job: ScheduledJob) -> None:
        """Register an HA timer for a job."""
        # Cancel existing timer for this job
        existing = self._cancel_callbacks.pop(job.job_id, None)
        if existing:
            existing()

        if job.schedule_type == "interval" and job.interval_seconds:
            cancel = async_track_time_interval(
                self._hass,
                lambda now, j=job: self._hass.async_create_task(self._on_job_tick(j)),
                timedelta(seconds=job.interval_seconds),
                name=f"{DOMAIN}_job_{job.job_id}",
                cancel_on_shutdown=True,
            )
            self._cancel_callbacks[job.job_id] = cancel

        elif job.schedule_type == "at" and job.run_at:
            try:
                target = dt_util.parse_datetime(job.run_at)
                if target and target > dt_util.utcnow():
                    cancel = async_track_point_in_time(
                        self._hass,
                        lambda now, j=job: self._hass.async_create_task(
                            self._on_job_tick(j)
                        ),
                        target,
                    )
                    self._cancel_callbacks[job.job_id] = cancel
                else:
                    _LOGGER.debug("Job '%s' has past run_at, skipping timer", job.name)
            except (ValueError, TypeError) as e:
                _LOGGER.warning("Invalid run_at for job '%s': %s", job.name, e)

    async def _on_job_tick(self, job: ScheduledJob) -> None:
        """Called when a job timer fires."""
        _LOGGER.info("Scheduler: executing job '%s' (id=%s)", job.name, job.job_id)
        run = await self._execute_job(job)

        # For one-shot jobs, clean up after execution
        if job.schedule_type == "at":
            self._cancel_callbacks.pop(job.job_id, None)
            if job.delete_after_run:
                del self._jobs[job.job_id]
                _LOGGER.info("One-shot job '%s' deleted after run", job.name)
            else:
                job.enabled = False

        await self._async_save()

    async def _execute_job(self, job: ScheduledJob) -> JobRun:
        """Execute a scheduled job and record the result."""
        start_time = time.monotonic()
        run = JobRun(
            job_id=job.job_id,
            job_name=job.name,
            timestamp=time.time(),
            status="pending",
        )

        try:
            result = await self.run_prompt(
                prompt=job.prompt,
                provider=job.provider,
                notify=job.notify,
                user_id=job.user_id,
            )

            run.status = "ok" if result.get("success") else "error"
            run.response = result.get("response", "")[:1000]
            run.error = result.get("error", "")
            run.duration_ms = int((time.monotonic() - start_time) * 1000)

            # Update job state
            job.last_run = datetime.now().isoformat()
            job.last_status = run.status
            job.last_error = run.error

            # Compute next_run for interval jobs
            if job.schedule_type == "interval" and job.interval_seconds:
                next_dt = dt_util.utcnow() + timedelta(seconds=job.interval_seconds)
                job.next_run = next_dt.isoformat()

        except Exception as e:
            run.status = "error"
            run.error = str(e)
            run.duration_ms = int((time.monotonic() - start_time) * 1000)
            job.last_status = "error"
            job.last_error = str(e)
            _LOGGER.error("Job '%s' execution failed: %s", job.name, e)

        # Store run in history
        self._run_history.append(asdict(run))
        if len(self._run_history) > MAX_JOB_HISTORY:
            self._run_history = self._run_history[-MAX_JOB_HISTORY:]

        return run

    def _get_agent(self, provider: str | None = None) -> Any:
        """Get an AI agent instance."""
        domain_data = self._hass.data.get(DOMAIN, {})
        agents = domain_data.get("agents", {})
        if not agents:
            return None

        if provider and provider in agents:
            return agents[provider]

        # Return first available
        return next(iter(agents.values()), None)

    async def _async_save(self) -> None:
        """Persist jobs and run history to HA Store."""
        await self._store.async_save(
            {
                "jobs": [
                    {k: v for k, v in asdict(j).items() if k != "cancel_callback"}
                    for j in self._jobs.values()
                ],
                "run_history": self._run_history[-MAX_JOB_HISTORY:],
            }
        )
