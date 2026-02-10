"""Tests for SchedulerService."""

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


class TestScheduledJob:
    """Tests for ScheduledJob dataclass."""

    def test_interval_job(self):
        """Test creating an interval job."""
        job = ScheduledJob(
            job_id="abc123",
            name="Check energy",
            enabled=True,
            schedule_type="interval",
            interval_seconds=3600,
            prompt="Check energy usage",
        )
        assert job.schedule_type == "interval"
        assert job.interval_seconds == 3600
        assert job.last_status == "pending"

    def test_at_job(self):
        """Test creating a one-shot job."""
        job = ScheduledJob(
            job_id="def456",
            name="Morning report",
            enabled=True,
            schedule_type="at",
            run_at="2026-02-11T08:00:00",
            prompt="Generate morning report",
            delete_after_run=True,
        )
        assert job.schedule_type == "at"
        assert job.run_at == "2026-02-11T08:00:00"
        assert job.delete_after_run is True

    def test_serialization(self):
        """Test job serialization to dict."""
        job = ScheduledJob(
            job_id="test",
            name="Test Job",
            enabled=True,
            schedule_type="interval",
            interval_seconds=300,
            prompt="test",
        )
        d = asdict(job)
        assert d["job_id"] == "test"
        assert d["name"] == "Test Job"
        assert d["schedule_type"] == "interval"


