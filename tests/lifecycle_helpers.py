"""Shared helpers for SubsystemLifecycle tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.const import DOMAIN

# ---------------------------------------------------------------------------
# Patch targets (all imports inside lifecycle.py)
# ---------------------------------------------------------------------------
PROACTIVE_PATCHES = {
    "heartbeat": "custom_components.homeclaw.proactive.HeartbeatService",
    "scheduler": "custom_components.homeclaw.proactive.SchedulerService",
    "subagent": "custom_components.homeclaw.core.subagent.SubagentManager",
}
CHANNEL_PATCHES = {
    "channel_mgr": "custom_components.homeclaw.channels.manager.ChannelManager",
    "intake": "custom_components.homeclaw.channels.intake.MessageIntake",
    "build_cfg": "custom_components.homeclaw.channels.config.build_channel_runtime_config",
}
RAG_PATCH = "custom_components.homeclaw.rag.RAGManager"
SVC_PATCHES = {
    "register": "custom_components.homeclaw.services.async_register_services",
    "remove": "custom_components.homeclaw.services.async_remove_services",
}
WS_PATCH = "custom_components.homeclaw.websocket_api.async_register_websocket_commands"
PANEL_PATCHES = {
    "register": "homeassistant.components.frontend.async_register_built_in_panel",
    "remove": "homeassistant.components.frontend.async_remove_panel",
}
STATIC_PATH_PATCH = "homeassistant.components.http.StaticPathConfig"


def make_entry(entry_id: str = "entry_1") -> MagicMock:
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {"ai_provider": "openai", "rag_enabled": False}
    entry.options = {}
    return entry


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance with DOMAIN data."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"agents": {}}}
    hass.bus = MagicMock()
    hass.config = MagicMock()
    hass.config.path = MagicMock(
        return_value="/config/custom_components/homeclaw/frontend"
    )
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()
    return hass


def _all_subsystem_patches() -> dict[str, str]:
    """Return a dict of all patch targets for a full lifecycle run."""
    targets: dict[str, str] = {}
    targets.update(PROACTIVE_PATCHES)
    targets.update(CHANNEL_PATCHES)
    targets["rag"] = RAG_PATCH
    targets.update({f"svc_{k}": v for k, v in SVC_PATCHES.items()})
    targets["ws"] = WS_PATCH
    targets.update({f"panel_{k}": v for k, v in PANEL_PATCHES.items()})
    targets["static_path"] = STATIC_PATH_PATCH
    return targets


def patch_all_subsystems() -> tuple[dict, dict]:
    """Start patches for every subsystem import.

    Returns:
        Tuple of (patchers dict, mocks dict) keyed by short name.
    """
    targets = _all_subsystem_patches()
    patchers: dict = {}
    mocks: dict = {}
    for name, target in targets.items():
        p = patch(target)
        patchers[name] = p
        mocks[name] = p.start()

    # Wire up async methods on the mocks that lifecycle calls
    for svc_name in ("heartbeat", "scheduler"):
        m = mocks[svc_name].return_value
        m.async_initialize = AsyncMock()
        m.async_start = AsyncMock()
        m.async_stop = AsyncMock()

    # Channel manager
    mocks["channel_mgr"].return_value.async_setup = AsyncMock()
    mocks["channel_mgr"].return_value.async_teardown = AsyncMock()
    mocks["channel_mgr"].return_value.active_channels = []

    # build_channel_runtime_config must be an AsyncMock
    patchers["build_cfg"].stop()
    patchers["build_cfg"] = patch(
        CHANNEL_PATCHES["build_cfg"], new_callable=AsyncMock, return_value={}
    )
    mocks["build_cfg"] = patchers["build_cfg"].start()

    # RAG manager
    mocks["rag"].return_value.async_initialize = AsyncMock()
    mocks["rag"].return_value.async_shutdown = AsyncMock()

    # Services — must be AsyncMock
    patchers["svc_register"].stop()
    patchers["svc_register"] = patch(SVC_PATCHES["register"], new_callable=AsyncMock)
    mocks["svc_register"] = patchers["svc_register"].start()

    patchers["svc_remove"].stop()
    patchers["svc_remove"] = patch(SVC_PATCHES["remove"], new_callable=AsyncMock)
    mocks["svc_remove"] = patchers["svc_remove"].start()

    return patchers, mocks


def stop_all_patches(patchers: dict) -> None:
    """Stop all active patchers."""
    for p in patchers.values():
        p.stop()
