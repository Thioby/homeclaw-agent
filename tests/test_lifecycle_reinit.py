"""Tests for SubsystemLifecycle — re-init after full unload, get_subsystem."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.lifecycle import SubsystemLifecycle

from tests.lifecycle_helpers import (
    PANEL_PATCHES,
    SVC_PATCHES,
    make_entry,
    mock_hass,  # noqa: F401 — pytest fixture
    patch_all_subsystems,
    stop_all_patches,
)


# ---------------------------------------------------------------------------
# TestReInit
# ---------------------------------------------------------------------------


class TestReInit:
    """Full unload then re-setup must work cleanly."""

    @pytest.mark.asyncio
    async def test_full_unload_then_setup_works(self, mock_hass):
        """Setup 3, unload all, setup 1 again → works."""
        lifecycle = SubsystemLifecycle()
        config = {"ai_provider": "openai", "rag_enabled": False}

        # Phase 1: setup 3 entries
        entries = [make_entry(f"entry_{i}") for i in range(3)]
        patchers, mocks = patch_all_subsystems()
        try:
            for e in entries:
                await lifecycle.async_setup_entry(mock_hass, e, config)
        finally:
            stop_all_patches(patchers)

        assert lifecycle._initialized is True

        # Phase 2: unload all
        with (
            patch(PANEL_PATCHES["remove"]),
            patch(SVC_PATCHES["remove"], new_callable=AsyncMock),
        ):
            for e in entries:
                await lifecycle.async_unload_entry(mock_hass, e)

        assert lifecycle._initialized is False
        assert len(lifecycle._entry_ids) == 0

        # Phase 3: setup a fresh entry
        mock_hass.data = {DOMAIN: {"agents": {}}}
        new_entry = make_entry("entry_new")
        patchers2, mocks2 = patch_all_subsystems()
        try:
            await lifecycle.async_setup_entry(mock_hass, new_entry, config)
        finally:
            stop_all_patches(patchers2)

        assert lifecycle._initialized is True
        assert len(lifecycle._entry_ids) == 1
        assert lifecycle._heartbeat is not None


# ---------------------------------------------------------------------------
# TestGetSubsystem
# ---------------------------------------------------------------------------


class TestGetSubsystem:
    """Tests for get_subsystem() accessor."""

    def test_get_subsystem_returns_none_before_init(self):
        """Before init, all subsystems should be None."""
        lifecycle = SubsystemLifecycle()
        assert lifecycle.get_subsystem("heartbeat") is None
        assert lifecycle.get_subsystem("scheduler") is None
        assert lifecycle.get_subsystem("subagent_manager") is None
        assert lifecycle.get_subsystem("channel_manager") is None
        assert lifecycle.get_subsystem("rag_manager") is None
        assert lifecycle.get_subsystem("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_subsystem_returns_instance_after_init(self, mock_hass):
        """After init, get_subsystem returns the live instance."""
        lifecycle = SubsystemLifecycle()
        entry = make_entry()
        config = {"ai_provider": "openai", "rag_enabled": False}

        patchers, mocks = patch_all_subsystems()
        try:
            await lifecycle.async_setup_entry(mock_hass, entry, config)
        finally:
            stop_all_patches(patchers)

        assert lifecycle.get_subsystem("heartbeat") is not None
        assert lifecycle.get_subsystem("scheduler") is not None
        assert lifecycle.get_subsystem("subagent_manager") is not None
        assert lifecycle.get_subsystem("channel_manager") is not None
        # RAG is disabled in config, so should be None
        assert lifecycle.get_subsystem("rag_manager") is None
