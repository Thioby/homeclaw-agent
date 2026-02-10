"""Tests for SchedulerService (cron-based)."""

from __future__ import annotations

import time
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.proactive.scheduler import (
    MAX_JOBS,
    ScheduledJob,
    SchedulerService,
    _migrate_v1_to_v2,
    _next_fire,
    _validate_cron,
)


@pytest.fixture
def mock_store():
    """Create a mock HA Store."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"agents": {}}}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    return hass


def _make_scheduler(mock_hass, mock_store):
    """Create SchedulerService with mock store injected."""
    with patch("custom_components.homeclaw.proactive.scheduler.Store"):
        svc = SchedulerService(mock_hass)
    svc._store = mock_store
    return svc


# --- Cron Helpers ---


class TestCronHelpers:
    """Tests for cron validation and next-fire computation."""

    def test_validate_valid_cron(self):
        assert _validate_cron("0 20 * * *") == "0 20 * * *"
        assert _validate_cron("*/5 * * * *") == "*/5 * * * *"
        assert _validate_cron("0 8 * * 1") == "0 8 * * 1"
        assert _validate_cron("0 9 1 * *") == "0 9 1 * *"

    def test_validate_invalid_cron(self):
        with pytest.raises(ValueError, match="Invalid cron"):
            _validate_cron("not a cron")
        with pytest.raises(ValueError, match="Invalid cron"):
            _validate_cron("")
        with pytest.raises(ValueError, match="Invalid cron"):
            _validate_cron("60 * * * *")  # minute out of range

    def test_next_fire_returns_future(self):
        from homeassistant.util import dt as dt_util

        result = _next_fire("* * * * *")  # every minute
        assert result > dt_util.now()

    def test_next_fire_daily_at_20(self):
        from datetime import datetime, timezone

        base = datetime(2026, 2, 10, 15, 0, 0, tzinfo=timezone.utc)
        result = _next_fire("0 20 * * *", after=base)
        assert result.hour == 20
        assert result.minute == 0
        assert result.day == 10  # same day, later

    def test_next_fire_daily_at_20_after_20(self):
        from datetime import datetime, timezone

        base = datetime(2026, 2, 10, 21, 0, 0, tzinfo=timezone.utc)
        result = _next_fire("0 20 * * *", after=base)
        assert result.hour == 20
        assert result.day == 11  # next day


# --- Migration ---


class TestMigration:
    """Tests for v1 -> v2 migration."""

    def test_migrate_interval_job(self):
        data = {
            "jobs": [
                {
                    "job_id": "j1",
                    "name": "Every 30 min",
                    "enabled": True,
                    "schedule_type": "interval",
                    "interval_seconds": 1800,
                    "prompt": "Check something",
                }
            ],
            "run_history": [],
        }
        migrated = _migrate_v1_to_v2(data)
        assert migrated["jobs"][0]["cron"] == "*/30 * * * *"

    def test_migrate_hourly_interval(self):
        data = {
            "jobs": [
                {
                    "job_id": "j2",
                    "name": "Every 2 hours",
                    "enabled": True,
                    "schedule_type": "interval",
                    "interval_seconds": 7200,
                    "prompt": "Check something",
                }
            ],
            "run_history": [],
        }
        migrated = _migrate_v1_to_v2(data)
        assert migrated["jobs"][0]["cron"] == "0 */2 * * *"

    def test_migrate_at_job(self):
        data = {
            "jobs": [
                {
                    "job_id": "j3",
                    "name": "Morning report",
                    "enabled": True,
                    "schedule_type": "at",
                    "run_at": "2026-02-11T08:30:00",
                    "prompt": "Generate report",
                }
            ],
            "run_history": [],
        }
        migrated = _migrate_v1_to_v2(data)
        assert migrated["jobs"][0]["cron"] == "30 8 11 2 *"

    def test_migrate_preserves_existing_cron(self):
        data = {
            "jobs": [
                {
                    "job_id": "j4",
                    "name": "Already cron",
                    "enabled": True,
                    "cron": "0 20 * * *",
                    "prompt": "test",
                }
            ],
            "run_history": [],
        }
        migrated = _migrate_v1_to_v2(data)
        assert migrated["jobs"][0]["cron"] == "0 20 * * *"


# --- ScheduledJob Dataclass ---


class TestScheduledJob:
    """Tests for ScheduledJob dataclass."""

    def test_cron_job(self):
        job = ScheduledJob(
            job_id="abc123",
            name="Daily check",
            enabled=True,
            cron="0 20 * * *",
            prompt="Check energy usage",
        )
        assert job.cron == "0 20 * * *"
        assert job.last_status == "pending"
        assert job.one_shot is False

    def test_one_shot_job(self):
        job = ScheduledJob(
            job_id="def456",
            name="Morning report",
            enabled=True,
            cron="30 8 11 2 *",
            prompt="Generate morning report",
            one_shot=True,
        )
        assert job.one_shot is True

    def test_serialization(self):
        job = ScheduledJob(
            job_id="test",
            name="Test Job",
            enabled=True,
            cron="*/5 * * * *",
            prompt="test",
        )
        d = asdict(job)
        assert d["job_id"] == "test"
        assert d["name"] == "Test Job"
        assert d["cron"] == "*/5 * * * *"


# --- SchedulerService Init ---


class TestSchedulerServiceInit:
    """Tests for SchedulerService initialization."""

    @pytest.mark.asyncio
    async def test_initialize_empty(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert svc._initialized is True
        assert len(svc._jobs) == 0

    @pytest.mark.asyncio
    async def test_initialize_with_stored_jobs(self, mock_hass, mock_store):
        mock_store.async_load.return_value = {
            "jobs": [
                {
                    "job_id": "j1",
                    "name": "Test Job",
                    "enabled": True,
                    "cron": "0 20 * * *",
                    "prompt": "Do something",
                    "created_by": "user",
                    "last_status": "ok",
                    "created_at": time.time(),
                }
            ],
            "run_history": [{"job_id": "j1", "status": "ok", "timestamp": time.time()}],
        }

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert len(svc._jobs) == 1
        assert "j1" in svc._jobs
        assert svc._jobs["j1"].cron == "0 20 * * *"
        assert len(svc._run_history) == 1

    @pytest.mark.asyncio
    async def test_initialize_migrates_v1_data(self, mock_hass, mock_store):
        """Test that v1 data (interval/at) is auto-migrated to cron."""
        mock_store.async_load.return_value = {
            "jobs": [
                {
                    "job_id": "legacy",
                    "name": "Legacy Interval",
                    "enabled": True,
                    "schedule_type": "interval",
                    "interval_seconds": 3600,
                    "prompt": "check energy",
                }
            ],
            "run_history": [],
        }

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert "legacy" in svc._jobs
        assert svc._jobs["legacy"].cron == "0 */1 * * *"
        # Migration should persist immediately
        mock_store.async_save.assert_called()

    @pytest.mark.asyncio
    async def test_initialize_skips_invalid_jobs(self, mock_hass, mock_store):
        mock_store.async_load.return_value = {
            "jobs": [
                {"invalid": "data"},
                {
                    "job_id": "valid",
                    "name": "Valid Job",
                    "enabled": True,
                    "cron": "*/5 * * * *",
                    "prompt": "test",
                },
            ],
            "run_history": [],
        }

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert svc._initialized is True


# --- Job CRUD ---


class TestSchedulerJobCRUD:
    """Tests for job CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_cron_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Daily Report",
                prompt="Generate daily report",
                cron="0 20 * * *",
                user_id="user1",
            )

        assert job.name == "Daily Report"
        assert job.cron == "0 20 * * *"
        assert job.enabled is True
        assert job.one_shot is False
        assert job.next_run is not None
        assert job.job_id in svc._jobs

    @pytest.mark.asyncio
    async def test_add_one_shot_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="One-time Check",
                prompt="Check something once",
                cron="30 8 11 2 *",
                one_shot=True,
                created_by="agent",
            )

        assert job.one_shot is True
        assert job.created_by == "agent"

    @pytest.mark.asyncio
    async def test_add_job_validates_cron(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with pytest.raises(ValueError, match="Invalid cron"):
            await svc.add_job(
                name="Bad Cron",
                prompt="test",
                cron="not valid",
            )

    @pytest.mark.asyncio
    async def test_add_job_max_limit(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        for i in range(MAX_JOBS):
            svc._jobs[str(i)] = ScheduledJob(
                job_id=str(i),
                name=f"Job {i}",
                enabled=True,
                cron="0 0 * * *",
                prompt="test",
            )

        with pytest.raises(ValueError, match="Maximum"):
            await svc.add_job(
                name="One Too Many",
                prompt="test",
                cron="0 0 * * *",
            )

    @pytest.mark.asyncio
    async def test_remove_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="To Remove",
                prompt="test",
                cron="*/5 * * * *",
            )

        assert await svc.remove_job(job.job_id) is True
        assert job.job_id not in svc._jobs

    @pytest.mark.asyncio
    async def test_remove_nonexistent_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert await svc.remove_job("nonexistent") is False

    @pytest.mark.asyncio
    async def test_enable_disable_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Toggle Me",
                prompt="test",
                cron="*/5 * * * *",
            )

        # Disable
        updated = await svc.enable_job(job.job_id, False)
        assert updated is not None
        assert updated.enabled is False

        # Enable
        with patch.object(svc, "_register_job_timer"):
            updated = await svc.enable_job(job.job_id, True)
        assert updated.enabled is True

    @pytest.mark.asyncio
    async def test_enable_nonexistent_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        result = await svc.enable_job("ghost", True)
        assert result is None


