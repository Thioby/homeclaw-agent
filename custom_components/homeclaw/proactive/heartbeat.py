"""Proactive heartbeat service for Homeclaw.

Periodically "wakes" the AI agent to check smart-home state,
detect anomalies, and store observations.  Inspired by PicoClaw's
HeartbeatService and OpenClaw's HEARTBEAT.md bootstrap pattern.

The heartbeat runs via HA's ``async_track_time_interval`` and delivers
results through three channels:
1. ``hass.bus.async_fire("homeclaw_proactive_alert")`` for frontend toasts
2. ``persistent_notification.create`` for critical alerts
3. A dedicated "Proactive Monitor" session in chat history
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Storage ---
HEARTBEAT_STORAGE_KEY = f"{DOMAIN}_heartbeat"
HEARTBEAT_STORAGE_VERSION = 1

# --- Defaults ---
DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_ENABLED = False
DEFAULT_THROTTLE_IF_ACTIVE_MINUTES = 5
DEFAULT_MAX_ALERTS_PER_HOUR = 5
DEFAULT_MONITORED_DOMAINS = [
    "sensor",
    "binary_sensor",
    "light",
    "lock",
    "alarm_control_panel",
    "climate",
    "cover",
]

# --- Events ---
EVENT_PROACTIVE_ALERT = f"{DOMAIN}_proactive_alert"
EVENT_HEARTBEAT_COMPLETE = f"{DOMAIN}_heartbeat_complete"

# Tools that the heartbeat is NOT allowed to use (read-only context)
HEARTBEAT_DENIED_TOOLS = frozenset(
    {
        "call_service",
        "set_entity_state",
        "create_automation",
        "create_dashboard",
        "update_dashboard",
        "scheduler",
        "subagent_spawn",
        "subagent_status",
        "memory_store",
        "memory_forget",
        "identity_set",
    }
)

# Maximum entities to include in the heartbeat prompt snapshot
MAX_ENTITIES_IN_SNAPSHOT = 100

# Maximum alerts to keep in history
MAX_ALERT_HISTORY = 200


@dataclass
class HeartbeatConfig:
    """Configuration for the heartbeat service."""

    enabled: bool = DEFAULT_ENABLED
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES
    throttle_if_active_minutes: int = DEFAULT_THROTTLE_IF_ACTIVE_MINUTES
    max_alerts_per_hour: int = DEFAULT_MAX_ALERTS_PER_HOUR
    monitored_domains: list[str] = field(
        default_factory=lambda: list(DEFAULT_MONITORED_DOMAINS)
    )


@dataclass
class HeartbeatAlert:
    """A single proactive alert."""

    severity: str  # "warning" | "critical"
    entity_id: str
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class HeartbeatResult:
    """Result of a single heartbeat run."""

    timestamp: float
    alerts: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    all_clear: bool = True
    error: str | None = None
    duration_ms: int = 0


class HeartbeatService:
    """Proactive heartbeat — periodically checks smart-home state via AI.

    Lifecycle:
        1. ``async_initialize()`` — loads config from HA Store.
        2. ``async_start()`` — registers ``async_track_time_interval``,
           deferred via ``async_at_started`` so all integrations are loaded.
        3. ``async_stop()`` — cancels the interval.

    The heartbeat callback:
        - Builds a snapshot of monitored entity states.
        - Sends it to the first available AI provider with a special prompt.
        - Parses the JSON response for alerts / observations.
        - Dispatches alerts through HA events and persistent notifications.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._config = HeartbeatConfig()
        self._store = Store[dict[str, Any]](
            hass, HEARTBEAT_STORAGE_VERSION, HEARTBEAT_STORAGE_KEY
        )
        self._cancel_interval: CALLBACK_TYPE | None = None
        self._alert_history: list[dict[str, Any]] = []
        self._result_history: list[dict[str, Any]] = []
        self._last_run: float | None = None
        self._alerts_this_hour: int = 0
        self._alerts_hour_start: float = 0.0
        self._initialized = False

    # === Lifecycle ===

    async def async_initialize(self) -> None:
        """Load persisted config and alert history."""
        data = await self._store.async_load()
        if data:
            cfg = data.get("config", {})
            self._config = HeartbeatConfig(
                enabled=cfg.get("enabled", DEFAULT_ENABLED),
                interval_minutes=cfg.get("interval_minutes", DEFAULT_INTERVAL_MINUTES),
                throttle_if_active_minutes=cfg.get(
                    "throttle_if_active_minutes", DEFAULT_THROTTLE_IF_ACTIVE_MINUTES
                ),
                max_alerts_per_hour=cfg.get(
                    "max_alerts_per_hour", DEFAULT_MAX_ALERTS_PER_HOUR
                ),
                monitored_domains=cfg.get(
                    "monitored_domains", list(DEFAULT_MONITORED_DOMAINS)
                ),
            )
            self._alert_history = data.get("alert_history", [])[-MAX_ALERT_HISTORY:]
            self._result_history = data.get("result_history", [])[-50:]
        self._initialized = True
        _LOGGER.info(
            "Heartbeat service initialized (enabled=%s, interval=%dm)",
            self._config.enabled,
            self._config.interval_minutes,
        )

    async def async_start(self) -> None:
        """Start the heartbeat interval, deferred until HA is fully started."""
        if not self._initialized:
            await self.async_initialize()

        if not self._config.enabled:
            _LOGGER.debug("Heartbeat disabled, not starting interval")
            return

        async def _deferred_start(_hass: HomeAssistant) -> None:
            self._register_interval()

        async_at_started(self._hass, _deferred_start)

    async def async_stop(self) -> None:
        """Cancel the heartbeat interval and persist state."""
        if self._cancel_interval:
            self._cancel_interval()
            self._cancel_interval = None
            _LOGGER.info("Heartbeat interval cancelled")
        await self._async_save()

    # === Configuration ===

    def get_config(self) -> dict[str, Any]:
        """Return current config as dict."""
        return asdict(self._config)

    async def async_update_config(self, **kwargs: Any) -> dict[str, Any]:
        """Update configuration and restart interval if needed.

        Args:
            **kwargs: Config fields to update (enabled, interval_minutes, etc.)

        Returns:
            Updated config dict.
        """
        restart_needed = False

        if "enabled" in kwargs:
            new_enabled = bool(kwargs["enabled"])
            if new_enabled != self._config.enabled:
                self._config.enabled = new_enabled
                restart_needed = True

        if "interval_minutes" in kwargs:
            new_interval = max(5, min(1440, int(kwargs["interval_minutes"])))
            if new_interval != self._config.interval_minutes:
                self._config.interval_minutes = new_interval
                restart_needed = True

        if "throttle_if_active_minutes" in kwargs:
            self._config.throttle_if_active_minutes = max(
                0, int(kwargs["throttle_if_active_minutes"])
            )

        if "max_alerts_per_hour" in kwargs:
            self._config.max_alerts_per_hour = max(
                1, int(kwargs["max_alerts_per_hour"])
            )

        if "monitored_domains" in kwargs:
            domains = kwargs["monitored_domains"]
            if isinstance(domains, list):
                self._config.monitored_domains = domains

        await self._async_save()

        if restart_needed:
            # Cancel existing interval
            if self._cancel_interval:
                self._cancel_interval()
                self._cancel_interval = None
            # Re-register if enabled
            if self._config.enabled:
                self._register_interval()
            _LOGGER.info(
                "Heartbeat config updated (enabled=%s, interval=%dm)",
                self._config.enabled,
                self._config.interval_minutes,
            )

        return self.get_config()

    def get_alert_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent alert history."""
        return self._alert_history[-limit:]

    def get_result_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent heartbeat run results."""
        return self._result_history[-limit:]

    # === Core Heartbeat Logic ===

    async def async_run_heartbeat(self) -> HeartbeatResult:
        """Run a single heartbeat check (can be called manually via service).

        Returns:
            HeartbeatResult with alerts and observations.
        """
        start_time = time.monotonic()
        result = HeartbeatResult(timestamp=time.time())

        try:
            # 1. Get an agent
            agent = self._get_agent()
            if not agent:
                result.error = "No AI agent available"
                _LOGGER.warning("Heartbeat: no agent available")
                return result

            # 2. Build entity state snapshot
            snapshot = self._build_entity_snapshot()
            if not snapshot:
                result.error = "No monitored entities found"
                _LOGGER.debug("Heartbeat: no entities to monitor")
                return result

            # 3. Build heartbeat prompt
            from ..prompts import HEARTBEAT_SYSTEM_PROMPT

            prompt = self._build_heartbeat_prompt(snapshot)

            # 4. Call agent with read-only tools (denied_tools blocks all writes)
            agent_result = await agent.process_query(
                user_query=prompt,
                conversation_history=[],  # Clean history — no carry-over
                denied_tools=HEARTBEAT_DENIED_TOOLS,
                system_prompt=HEARTBEAT_SYSTEM_PROMPT,
            )

            # 5. Parse response
            response_text = agent_result.get("answer", "") or agent_result.get(
                "response", ""
            )
            parsed = self._parse_heartbeat_response(response_text)

            result.alerts = parsed.get("alerts", [])
            result.observations = parsed.get("observations", [])
            result.all_clear = parsed.get("all_clear", True)

            # 6. Dispatch alerts
            await self._dispatch_alerts(result)

            # 7. Store observations in memory (if RAG/memory available)
            await self._store_observations(result)

        except Exception as e:
            result.error = str(e)
            _LOGGER.error("Heartbeat check failed: %s", e)

        result.duration_ms = int((time.monotonic() - start_time) * 1000)
        self._last_run = result.timestamp

        # Store in history
        self._result_history.append(asdict(result))
        if len(self._result_history) > 50:
            self._result_history = self._result_history[-50:]

        # Fire completion event
        self._hass.bus.async_fire(
            EVENT_HEARTBEAT_COMPLETE,
            {
                "timestamp": result.timestamp,
                "alert_count": len(result.alerts),
                "all_clear": result.all_clear,
                "duration_ms": result.duration_ms,
                "error": result.error,
            },
        )

        # Persist
        await self._async_save()

        _LOGGER.info(
            "Heartbeat complete: %d alerts, %d observations, %dms (all_clear=%s)",
            len(result.alerts),
            len(result.observations),
            result.duration_ms,
            result.all_clear,
        )
        return result

    # === Internal Helpers ===

    def _register_interval(self) -> None:
        """Register the periodic heartbeat interval."""
        if self._cancel_interval:
            self._cancel_interval()

        interval = timedelta(minutes=self._config.interval_minutes)
        self._cancel_interval = async_track_time_interval(
            self._hass,
            self._heartbeat_tick,
            interval,
            name=f"{DOMAIN}_heartbeat",
            cancel_on_shutdown=True,
        )
        _LOGGER.info(
            "Heartbeat interval registered: every %d minutes",
            self._config.interval_minutes,
        )

    async def _heartbeat_tick(self, now: datetime) -> None:
        """Called by async_track_time_interval on each tick."""
        # Throttle if user was recently active
        if self._should_throttle():
            _LOGGER.debug("Heartbeat throttled — user recently active")
            return

        await self.async_run_heartbeat()

    def _should_throttle(self) -> bool:
        """Check if heartbeat should be skipped (user recently active)."""
        if self._config.throttle_if_active_minutes <= 0:
            return False

        # Check last activity from session storage
        domain_data = self._hass.data.get(DOMAIN, {})
        last_activity = domain_data.get("_last_user_activity")
        if last_activity is None:
            return False

        elapsed = time.time() - last_activity
        return elapsed < (self._config.throttle_if_active_minutes * 60)

    def _get_agent(self) -> Any:
        """Get the first available AI agent."""
        domain_data = self._hass.data.get(DOMAIN, {})
        agents = domain_data.get("agents", {})
        if not agents:
            return None
        # Return the first available agent
        return next(iter(agents.values()), None)

    def _build_entity_snapshot(self) -> str:
        """Build a text snapshot of monitored entity states."""
        lines: list[str] = []
        count = 0

        for domain in self._config.monitored_domains:
            states = self._hass.states.async_all(domain)
            for state in states:
                if count >= MAX_ENTITIES_IN_SNAPSHOT:
                    lines.append(
                        f"... and more (truncated at {MAX_ENTITIES_IN_SNAPSHOT})"
                    )
                    return "\n".join(lines)

                entity_id = state.entity_id
                state_val = state.state
                friendly_name = state.attributes.get("friendly_name", entity_id)
                unit = state.attributes.get("unit_of_measurement", "")

                if state_val in ("unavailable", "unknown"):
                    lines.append(f"- {friendly_name} ({entity_id}): {state_val}")
                elif unit:
                    lines.append(f"- {friendly_name} ({entity_id}): {state_val} {unit}")
                else:
                    lines.append(f"- {friendly_name} ({entity_id}): {state_val}")
                count += 1

        return "\n".join(lines) if lines else ""

    def _build_heartbeat_prompt(self, snapshot: str) -> str:
        """Build the heartbeat query prompt with entity snapshot."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        return (
            f"Current time: {now_str}\n\n"
            f"## Entity States ({len(snapshot.splitlines())} entities)\n\n"
            f"{snapshot}"
        )

    def _parse_heartbeat_response(self, response_text: str) -> dict[str, Any]:
        """Parse the AI response — expects JSON with alerts/observations."""
        # Try to extract JSON from response
        text = response_text.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: try to find JSON in the response
        import re

        json_match = re.search(r"\{[^{}]*\"alerts\"[^{}]*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Could not parse — treat entire response as observation
        if text:
            return {
                "alerts": [],
                "observations": [{"message": text, "worth_remembering": False}],
                "all_clear": True,
            }
        return {"alerts": [], "observations": [], "all_clear": True}

    async def _dispatch_alerts(self, result: HeartbeatResult) -> None:
        """Send alerts through HA events and persistent notifications."""
        now = time.time()

        # Rate limiting: reset counter every hour
        if now - self._alerts_hour_start > 3600:
            self._alerts_this_hour = 0
            self._alerts_hour_start = now

        for alert_data in result.alerts:
            if self._alerts_this_hour >= self._config.max_alerts_per_hour:
                _LOGGER.warning(
                    "Alert rate limit reached (%d/hour), suppressing",
                    self._config.max_alerts_per_hour,
                )
                break

            alert = {
                "severity": alert_data.get("severity", "warning"),
                "entity_id": alert_data.get("entity_id", ""),
                "message": alert_data.get("message", ""),
                "timestamp": now,
            }

            # Fire HA event (for frontend toasts)
            self._hass.bus.async_fire(EVENT_PROACTIVE_ALERT, alert)

            # Store in history
            self._alert_history.append(alert)
            if len(self._alert_history) > MAX_ALERT_HISTORY:
                self._alert_history = self._alert_history[-MAX_ALERT_HISTORY:]

            self._alerts_this_hour += 1

            # Critical alerts also create persistent notifications
            if alert["severity"] == "critical":
                await self._hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": f"Homeclaw Alert: {alert.get('entity_id', 'System')}",
                        "message": alert["message"],
                        "notification_id": f"homeclaw_alert_{int(now)}",
                    },
                )

    async def _store_observations(self, result: HeartbeatResult) -> None:
        """Store noteworthy observations in long-term memory."""
        rag_manager = self._hass.data.get(DOMAIN, {}).get("rag_manager")
        if not rag_manager or not rag_manager.is_initialized:
            return

        mem_mgr = getattr(rag_manager, "_memory_manager", None)
        if not mem_mgr:
            return

        for obs in result.observations:
            if obs.get("worth_remembering"):
                try:
                    await mem_mgr.store_memory(
                        text=obs["message"],
                        user_id="system",
                        category="observation",
                        importance=0.6,
                        source="heartbeat",
                    )
                except Exception as e:
                    _LOGGER.debug("Failed to store heartbeat observation: %s", e)

    async def _async_save(self) -> None:
        """Persist config and alert history to HA Store."""
        await self._store.async_save(
            {
                "config": asdict(self._config),
                "alert_history": self._alert_history[-MAX_ALERT_HISTORY:],
                "result_history": self._result_history[-50:],
            }
        )