class TestSchedulerServiceInit:
    """Tests for SchedulerService initialization."""

    @pytest.mark.asyncio
    async def test_initialize_empty(self, mock_hass, mock_store):
        """Test initialization with no stored data."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert svc._initialized is True
        assert len(svc._jobs) == 0

    @pytest.mark.asyncio
    async def test_initialize_with_stored_jobs(self, mock_hass, mock_store):
        """Test initialization loads stored jobs."""
        mock_store.async_load.return_value = {
            "jobs": [
                {
                    "job_id": "j1",
                    "name": "Test Job",
                    "enabled": True,
                    "schedule_type": "interval",
                    "interval_seconds": 600,
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
        assert len(svc._run_history) == 1

    @pytest.mark.asyncio
    async def test_initialize_skips_invalid_jobs(self, mock_hass, mock_store):
        """Test that invalid job data is skipped gracefully."""
        mock_store.async_load.return_value = {
            "jobs": [
                {"invalid": "data"},  # Missing required fields
                {
                    "job_id": "valid",
                    "name": "Valid Job",
                    "enabled": True,
                    "schedule_type": "interval",
                    "interval_seconds": 300,
                    "prompt": "test",
                },
            ],
            "run_history": [],
        }

        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        # Should not crash
        assert svc._initialized is True


class TestSchedulerJobCRUD:
    """Tests for job CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_interval_job(self, mock_hass, mock_store):
        """Test adding an interval job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Energy Check",
                prompt="Check energy usage and report anomalies",
                schedule_type="interval",
                interval_seconds=3600,
                user_id="user1",
            )

        assert job.name == "Energy Check"
        assert job.schedule_type == "interval"
        assert job.interval_seconds == 3600
        assert job.enabled is True
        assert job.job_id in svc._jobs

    @pytest.mark.asyncio
    async def test_add_at_job(self, mock_hass, mock_store):
        """Test adding a one-shot job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Morning Report",
                prompt="Generate morning report",
                schedule_type="at",
                run_at="2026-03-01T08:00:00",
                delete_after_run=True,
                created_by="agent",
            )

        assert job.schedule_type == "at"
        assert job.run_at == "2026-03-01T08:00:00"
        assert job.delete_after_run is True
        assert job.created_by == "agent"

    @pytest.mark.asyncio
    async def test_add_job_validates_interval(self, mock_hass, mock_store):
        """Test that interval must be at least 60 seconds."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with pytest.raises(ValueError, match="at least 60 seconds"):
            await svc.add_job(
                name="Too Fast",
                prompt="test",
                schedule_type="interval",
                interval_seconds=30,
            )

    @pytest.mark.asyncio
    async def test_add_job_validates_at_requires_run_at(self, mock_hass, mock_store):
        """Test that 'at' jobs require run_at."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with pytest.raises(ValueError, match="run_at is required"):
            await svc.add_job(
                name="No Time",
                prompt="test",
                schedule_type="at",
            )

    @pytest.mark.asyncio
    async def test_add_job_max_limit(self, mock_hass, mock_store):
        """Test that job limit is enforced."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        for i in range(MAX_JOBS):
            svc._jobs[str(i)] = ScheduledJob(
                job_id=str(i),
                name=f"Job {i}",
                enabled=True,
                schedule_type="interval",
                interval_seconds=300,
                prompt="test",
            )

        with pytest.raises(ValueError, match="Maximum"):
            await svc.add_job(
                name="One Too Many",
                prompt="test",
                schedule_type="interval",
                interval_seconds=300,
            )

    @pytest.mark.asyncio
    async def test_remove_job(self, mock_hass, mock_store):
        """Test removing a job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="To Remove",
                prompt="test",
                schedule_type="interval",
                interval_seconds=300,
            )

        assert await svc.remove_job(job.job_id) is True
        assert job.job_id not in svc._jobs

    @pytest.mark.asyncio
    async def test_remove_nonexistent_job(self, mock_hass, mock_store):
        """Test removing a non-existent job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        assert await svc.remove_job("nonexistent") is False

    @pytest.mark.asyncio
    async def test_enable_disable_job(self, mock_hass, mock_store):
        """Test enabling and disabling a job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Toggle Me",
                prompt="test",
                schedule_type="interval",
                interval_seconds=300,
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
        """Test enabling a non-existent job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        result = await svc.enable_job("ghost", True)
        assert result is None


class TestSchedulerListing:
    """Tests for job listing and status."""

    @pytest.mark.asyncio
    async def test_list_jobs_all(self, mock_hass, mock_store):
        """Test listing all jobs."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            await svc.add_job(
                name="J1", prompt="p1", schedule_type="interval", interval_seconds=300
            )
            await svc.add_job(
                name="J2", prompt="p2", schedule_type="interval", interval_seconds=600
            )

        jobs = svc.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_enabled_only(self, mock_hass, mock_store):
        """Test listing only enabled jobs."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            j1 = await svc.add_job(
                name="J1", prompt="p1", schedule_type="interval", interval_seconds=300
            )
            j2 = await svc.add_job(
                name="J2", prompt="p2", schedule_type="interval", interval_seconds=600
            )

        await svc.enable_job(j2.job_id, False)

        jobs = svc.list_jobs(include_disabled=False)
        assert len(jobs) == 1
        assert jobs[0]["name"] == "J1"

    @pytest.mark.asyncio
    async def test_get_status(self, mock_hass, mock_store):
        """Test getting scheduler status."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        status = svc.get_status()
        assert "total_jobs" in status
        assert "enabled_jobs" in status
        assert "active_timers" in status
        assert "recent_runs" in status

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, mock_hass, mock_store):
        """Test getting a specific job."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        with patch.object(svc, "_register_job_timer"):
            job = await svc.add_job(
                name="Specific",
                prompt="test",
                schedule_type="interval",
                interval_seconds=300,
            )

        found = svc.get_job(job.job_id)
        assert found is not None
        assert found["name"] == "Specific"

        not_found = svc.get_job("nonexistent")
        assert not_found is None


class TestSchedulerExecution:
    """Tests for job execution."""

    @pytest.mark.asyncio
    async def test_run_prompt_success(self, mock_hass, mock_store):
        """Test running an ad-hoc prompt successfully."""
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
        """Test running a prompt when no agent available."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        result = await svc.run_prompt("test")
        assert result["success"] is False
        assert "No AI agent" in result["error"]

    @pytest.mark.asyncio
    async def test_run_job_by_id(self, mock_hass, mock_store):
        """Test running a specific job by ID."""
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
                schedule_type="interval",
                interval_seconds=300,
            )

        run = await svc.run_job(job.job_id)
        assert run is not None
        assert run.status == "ok"
        assert run.response == "Done."

    @pytest.mark.asyncio
    async def test_run_nonexistent_job(self, mock_hass, mock_store):
        """Test running a non-existent job returns None."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        run = await svc.run_job("nonexistent")
        assert run is None


class TestSchedulerLifecycle:
    """Tests for scheduler start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_stop_cancels_all_timers(self, mock_hass, mock_store):
        """Test that stop cancels all timer callbacks."""
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
        """Test that stop persists state."""
        svc = _make_scheduler(mock_hass, mock_store)
        await svc.async_initialize()

        await svc.async_stop()
        mock_store.async_save.assert_called()