# --- Listing ---


class TestSchedulerListing:
    """Tests for job listing and status."""

    @pytest.mark.asyncio
    async def test_list_jobs_all(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            await svc.add_job(name="J1", prompt="p1", cron="0 8 * * *")
            await svc.add_job(name="J2", prompt="p2", cron="0 20 * * *")

        jobs = svc.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_enabled_only(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            await svc.add_job(name="J1", prompt="p1", cron="0 8 * * *")
            j2 = await svc.add_job(name="J2", prompt="p2", cron="0 20 * * *")

        await svc.enable_job(j2.job_id, False)

        jobs = svc.list_jobs(include_disabled=False)
        assert len(jobs) == 1
        assert jobs[0]["name"] == "J1"

    @pytest.mark.asyncio
    async def test_get_status(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        status = svc.get_status()
        assert "total_jobs" in status
        assert "enabled_jobs" in status
        assert "active_timers" in status
        assert "recent_runs" in status

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Specific",
                prompt="test",
                cron="0 12 * * *",
            )

        found = svc.get_job(job.job_id)
        assert found is not None
        assert found["name"] == "Specific"
        assert found["cron"] == "0 12 * * *"

        not_found = svc.get_job("nonexistent")
        assert not_found is None


# --- Execution ---


class TestSchedulerExecution:
    """Tests for job execution."""

    @pytest.mark.asyncio
    async def test_run_prompt_success(self, mock_hass, mock_store):
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "response": "Energy usage is normal.",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        result = await svc.run_prompt("Check energy usage")
        assert result["success"] is True
        assert "Energy usage" in result["response"]

    @pytest.mark.asyncio
    async def test_run_prompt_no_agent(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        result = await svc.run_prompt("test")
        assert result["success"] is False
        assert "No AI agent" in result["error"]

    @pytest.mark.asyncio
    async def test_run_job_by_id(self, mock_hass, mock_store):
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "response": "Done.",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Manual Run",
                prompt="test prompt",
                cron="0 20 * * *",
            )

        with patch.object(svc, "_save_to_session", new_callable=AsyncMock):
            run = await svc.run_job(job.job_id)
        assert run is not None
        assert run.status == "ok"
        assert run.response == "Done."

    @pytest.mark.asyncio
    async def test_run_nonexistent_job(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        run = await svc.run_job("nonexistent")
        assert run is None

    @pytest.mark.asyncio
    async def test_on_job_tick_chains_next_timer(self, mock_hass, mock_store):
        """_on_job_tick must re-register the timer for the next fire time."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={"response": "OK", "success": True}
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Chain Test",
                prompt="test prompt",
                cron="0 20 * * *",
            )

        # Simulate the timer firing by calling _on_job_tick directly
        with (
            patch.object(svc, "_register_job_timer") as mock_register,
            patch.object(svc, "_save_to_session", new_callable=AsyncMock),
        ):
            await svc._on_job_tick(job)

        # Must re-register for the next fire
        mock_register.assert_called_once_with(job)
        # Job should still be enabled
        assert job.enabled is True

    @pytest.mark.asyncio
    async def test_on_job_tick_one_shot_disables_and_no_reregister(
        self, mock_hass, mock_store
    ):
        """One-shot jobs must be disabled after execution and NOT re-register a timer."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={"response": "Done once", "success": True}
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="One Shot Test",
                prompt="run once",
                cron="30 8 11 2 *",
                one_shot=True,
            )

        assert job.one_shot is True
        assert job.enabled is True

        # Simulate the timer firing
        with (
            patch.object(svc, "_register_job_timer") as mock_register,
            patch.object(svc, "_save_to_session", new_callable=AsyncMock),
        ):
            await svc._on_job_tick(job)

        # One-shot: must be disabled, must NOT re-register
        assert job.enabled is False
        mock_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_job_tick_records_history(self, mock_hass, mock_store):
        """_on_job_tick must record the run in history."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={"response": "Logged", "success": True}
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="History Test",
                prompt="test",
                cron="*/5 * * * *",
            )

        assert len(svc._run_history) == 0

        with (
            patch.object(svc, "_register_job_timer"),
            patch.object(svc, "_save_to_session", new_callable=AsyncMock),
        ):
            await svc._on_job_tick(job)

        assert len(svc._run_history) == 1
        assert svc._run_history[0]["job_id"] == job.job_id
        assert svc._run_history[0]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_execute_job_error_sets_status(self, mock_hass, mock_store):
        """If run_prompt raises, _execute_job must set status to 'error', not leave 'pending'."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(side_effect=RuntimeError("boom"))
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Error Test",
                prompt="will fail",
                cron="0 12 * * *",
            )

        with patch.object(svc, "_save_to_session", new_callable=AsyncMock):
            run = await svc._execute_job(job)
        assert run.status == "error"
        assert "boom" in run.error
        assert job.last_status == "error"


# --- Lifecycle ---


class TestSchedulerLifecycle:
    """Tests for scheduler start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_stop_cancels_all_timers(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        cancel1 = MagicMock()
        cancel2 = MagicMock()
        svc._cancel_callbacks = {"j1": cancel1, "j2": cancel2}

        await svc.async_stop()

        cancel1.assert_called_once()
        cancel2.assert_called_once()
        assert len(svc._cancel_callbacks) == 0

    @pytest.mark.asyncio
    async def test_stop_persists_state(self, mock_hass, mock_store):
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        await svc.async_stop()
        mock_store.async_save.assert_called()
