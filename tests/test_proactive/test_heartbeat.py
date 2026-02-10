"""Tests for HeartbeatService."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.proactive.heartbeat import (
    DEFAULT_ENABLED,
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_MAX_ALERTS_PER_HOUR,
    DEFAULT_MONITORED_DOMAINS,
    DEFAULT_THROTTLE_IF_ACTIVE_MINUTES,
    EVENT_HEARTBEAT_COMPLETE,
    EVENT_PROACTIVE_ALERT,
    HEARTBEAT_DENIED_TOOLS,
    HeartbeatConfig,
    HeartbeatResult,
    HeartbeatService,
    MAX_ENTITIES_IN_SNAPSHOT,
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
    """Create a mock HomeAssistant instance with config dir."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"agents": {}, "_last_user_activity": None}}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states = MagicMock()
    hass.states.async_all = MagicMock(return_value=[])
    return hass


def _make_service(mock_hass, mock_store):
    """Create HeartbeatService with mock store injected."""
    with patch("custom_components.homeclaw.proactive.heartbeat.Store"):
        service = HeartbeatService(mock_hass)
    service._store = mock_store
    return service


class TestHeartbeatConfig:
    """Tests for HeartbeatConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HeartbeatConfig()
        assert config.enabled is DEFAULT_ENABLED
        assert config.interval_minutes == DEFAULT_INTERVAL_MINUTES
        assert config.throttle_if_active_minutes == DEFAULT_THROTTLE_IF_ACTIVE_MINUTES
        assert config.max_alerts_per_hour == DEFAULT_MAX_ALERTS_PER_HOUR
        assert config.monitored_domains == list(DEFAULT_MONITORED_DOMAINS)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HeartbeatConfig(
            enabled=True,
            interval_minutes=30,
            throttle_if_active_minutes=10,
            max_alerts_per_hour=3,
            monitored_domains=["sensor", "light"],
        )
        assert config.enabled is True
        assert config.interval_minutes == 30
        assert config.monitored_domains == ["sensor", "light"]


class TestHeartbeatResult:
    """Tests for HeartbeatResult dataclass."""

    def test_default_values(self):
        """Test default result values."""
        result = HeartbeatResult(timestamp=time.time())
        assert result.alerts == []
        assert result.observations == []
        assert result.all_clear is True
        assert result.error is None
        assert result.duration_ms == 0

    def test_result_with_data(self):
        """Test result with alerts and observations."""
        result = HeartbeatResult(
            timestamp=time.time(),
            alerts=[
                {
                    "severity": "warning",
                    "entity_id": "light.kitchen",
                    "message": "Left on",
                }
            ],
            observations=[{"message": "Warm today", "worth_remembering": True}],
            all_clear=False,
            duration_ms=250,
        )
        assert len(result.alerts) == 1
        assert result.all_clear is False
        assert result.duration_ms == 250


class TestHeartbeatServiceInit:
    """Tests for HeartbeatService initialization."""

    @pytest.mark.asyncio
    async def test_initialize_no_stored_data(self, mock_hass, mock_store):
        """Test initialization with no stored data."""
        service = _make_service(mock_hass, mock_store)

        await service.async_initialize()

        assert service._initialized is True
        assert service._config.enabled is DEFAULT_ENABLED
        assert service._alert_history == []

    @pytest.mark.asyncio
    async def test_initialize_with_stored_data(self, mock_hass, mock_store):
        """Test initialization loads stored config."""
        mock_store.async_load.return_value = {
            "config": {
                "enabled": True,
                "interval_minutes": 30,
                "throttle_if_active_minutes": 10,
                "max_alerts_per_hour": 3,
                "monitored_domains": ["sensor", "binary_sensor"],
            },
            "alert_history": [
                {"severity": "warning", "entity_id": "light.test", "message": "test"}
            ],
            "result_history": [{"timestamp": 1234, "all_clear": True}],
        }

        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        assert service._config.enabled is True
        assert service._config.interval_minutes == 30
        assert len(service._alert_history) == 1
        assert len(service._result_history) == 1


class TestHeartbeatServiceConfig:
    """Tests for HeartbeatService configuration management."""

    @pytest.mark.asyncio
    async def test_get_config(self, mock_hass, mock_store):
        """Test getting current config."""
        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        config = service.get_config()
        assert isinstance(config, dict)
        assert "enabled" in config
        assert "interval_minutes" in config
        assert "monitored_domains" in config

    @pytest.mark.asyncio
    async def test_update_config_enabled(self, mock_hass, mock_store):
        """Test enabling the heartbeat."""
        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        with patch.object(service, "_register_interval"):
            updated = await service.async_update_config(enabled=True)

        assert updated["enabled"] is True

    @pytest.mark.asyncio
    async def test_update_config_interval_clamped(self, mock_hass, mock_store):
        """Test interval is clamped to min/max."""
        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        with patch.object(service, "_register_interval"):
            # Below minimum (5)
            updated = await service.async_update_config(interval_minutes=2)
            assert updated["interval_minutes"] == 5

            # Above maximum (1440)
            updated = await service.async_update_config(interval_minutes=2000)
            assert updated["interval_minutes"] == 1440

    @pytest.mark.asyncio
    async def test_update_config_monitored_domains(self, mock_hass, mock_store):
        """Test updating monitored domains."""
        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        updated = await service.async_update_config(
            monitored_domains=["sensor", "lock"]
        )
        assert updated["monitored_domains"] == ["sensor", "lock"]


class TestHeartbeatEntitySnapshot:
    """Tests for entity state snapshot building."""

    def test_build_snapshot_empty(self, mock_hass, mock_store):
        """Test snapshot with no entities."""
        service = _make_service(mock_hass, mock_store)
        snapshot = service._build_entity_snapshot()
        assert snapshot == ""

    def test_build_snapshot_with_entities(self, mock_hass, mock_store):
        """Test snapshot with various entity states."""
        mock_state_1 = MagicMock()
        mock_state_1.entity_id = "sensor.temperature"
        mock_state_1.state = "22.5"
        mock_state_1.attributes = {
            "friendly_name": "Temperature",
            "unit_of_measurement": "°C",
        }

        mock_state_2 = MagicMock()
        mock_state_2.entity_id = "light.kitchen"
        mock_state_2.state = "on"
        mock_state_2.attributes = {"friendly_name": "Kitchen Light"}

        mock_state_3 = MagicMock()
        mock_state_3.entity_id = "sensor.broken"
        mock_state_3.state = "unavailable"
        mock_state_3.attributes = {"friendly_name": "Broken Sensor"}

        def mock_async_all(domain):
            return {
                "sensor": [mock_state_1, mock_state_3],
                "light": [mock_state_2],
            }.get(domain, [])

        mock_hass.states.async_all = mock_async_all

        service = _make_service(mock_hass, mock_store)
        service._config.monitored_domains = ["sensor", "light"]
        snapshot = service._build_entity_snapshot()

        assert "Temperature (sensor.temperature): 22.5 °C" in snapshot
        assert "Kitchen Light (light.kitchen): on" in snapshot
        assert "Broken Sensor (sensor.broken): unavailable" in snapshot

    def test_build_snapshot_truncation(self, mock_hass, mock_store):
        """Test snapshot truncates at MAX_ENTITIES_IN_SNAPSHOT."""
        states = []
        for i in range(MAX_ENTITIES_IN_SNAPSHOT + 10):
            s = MagicMock()
            s.entity_id = f"sensor.test_{i}"
            s.state = str(i)
            s.attributes = {"friendly_name": f"Test {i}"}
            states.append(s)

        mock_hass.states.async_all = MagicMock(return_value=states)

        service = _make_service(mock_hass, mock_store)
        service._config.monitored_domains = ["sensor"]
        snapshot = service._build_entity_snapshot()

        assert "truncated" in snapshot


class TestHeartbeatResponseParsing:
    """Tests for heartbeat response parsing."""

    def test_parse_valid_json(self, mock_hass, mock_store):
        """Test parsing a valid JSON response."""
        service = _make_service(mock_hass, mock_store)

        response = json.dumps(
            {
                "alerts": [
                    {
                        "severity": "warning",
                        "entity_id": "light.kitchen",
                        "message": "Left on",
                    }
                ],
                "observations": [{"message": "All good", "worth_remembering": False}],
                "all_clear": False,
            }
        )

        parsed = service._parse_heartbeat_response(response)
        assert len(parsed["alerts"]) == 1
        assert parsed["all_clear"] is False

    def test_parse_json_in_code_block(self, mock_hass, mock_store):
        """Test parsing JSON wrapped in markdown code block."""
        service = _make_service(mock_hass, mock_store)

        response = '```json\n{"alerts": [], "observations": [], "all_clear": true}\n```'
        parsed = service._parse_heartbeat_response(response)
        assert parsed["all_clear"] is True
        assert parsed["alerts"] == []

    def test_parse_invalid_json(self, mock_hass, mock_store):
        """Test parsing invalid/non-JSON response."""
        service = _make_service(mock_hass, mock_store)

        response = "Everything looks fine, no issues detected."
        parsed = service._parse_heartbeat_response(response)
        assert parsed["all_clear"] is True
        assert len(parsed["observations"]) == 1

    def test_parse_empty_response(self, mock_hass, mock_store):
        """Test parsing empty response."""
        service = _make_service(mock_hass, mock_store)

        parsed = service._parse_heartbeat_response("")
        assert parsed["all_clear"] is True
        assert parsed["alerts"] == []


class TestHeartbeatAlertDispatch:
    """Tests for alert dispatching."""

    @pytest.mark.asyncio
    async def test_dispatch_warning_alert(self, mock_hass, mock_store):
        """Test dispatching a warning alert."""
        service = _make_service(mock_hass, mock_store)
        result = HeartbeatResult(
            timestamp=time.time(),
            alerts=[
                {"severity": "warning", "entity_id": "light.test", "message": "Left on"}
            ],
        )

        await service._dispatch_alerts(result)

        mock_hass.bus.async_fire.assert_called()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == EVENT_PROACTIVE_ALERT

    @pytest.mark.asyncio
    async def test_dispatch_critical_alert_creates_notification(
        self, mock_hass, mock_store
    ):
        """Test that critical alerts create persistent notifications."""
        service = _make_service(mock_hass, mock_store)
        result = HeartbeatResult(
            timestamp=time.time(),
            alerts=[
                {
                    "severity": "critical",
                    "entity_id": "lock.front_door",
                    "message": "Open!",
                }
            ],
        )

        await service._dispatch_alerts(result)

        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][0] == "persistent_notification"
        assert call_args[0][1] == "create"

    @pytest.mark.asyncio
    async def test_alert_rate_limiting(self, mock_hass, mock_store):
        """Test that alerts are rate-limited."""
        service = _make_service(mock_hass, mock_store)
        service._config.max_alerts_per_hour = 2
        service._alerts_this_hour = 0
        service._alerts_hour_start = time.time()

        result = HeartbeatResult(
            timestamp=time.time(),
            alerts=[
                {"severity": "warning", "entity_id": f"light.test_{i}", "message": "on"}
                for i in range(3)
            ],
        )

        await service._dispatch_alerts(result)

        # Only 2 events should have been fired (rate limit = 2)
        assert mock_hass.bus.async_fire.call_count == 2


class TestHeartbeatThrottling:
    """Tests for heartbeat throttling."""

    def test_no_throttle_when_no_activity(self, mock_hass, mock_store):
        """Test no throttling when no user activity recorded."""
        service = _make_service(mock_hass, mock_store)
        assert service._should_throttle() is False

    def test_throttle_when_recently_active(self, mock_hass, mock_store):
        """Test throttling when user was recently active."""
        mock_hass.data[DOMAIN]["_last_user_activity"] = time.time() - 60  # 1 min ago
        service = _make_service(mock_hass, mock_store)
        service._config.throttle_if_active_minutes = 5
        assert service._should_throttle() is True

    def test_no_throttle_when_activity_old(self, mock_hass, mock_store):
        """Test no throttling when user activity is old enough."""
        mock_hass.data[DOMAIN]["_last_user_activity"] = time.time() - 600  # 10 min ago
        service = _make_service(mock_hass, mock_store)
        service._config.throttle_if_active_minutes = 5
        assert service._should_throttle() is False

    def test_throttle_disabled(self, mock_hass, mock_store):
        """Test throttling disabled when set to 0."""
        mock_hass.data[DOMAIN]["_last_user_activity"] = time.time()
        service = _make_service(mock_hass, mock_store)
        service._config.throttle_if_active_minutes = 0
        assert service._should_throttle() is False


class TestHeartbeatDeniedTools:
    """Tests for HEARTBEAT_DENIED_TOOLS configuration."""

    def test_all_write_tools_denied(self):
        """Test that all write/mutating tools are blocked for heartbeat."""
        assert "call_service" in HEARTBEAT_DENIED_TOOLS
        assert "set_entity_state" in HEARTBEAT_DENIED_TOOLS
        assert "create_automation" in HEARTBEAT_DENIED_TOOLS
        assert "create_dashboard" in HEARTBEAT_DENIED_TOOLS
        assert "update_dashboard" in HEARTBEAT_DENIED_TOOLS
        assert "scheduler" in HEARTBEAT_DENIED_TOOLS
        assert "subagent_spawn" in HEARTBEAT_DENIED_TOOLS
        assert "subagent_status" in HEARTBEAT_DENIED_TOOLS
        assert "memory_store" in HEARTBEAT_DENIED_TOOLS
        assert "memory_forget" in HEARTBEAT_DENIED_TOOLS
        assert "identity_set" in HEARTBEAT_DENIED_TOOLS

    def test_read_tools_not_denied(self):
        """Test that read-only tools are NOT denied for heartbeat."""
        assert "get_entity_state" not in HEARTBEAT_DENIED_TOOLS
        assert "get_entities_by_domain" not in HEARTBEAT_DENIED_TOOLS
        assert "memory_recall" not in HEARTBEAT_DENIED_TOOLS


class TestHeartbeatRunFull:
    """Tests for full heartbeat run."""

    @pytest.mark.asyncio
    async def test_run_heartbeat_no_agent(self, mock_hass, mock_store):
        """Test heartbeat when no agent available."""
        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        result = await service.async_run_heartbeat()
        assert result.error == "No AI agent available"

    @pytest.mark.asyncio
    async def test_run_heartbeat_no_entities(self, mock_hass, mock_store):
        """Test heartbeat when no entities to monitor."""
        mock_agent = MagicMock()
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        result = await service.async_run_heartbeat()
        assert result.error == "No monitored entities found"

    @pytest.mark.asyncio
    async def test_run_heartbeat_success(self, mock_hass, mock_store):
        """Test successful heartbeat run."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "response": json.dumps(
                    {
                        "alerts": [],
                        "observations": [
                            {"message": "All clear", "worth_remembering": False}
                        ],
                        "all_clear": True,
                    }
                ),
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        mock_state = MagicMock()
        mock_state.entity_id = "sensor.temp"
        mock_state.state = "22"
        mock_state.attributes = {"friendly_name": "Temp", "unit_of_measurement": "°C"}
        mock_hass.states.async_all = MagicMock(return_value=[mock_state])

        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        result = await service.async_run_heartbeat()
        assert result.error is None
        assert result.all_clear is True
        assert result.duration_ms >= 0

        event_names = [call[0][0] for call in mock_hass.bus.async_fire.call_args_list]
        assert EVENT_HEARTBEAT_COMPLETE in event_names

    @pytest.mark.asyncio
    async def test_run_heartbeat_stores_history(self, mock_hass, mock_store):
        """Test that heartbeat run is stored in history."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "response": '{"alerts": [], "observations": [], "all_clear": true}',
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        mock_state = MagicMock()
        mock_state.entity_id = "sensor.temp"
        mock_state.state = "22"
        mock_state.attributes = {"friendly_name": "Temp"}
        mock_hass.states.async_all = MagicMock(return_value=[mock_state])

        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        await service.async_run_heartbeat()
        assert len(service._result_history) == 1

    @pytest.mark.asyncio
    async def test_stop_cancels_interval(self, mock_hass, mock_store):
        """Test that stop cancels the interval."""
        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        mock_cancel = MagicMock()
        service._cancel_interval = mock_cancel

        await service.async_stop()
        mock_cancel.assert_called_once()
        assert service._cancel_interval is None

    @pytest.mark.asyncio
    async def test_run_heartbeat_passes_denied_tools(self, mock_hass, mock_store):
        """Test that heartbeat passes HEARTBEAT_DENIED_TOOLS to agent."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": json.dumps(
                    {"alerts": [], "observations": [], "all_clear": True}
                ),
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        mock_state = MagicMock()
        mock_state.entity_id = "sensor.temp"
        mock_state.state = "22"
        mock_state.attributes = {"friendly_name": "Temp"}
        mock_hass.states.async_all = MagicMock(return_value=[mock_state])

        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        await service.async_run_heartbeat()

        mock_agent.process_query.assert_called_once()
        call_kwargs = mock_agent.process_query.call_args
        assert call_kwargs.kwargs.get("denied_tools") == HEARTBEAT_DENIED_TOOLS

    @pytest.mark.asyncio
    async def test_run_heartbeat_passes_system_prompt(self, mock_hass, mock_store):
        """Test that heartbeat passes HEARTBEAT_SYSTEM_PROMPT."""
        from custom_components.homeclaw.prompts import HEARTBEAT_SYSTEM_PROMPT

        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": json.dumps(
                    {"alerts": [], "observations": [], "all_clear": True}
                ),
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        mock_state = MagicMock()
        mock_state.entity_id = "sensor.temp"
        mock_state.state = "22"
        mock_state.attributes = {"friendly_name": "Temp"}
        mock_hass.states.async_all = MagicMock(return_value=[mock_state])

        service = _make_service(mock_hass, mock_store)
        await service.async_initialize()

        await service.async_run_heartbeat()

        call_kwargs = mock_agent.process_query.call_args
        assert call_kwargs.kwargs.get("system_prompt") == HEARTBEAT_SYSTEM_PROMPT
