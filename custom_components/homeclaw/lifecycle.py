"""Exactly-once lifecycle manager for global Homeclaw subsystems.

A single ``asyncio.Lock`` guarantees mutual exclusion between concurrent
``async_setup_entry`` calls and between init/shutdown.

Init order: proactive → channels → rag → services → websocket → frontend.
Shutdown is the reverse.  Each subsystem is independent — a failure in one
does not prevent others from starting or stopping.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from .const import CONF_RAG_ENABLED, DEFAULT_RAG_ENABLED, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
_StopFn = Callable[[], Coroutine[Any, Any, None]]


class SubsystemLifecycle:
    """Exactly-once lifecycle manager for global Homeclaw subsystems.

    Guarantees:
    - Init runs exactly once, even under concurrent async_setup_entry calls
    - Shutdown runs only when the last config entry is unloaded
    - Partial init failure triggers rollback of already-started subsystems
    - Init and shutdown are mutually exclusive (same lock)
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._entry_ids: set[str] = set()
        self._initialized: bool = False
        self._first_entry: Any | None = None
        self._heartbeat: Any | None = None
        self._scheduler: Any | None = None
        self._subagent_mgr: Any | None = None
        self._channel_mgr: Any | None = None
        self._rag_mgr: Any | None = None

    async def async_setup_entry(self, hass: HomeAssistant, entry: ConfigEntry, config_data: dict[str, Any]) -> None:
        """Register *entry* and start global subsystems on first call."""
        async with self._lock:
            self._entry_ids.add(entry.entry_id)
            if self._initialized:
                _LOGGER.debug("Subsystems already running, entry %s ref-counted", entry.entry_id)
                return
            self._first_entry = entry
            try:
                await self._start_all(hass, entry, config_data)
                self._initialized = True
                _LOGGER.info("Global subsystems initialized (first entry: %s)", entry.entry_id)
            except Exception:
                _LOGGER.warning("Global subsystem init failed — degraded mode", exc_info=True)

    async def async_unload_entry(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Unregister *entry*; tear down subsystems when the last entry leaves."""
        async with self._lock:
            self._entry_ids.discard(entry.entry_id)
            if self._entry_ids:
                _LOGGER.debug("Entry %s unloaded, %d remain", entry.entry_id, len(self._entry_ids))
                return
            await self._stop_all(hass)
            self._initialized = False
            self._first_entry = None
            _LOGGER.info("All entries unloaded — global subsystems shut down")

    def get_subsystem(self, name: str) -> Any | None:
        """Return a subsystem reference by name (e.g. ``scheduler``, ``rag_manager``)."""
        return {
            "heartbeat": self._heartbeat,
            "scheduler": self._scheduler,
            "subagent_manager": self._subagent_mgr,
            "channel_manager": self._channel_mgr,
            "rag_manager": self._rag_mgr,
        }.get(name)

    # -- ordered init --------------------------------------------------

    async def _start_all(self, hass: HomeAssistant, entry: ConfigEntry, config_data: dict[str, Any]) -> None:
        """Start subsystems in order.  Each group is independent."""
        await self._start_proactive(hass)
        await self._start_channels(hass, entry)
        await self._start_rag(hass, config_data, entry)
        await self._start_services(hass)
        await self._start_websocket(hass)
        await self._start_frontend(hass)

    async def _start_proactive(self, hass: HomeAssistant) -> None:
        """Start heartbeat, scheduler, and subagent manager."""
        started: list[tuple[str, _StopFn]] = []
        try:
            from .core.subagent import SubagentManager
            from .proactive import HeartbeatService, SchedulerService

            heartbeat = HeartbeatService(hass)
            await heartbeat.async_initialize()
            await heartbeat.async_start()
            self._heartbeat = heartbeat
            hass.data[DOMAIN]["heartbeat"] = heartbeat
            started.append(("heartbeat", heartbeat.async_stop))

            scheduler = SchedulerService(hass)
            await scheduler.async_initialize()
            await scheduler.async_start()
            self._scheduler = scheduler
            hass.data[DOMAIN]["scheduler"] = scheduler
            started.append(("scheduler", scheduler.async_stop))

            subagent_manager = SubagentManager(hass)
            self._subagent_mgr = subagent_manager
            hass.data[DOMAIN]["subagent_manager"] = subagent_manager
            _LOGGER.info("Proactive subsystem started")
        except Exception:
            _LOGGER.warning("Proactive subsystem failed — rolling back", exc_info=True)
            await self._rollback(hass, started)
            self._heartbeat = self._scheduler = self._subagent_mgr = None
            for key in ("heartbeat", "scheduler", "subagent_manager"):
                hass.data[DOMAIN].pop(key, None)

    async def _start_channels(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Start the channel manager with all enabled channels."""
        try:
            from .channels.config import build_channel_runtime_config
            from .channels.intake import MessageIntake
            from .channels.manager import ChannelManager

            intake = MessageIntake(hass)
            manager = ChannelManager(hass, intake)
            channel_config = await build_channel_runtime_config(hass, {**entry.data, **entry.options})
            await manager.async_setup(channel_config)
            self._channel_mgr = manager
            hass.data[DOMAIN]["channel_manager"] = manager
            _LOGGER.info("Channel manager started (active: %s)", manager.active_channels)
        except Exception:
            _LOGGER.warning("Channel subsystem failed", exc_info=True)

    async def _start_rag(self, hass: HomeAssistant, config_data: dict[str, Any], entry: ConfigEntry) -> None:
        """Start the RAG manager if enabled in config."""
        if not config_data.get(CONF_RAG_ENABLED, DEFAULT_RAG_ENABLED):
            _LOGGER.debug("RAG not enabled, skipping")
            return
        try:
            from .rag import RAGManager

            rag_manager = RAGManager(hass, config_data, entry)
            await rag_manager.async_initialize()
            self._rag_mgr = rag_manager
            hass.data[DOMAIN]["rag_manager"] = rag_manager
            for agent in hass.data[DOMAIN].get("agents", {}).values():
                agent.set_rag_manager(rag_manager)
            _LOGGER.info("RAG manager started and connected to agents")
        except Exception:
            _LOGGER.warning("RAG subsystem failed", exc_info=True)

    async def _start_services(self, hass: HomeAssistant) -> None:
        """Register HA services."""
        try:
            from .services import async_register_services

            await async_register_services(hass)
        except Exception:
            _LOGGER.warning("Service registration failed", exc_info=True)

    async def _start_websocket(self, hass: HomeAssistant) -> None:
        """Register WebSocket commands (idempotent)."""
        try:
            from .websocket_api import async_register_websocket_commands

            async_register_websocket_commands(hass)
        except Exception:
            _LOGGER.warning("WebSocket registration failed", exc_info=True)

    async def _start_frontend(self, hass: HomeAssistant) -> None:
        """Register the static path and sidebar panel."""
        try:
            from homeassistant.components.frontend import async_register_built_in_panel
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        "/frontend/homeclaw",
                        hass.config.path("custom_components/homeclaw/frontend"),
                        False,
                    )
                ]
            )
            async_register_built_in_panel(
                hass,
                component_name="custom",
                sidebar_title="Homeclaw",
                sidebar_icon="mdi:robot",
                frontend_url_path="homeclaw",
                require_admin=False,
                config={
                    "_panel_custom": {
                        "name": "homeclaw-panel",
                        "module_url": "/frontend/homeclaw/homeclaw-panel.js",
                        "embed_iframe": False,
                    }
                },
            )
        except Exception:
            _LOGGER.warning("Frontend panel registration failed", exc_info=True)

    # -- ordered shutdown (reverse of init) ----------------------------

    async def _stop_all(self, hass: HomeAssistant) -> None:
        """Stop subsystems in reverse order.  Each step is best-effort."""
        await self._stop_frontend(hass)
        await self._stop_services(hass)
        await self._stop_rag(hass)
        await self._stop_channels(hass)
        await self._stop_proactive(hass)
        self._cleanup_storage_cache(hass)

    async def _stop_frontend(self, hass: HomeAssistant) -> None:
        """Remove the sidebar panel."""
        try:
            from homeassistant.components.frontend import async_remove_panel

            async_remove_panel(hass, "homeclaw")
        except Exception:
            _LOGGER.debug("Panel removal skipped or failed", exc_info=True)

    async def _stop_services(self, hass: HomeAssistant) -> None:
        """Remove registered HA services."""
        try:
            from .services import async_remove_services

            await async_remove_services(hass)
        except Exception:
            _LOGGER.warning("Service removal failed", exc_info=True)

    async def _stop_rag(self, hass: HomeAssistant) -> None:
        """Shut down the RAG manager."""
        if not self._rag_mgr:
            return
        try:
            await self._rag_mgr.async_shutdown()
        except Exception:
            _LOGGER.warning("RAG shutdown error", exc_info=True)
        finally:
            hass.data[DOMAIN].pop("rag_manager", None)
            self._rag_mgr = None

    async def _stop_channels(self, hass: HomeAssistant) -> None:
        """Tear down the channel manager."""
        if not self._channel_mgr:
            return
        try:
            await self._channel_mgr.async_teardown()
        except Exception:
            _LOGGER.warning("Channel shutdown error", exc_info=True)
        finally:
            hass.data[DOMAIN].pop("channel_manager", None)
            self._channel_mgr = None

    async def _stop_proactive(self, hass: HomeAssistant) -> None:
        """Stop heartbeat, scheduler, and clean up subagent manager."""
        for attr, key in (("_heartbeat", "heartbeat"), ("_scheduler", "scheduler")):
            svc = getattr(self, attr)
            if svc:
                try:
                    await svc.async_stop()
                except Exception:
                    _LOGGER.warning("%s stop error", key, exc_info=True)
                finally:
                    hass.data[DOMAIN].pop(key, None)
                    setattr(self, attr, None)
        hass.data[DOMAIN].pop("subagent_manager", None)
        self._subagent_mgr = None

    def _cleanup_storage_cache(self, hass: HomeAssistant) -> None:
        """Remove cached storage instances from hass.data."""
        prefix = f"{DOMAIN}_storage_"
        keys = [k for k in list(hass.data.keys()) if isinstance(k, str) and k.startswith(prefix)]
        for key in keys:
            hass.data.pop(key, None)

    # -- rollback helper -----------------------------------------------

    async def _rollback(self, hass: HomeAssistant, started: list[tuple[str, _StopFn]]) -> None:
        """Best-effort rollback of already-started subsystems (reverse order)."""
        for name, stop_fn in reversed(started):
            try:
                await stop_fn()
                _LOGGER.debug("Rolled back %s", name)
            except Exception:
                _LOGGER.warning("Rollback of %s failed", name, exc_info=True)
