"""Scheduled task service for Homeclaw.

Manages user- and agent-created scheduled prompts using **cron expressions**
for all scheduling.  Every job stores a standard 5-field cron string
(minute hour day-of-month month day-of-week) and uses ``croniter`` to
compute the next fire time.  Under the hood a single
``async_track_point_in_time`` per job chains one-shot HA timers so that
jobs fire at the exact wall-clock times implied by the cron expression.

The agent can create jobs via the ``scheduler`` tool.  Users can also
manage jobs via WebSocket commands (``homeclaw/scheduler/*``).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from croniter import croniter
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Storage ---
SCHEDULER_STORAGE_KEY = f"{DOMAIN}_scheduler"
SCHEDULER_STORAGE_VERSION = 2

# --- Limits ---
MAX_JOBS = 50
MAX_JOB_HISTORY = 100
MIN_INTERVAL_SECONDS = 60


def _validate_cron(expression: str) -> str:
    """Validate a cron expression and return it normalised.

    Raises ValueError on invalid input.
    """
    if not croniter.is_valid(expression):
        raise ValueError(f"Invalid cron expression: {expression!r}")
    return expression


def _next_fire(cron: str, after: datetime | None = None) -> datetime:
    """Return the next fire time for *cron* after *after* (default: now, local TZ).

    Uses HA's configured timezone so that cron expressions like
    ``0 8 * * *`` fire at 08:00 *local* time, not UTC.
    """
    base = after or dt_util.now()
    return croniter(cron, base).get_next(datetime)


# --- Migration helpers ---


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate storage from v1 (interval/at) to v2 (cron).

    * ``interval`` jobs  -> ``*/N * * * *`` (or closest minute granularity).
    * ``at`` (one-shot)  -> preserved as ``cron`` with ``one_shot=True``.
    """
    jobs = data.get("jobs", [])
    migrated: list[dict[str, Any]] = []
    for j in jobs:
        stype = j.get("schedule_type", "")
        cron_expr = j.get("cron", "")

        if cron_expr:
            # Already has cron — keep as-is
            migrated.append(j)
            continue

        if stype == "interval":
            seconds = j.get("interval_seconds") or 300
            minutes = max(1, seconds // 60)
            if minutes < 60:
                cron_expr = f"*/{minutes} * * * *"
            elif minutes < 1440:
                hours = minutes // 60
                cron_expr = f"0 */{hours} * * *"
            else:
                cron_expr = "0 0 * * *"  # daily fallback

        elif stype == "at" and j.get("run_at"):
            # Try to parse the one-shot datetime and create a one-shot cron
            try:
                dt = dt_util.parse_datetime(j["run_at"])
                if dt:
                    cron_expr = f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"
                else:
                    cron_expr = "0 0 * * *"
            except (ValueError, TypeError):
                cron_expr = "0 0 * * *"
        else:
            cron_expr = "0 0 * * *"

        j["cron"] = cron_expr
        # Clean up legacy fields (keep them for reference but they're ignored)
        migrated.append(j)

    data["jobs"] = migrated
    return data


@dataclass
class ScheduledJob:
    """Definition of a scheduled job."""

    job_id: str
    name: str
    enabled: bool
    cron: str  # 5-field cron expression
    prompt: str = ""
    provider: str | None = None  # None = use default
    notify: bool = True
    one_shot: bool = False  # If True, disable after first run
    created_by: str = "user"  # "user" | "agent"
    user_id: str = ""
    session_id: str = ""  # Dedicated chat session for this job's runs
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
    """Manages scheduled prompts with cron-based scheduling.

    Every enabled job gets a single ``async_track_point_in_time`` callback
    targeting its next fire time.  After each execution the service computes
    the *next* fire time and re-registers the timer (chain of one-shots).

    Lifecycle:
        1. ``async_initialize()`` — loads persisted jobs from HA Store.
        2. ``async_start()`` — registers timers for all enabled jobs.
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
        """Load persisted jobs (with v1->v2 migration if needed)."""
        data = await self._store.async_load()
        if data:
            # Detect v1 data: if any job lacks "cron" field, migrate
            jobs_raw = data.get("jobs", [])
            needs_migration = any(not j.get("cron") for j in jobs_raw)
            if needs_migration:
                _LOGGER.info(
                    "Migrating scheduler storage from v1 (interval/at) to v2 (cron)"
                )
                data = _migrate_v1_to_v2(data)
                # Persist migrated data immediately
                await self._store.async_save(data)

            for job_data in data.get("jobs", []):
                try:
                    # Filter to only known fields
                    known = {k for k in ScheduledJob.__dataclass_fields__}
                    filtered = {k: v for k, v in job_data.items() if k in known}
                    job = ScheduledJob(**filtered)
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
        cron: str,
        provider: str | None = None,
        notify: bool = True,
        one_shot: bool = False,
        created_by: str = "user",
        user_id: str = "",
    ) -> ScheduledJob:
        """Create and register a new scheduled job.

        Args:
            name: Human-readable job name.
            prompt: The AI prompt to execute when the job runs.
            cron: 5-field cron expression (minute hour dom month dow).
            provider: AI provider to use (None for default).
            notify: Whether to notify the user.
            one_shot: If True, disable after first execution.
            created_by: "user" or "agent".
            user_id: Owner user ID.

        Returns:
            The created ScheduledJob.

        Raises:
            ValueError: If max jobs reached or invalid cron expression.
        """
        if len(self._jobs) >= MAX_JOBS:
            raise ValueError(f"Maximum number of scheduled jobs reached ({MAX_JOBS})")

        cron = _validate_cron(cron)

        job = ScheduledJob(
            job_id=str(uuid.uuid4())[:8],
            name=name,
            enabled=True,
            cron=cron,
            prompt=prompt,
            provider=provider,
            notify=notify,
            one_shot=one_shot,
            created_by=created_by,
            user_id=user_id,
        )

        # Compute next_run
        job.next_run = _next_fire(cron).isoformat()

        self._jobs[job.job_id] = job
        self._register_job_timer(job)
        await self._async_save()

        _LOGGER.info(
            "Scheduled job added: '%s' (cron=%s, id=%s, by=%s, next=%s)",
            name,
            cron,
            job.job_id,
            created_by,
            job.next_run,
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
            # Recompute next_run and register timer
            job.next_run = _next_fire(job.cron).isoformat()
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
        """Run an ad-hoc prompt.

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
        """Register an HA point-in-time timer for the job's next fire time.

        Uses ``croniter`` to compute the next fire time and
        ``async_track_point_in_time`` for a one-shot callback.
        After each fire, the callback re-registers for the next time.
        """
        # Cancel existing timer for this job
        existing = self._cancel_callbacks.pop(job.job_id, None)
        if existing:
            existing()

        try:
            target = _next_fire(job.cron)
        except (ValueError, KeyError) as e:
            _LOGGER.warning("Cannot compute next fire for job '%s': %s", job.name, e)
            return

        job.next_run = target.isoformat()

        async def _tick_callback(_now: datetime, _job: ScheduledJob = job) -> None:
            await self._on_job_tick(_job)

        cancel = async_track_point_in_time(
            self._hass,
            _tick_callback,
            target,
        )
        self._cancel_callbacks[job.job_id] = cancel

    async def _on_job_tick(self, job: ScheduledJob) -> None:
        """Called when a job timer fires."""
        _LOGGER.info("Scheduler: executing job '%s' (id=%s)", job.name, job.job_id)
        await self._execute_job(job)

        # Remove from cancel_callbacks (the one-shot already fired)
        self._cancel_callbacks.pop(job.job_id, None)

        if job.one_shot:
            job.enabled = False
            _LOGGER.info("One-shot job '%s' disabled after run", job.name)
        elif job.enabled:
            # Chain: register the next timer
            self._register_job_timer(job)

        await self._async_save()

    async def _execute_job(self, job: ScheduledJob) -> JobRun:
        """Execute a scheduled job and record the result.

        Each job gets a dedicated chat session. The prompt and response are
        saved as messages so the user can review them in the sidebar.
        """
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

            # Save prompt + response to a dedicated session
            await self._save_to_session(job, run)

        except BaseException as e:
            run.status = "error"
            run.error = str(e)
            run.duration_ms = int((time.monotonic() - start_time) * 1000)
            job.last_status = "error"
            job.last_error = str(e)
            _LOGGER.error("Job '%s' execution failed: %s", job.name, e)
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise

        # Store run in history
        self._run_history.append(asdict(run))
        if len(self._run_history) > MAX_JOB_HISTORY:
            self._run_history = self._run_history[-MAX_JOB_HISTORY:]

        return run

    async def _save_to_session(self, job: ScheduledJob, run: JobRun) -> None:
        """Save the job run as messages in a dedicated chat session.

        Creates the session on first run, reuses it for subsequent runs.
        The session appears in the user's sidebar with a scheduler prefix.
        """
        from ..storage import Message, SessionStorage

        user_id = job.user_id or "default"
        cache_key = f"{DOMAIN}_storage_{user_id}"

        # Get or create SessionStorage for this user
        if cache_key not in self._hass.data:
            self._hass.data[cache_key] = SessionStorage(self._hass, user_id)
        storage: SessionStorage = self._hass.data[cache_key]

        try:
            # Create session on first run
            if not job.session_id:
                provider_name = job.provider or "default"
                session = await storage.create_session(
                    provider=provider_name,
                    title=f"[Scheduler] {job.name}",
                )
                job.session_id = session.session_id
                _LOGGER.info(
                    "Created scheduler session '%s' for job '%s'",
                    session.session_id,
                    job.name,
                )
            else:
                # Verify session still exists (could have been deleted by user)
                existing = await storage.get_session(job.session_id)
                if not existing:
                    session = await storage.create_session(
                        provider=job.provider or "default",
                        title=f"[Scheduler] {job.name}",
                    )
                    job.session_id = session.session_id
                    _LOGGER.info(
                        "Re-created scheduler session for job '%s' (old session was deleted)",
                        job.name,
                    )

            now = datetime.now().isoformat()
            run_id = str(uuid.uuid4())[:8]

            # Save user message (the prompt)
            await storage.add_message(
                job.session_id,
                Message(
                    message_id=f"sched-{job.job_id}-{run_id}-prompt",
                    session_id=job.session_id,
                    role="user",
                    content=job.prompt,
                    timestamp=now,
                    metadata={"source": "scheduler", "job_id": job.job_id},
                ),
            )

            # Save assistant message (the response or error)
            content = run.response if run.status == "ok" else f"Error: {run.error}"
            await storage.add_message(
                job.session_id,
                Message(
                    message_id=f"sched-{job.job_id}-{run_id}-response",
                    session_id=job.session_id,
                    role="assistant",
                    content=content or "(no response)",
                    timestamp=now,
                    status="completed" if run.status == "ok" else "error",
                    error_message=run.error,
                    metadata={
                        "source": "scheduler",
                        "job_id": job.job_id,
                        "duration_ms": run.duration_ms,
                    },
                ),
            )

        except Exception as err:
            _LOGGER.warning(
                "Failed to save scheduler run to session for job '%s': %s",
                job.name,
                err,
            )

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
