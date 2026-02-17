"""Tests for SubsystemLifecycle — concurrent init, refcount unload, rollback."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.lifecycle import SubsystemLifecycle

from tests.lifecycle_helpers import (
    CHANNEL_PATCHES,
    PANEL_PATCHES,
    PROACTIVE_PATCHES,
    STATIC_PATH_PATCH,
    SVC_PATCHES,
    WS_PATCH,
    make_entry,
    mock_hass,  # noqa: F401 — pytest fixture
    patch_all_subsystems,
    stop_all_patches,
)


# ---------------------------------------------------------------------------
# TestConcurrentInit
# ---------------------------------------------------------------------------


class TestConcurrentInit:
    """Three concurrent setup_entry calls must init subsystems exactly once."""

    @pytest.mark.asyncio
    async def test_three_concurrent_setup_entries_init_once(self, mock_hass):
        """3× asyncio.gather(lifecycle.async_setup_entry) → subsystems started once."""
        init_count = 0

        class _CountingHeartbeat:
            def __init__(self, hass):
                nonlocal init_count
                init_count += 1

            async def async_initialize(self):
                await asyncio.sleep(0)

            async def async_start(self):
                await asyncio.sleep(0)

            async def async_stop(self):
                pass

        class _FakeScheduler:
            def __init__(self, hass):
                pass

            async def async_initialize(self):
                await asyncio.sleep(0)

            async def async_start(self):
                await asyncio.sleep(0)

            async def async_stop(self):
                pass

        class _FakeSubagent:
            def __init__(self, hass):
                pass

        lifecycle = SubsystemLifecycle()
        entries = [make_entry(f"entry_{i}") for i in range(3)]
        config = {"ai_provider": "openai", "rag_enabled": False}

        with (
            patch(PROACTIVE_PATCHES["heartbeat"], _CountingHeartbeat),
            patch(PROACTIVE_PATCHES["scheduler"], _FakeScheduler),
            patch(PROACTIVE_PATCHES["subagent"], _FakeSubagent),
            patch(CHANNEL_PATCHES["channel_mgr"]) as mock_cm,
            patch(CHANNEL_PATCHES["intake"]),
            patch(
                CHANNEL_PATCHES["build_cfg"], new_callable=AsyncMock, return_value={}
            ),
            patch(SVC_PATCHES["register"], new_callable=AsyncMock),
            patch(WS_PATCH),
            patch(PANEL_PATCHES["register"]),
            patch(STATIC_PATH_PATCH),
        ):
            mock_cm.return_value.async_setup = AsyncMock()
            mock_cm.return_value.active_channels = []

            await asyncio.gather(
                lifecycle.async_setup_entry(mock_hass, entries[0], config),
                lifecycle.async_setup_entry(mock_hass, entries[1], config),
                lifecycle.async_setup_entry(mock_hass, entries[2], config),
            )

        assert init_count == 1, (
            f"Expected heartbeat instantiated once, got {init_count}"
        )
        assert lifecycle._initialized is True
        assert len(lifecycle._entry_ids) == 3


# ---------------------------------------------------------------------------
# TestRefcountUnload
# ---------------------------------------------------------------------------


class TestRefcountUnload:
    """Unloading entries decrements refcount; last unload stops subsystems."""

    async def _setup_three_entries(self, mock_hass, lifecycle):
        """Helper: set up 3 entries through the lifecycle."""
        entries = [make_entry(f"entry_{i}") for i in range(3)]
        config = {"ai_provider": "openai", "rag_enabled": False}
        patchers, mocks = patch_all_subsystems()
        try:
            for e in entries:
                await lifecycle.async_setup_entry(mock_hass, e, config)
        finally:
            stop_all_patches(patchers)
        return entries, mocks

    @pytest.mark.asyncio
    async def test_unload_one_of_three_keeps_subsystems(self, mock_hass):
        """Setup 3 entries, unload 1 → subsystems still alive."""
        lifecycle = SubsystemLifecycle()
        entries, _ = await self._setup_three_entries(mock_hass, lifecycle)

        await lifecycle.async_unload_entry(mock_hass, entries[0])

        assert lifecycle._initialized is True
        assert len(lifecycle._entry_ids) == 2
        assert lifecycle._heartbeat is not None

    @pytest.mark.asyncio
    async def test_unload_all_three_stops_subsystems(self, mock_hass):
        """Setup 3, unload all 3 → all stopped, initialized=False."""
        lifecycle = SubsystemLifecycle()
        entries, _ = await self._setup_three_entries(mock_hass, lifecycle)

        for e in entries:
            await lifecycle.async_unload_entry(mock_hass, e)

        assert lifecycle._initialized is False
        assert len(lifecycle._entry_ids) == 0
        assert lifecycle._heartbeat is None
        assert lifecycle._scheduler is None
        assert lifecycle._subagent_mgr is None
        assert lifecycle._channel_mgr is None
        assert lifecycle._rag_mgr is None

    @pytest.mark.asyncio
    async def test_last_unload_triggers_stop(self, mock_hass):
        """Verify stop methods are called on last unload."""
        lifecycle = SubsystemLifecycle()
        entries, _ = await self._setup_three_entries(mock_hass, lifecycle)

        heartbeat = lifecycle._heartbeat
        scheduler = lifecycle._scheduler

        with (
            patch(PANEL_PATCHES["remove"]),
            patch(SVC_PATCHES["remove"], new_callable=AsyncMock) as mock_svc_remove,
        ):
            for e in entries:
                await lifecycle.async_unload_entry(mock_hass, e)

        heartbeat.async_stop.assert_called_once()
        scheduler.async_stop.assert_called_once()
        mock_svc_remove.assert_called_once()


# ---------------------------------------------------------------------------
# TestPartialFailureRollback
# ---------------------------------------------------------------------------


class TestPartialFailureRollback:
    """If a subsystem fails during init, already-started ones are rolled back."""

    @pytest.mark.asyncio
    async def test_scheduler_fail_rolls_back_heartbeat(self, mock_hass):
        """Heartbeat starts OK, scheduler raises → heartbeat.async_stop() called."""
        heartbeat_stop = AsyncMock()

        class _GoodHeartbeat:
            def __init__(self, hass):
                pass

            async def async_initialize(self):
                await asyncio.sleep(0)

            async def async_start(self):
                await asyncio.sleep(0)

            async def async_stop(self):
                await heartbeat_stop()

        class _BadScheduler:
            def __init__(self, hass):
                pass

            async def async_initialize(self):
                raise RuntimeError("scheduler init boom")

        lifecycle = SubsystemLifecycle()
        entry = make_entry()
        config = {"ai_provider": "openai", "rag_enabled": False}

        with (
            patch(PROACTIVE_PATCHES["heartbeat"], _GoodHeartbeat),
            patch(PROACTIVE_PATCHES["scheduler"], _BadScheduler),
            patch(PROACTIVE_PATCHES["subagent"], MagicMock),
            patch(CHANNEL_PATCHES["channel_mgr"]) as mock_cm,
            patch(CHANNEL_PATCHES["intake"]),
            patch(
                CHANNEL_PATCHES["build_cfg"], new_callable=AsyncMock, return_value={}
            ),
            patch(SVC_PATCHES["register"], new_callable=AsyncMock),
            patch(WS_PATCH),
            patch(PANEL_PATCHES["register"]),
            patch(STATIC_PATH_PATCH),
        ):
            mock_cm.return_value.async_setup = AsyncMock()
            mock_cm.return_value.active_channels = []

            await lifecycle.async_setup_entry(mock_hass, entry, config)

        heartbeat_stop.assert_called_once()
        assert lifecycle._heartbeat is None
        assert lifecycle._scheduler is None
