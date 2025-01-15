"""Tests for AutomationManager.

Tests automation operations extracted from the God Class.
Uses TDD approach - tests written first.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.homeclaw.managers.automation_manager import AutomationManager


class MockState:
    """Mock Home Assistant state object."""

    def __init__(
        self,
        entity_id: str,
        state: str,
        attributes: dict = None,
        last_changed: datetime = None,
    ):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.last_changed = last_changed or datetime.now(timezone.utc)


@pytest.fixture
def automation_manager(hass):
    """Create an AutomationManager with mocked hass."""
    # Mock states and services on the real hass object to support existing tests
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    
    return AutomationManager(hass)


@pytest.fixture
def sample_automation_states():
    """Create sample automation states for testing."""
    return [
        MockState(
            "automation.morning_lights",
            "on",
            {"friendly_name": "Morning Lights", "last_triggered": "2025-01-29T07:00:00"},
        ),
        MockState(
            "automation.evening_routine",
            "off",
            {"friendly_name": "Evening Routine", "last_triggered": "2025-01-28T18:00:00"},
        ),
        MockState(
            "automation.motion_alert",
            "on",
            {"friendly_name": "Motion Alert", "last_triggered": None},
        ),
    ]


@pytest.fixture
def valid_automation_config():
    """Create a valid automation configuration."""
    return {
        "alias": "Test Automation",
        "trigger": [
            {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
        ],
        "action": [
            {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
        ],
    }


class TestValidateAutomationValid:
    """Tests for validate_automation method with valid configurations."""

    def test_validate_automation_valid(self, automation_manager):
        """Test that a valid automation config returns {valid: True}."""
        config = {
            "alias": "Test Automation",
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
            ],
            "action": [
                {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
            ],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True
        assert "error" not in result or result.get("error") is None

    def test_validate_automation_valid_with_single_trigger(self, automation_manager):
        """Test that a single trigger (not in list) is also valid."""
        config = {
            "alias": "Single Trigger Automation",
            "trigger": {"platform": "time", "at": "07:00:00"},
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True

    def test_validate_automation_valid_with_single_action(self, automation_manager):
        """Test that a single action (not in list) is also valid."""
        config = {
            "alias": "Single Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": {"service": "notify.mobile_app"},
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True

    def test_validate_automation_valid_with_action_field(self, automation_manager):
        """Test that action field (instead of service) is valid."""
        config = {
            "alias": "Action Field Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [{"action": "light.turn_on", "target": {"entity_id": "light.test"}}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True


class TestValidateAutomationMissingTrigger:
    """Tests for validate_automation with missing trigger."""

    def test_validate_automation_missing_trigger(self, automation_manager):
        """Test that missing trigger returns {valid: False, error: ...}."""
        config = {
            "alias": "No Trigger Automation",
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "trigger" in result["error"].lower()

    def test_validate_automation_empty_trigger(self, automation_manager):
        """Test that empty trigger list returns {valid: False, error: ...}."""
        config = {
            "alias": "Empty Trigger Automation",
            "trigger": [],
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "trigger" in result["error"].lower()

    def test_validate_automation_null_trigger(self, automation_manager):
        """Test that null trigger returns {valid: False, error: ...}."""
        config = {
            "alias": "Null Trigger Automation",
            "trigger": None,
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result


class TestValidateAutomationMissingAction:
    """Tests for validate_automation with missing action."""

    def test_validate_automation_missing_action(self, automation_manager):
        """Test that missing action returns {valid: False, error: ...}."""
        config = {
            "alias": "No Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "action" in result["error"].lower()

    def test_validate_automation_empty_action(self, automation_manager):
        """Test that empty action list returns {valid: False, error: ...}."""
        config = {
            "alias": "Empty Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "action" in result["error"].lower()

    def test_validate_automation_action_missing_service_and_action(self, automation_manager):
        """Test that action without service or action field returns {valid: False, error: ...}."""
        config = {
            "alias": "Invalid Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [{"target": {"entity_id": "light.test"}}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result


class TestCreateAutomation:
    """Tests for create_automation method."""

    @pytest.mark.asyncio
    async def test_create_automation(self, automation_manager, hass, valid_automation_config):
        """Test that create_automation calls hass.services.async_call."""
        result = await automation_manager.create_automation(valid_automation_config)

        # Should call the automation reload service
        hass.services.async_call.assert_called()
        assert result is not None
        assert "success" in result or "id" in result

    @pytest.mark.asyncio
    async def test_create_automation_generates_id_if_missing(self, automation_manager, hass):
        """Test that create_automation generates an ID if not provided."""
        config = {
            "alias": "Auto ID Automation",
            "trigger": [{"platform": "time", "at": "08:00:00"}],
            "action": [{"service": "light.turn_on"}],
        }

        result = await automation_manager.create_automation(config)

        assert result is not None
        # ID should be generated
        assert "id" in result

    @pytest.mark.asyncio
    async def test_create_automation_uses_provided_id(self, automation_manager, hass):
        """Test that create_automation uses the provided ID."""
        config = {
            "id": "custom_automation_id",
            "alias": "Custom ID Automation",
            "trigger": [{"platform": "time", "at": "08:00:00"}],
            "action": [{"service": "light.turn_on"}],
        }

        result = await automation_manager.create_automation(config)

        assert result is not None
        assert result.get("id") == "custom_automation_id"


class TestGetAutomations:
    """Tests for get_automations method."""

    def test_get_automations(self, automation_manager, hass, sample_automation_states):
        """Test that get_automations returns list from hass.states.async_all("automation")."""
        hass.states.async_all.return_value = sample_automation_states

        result = automation_manager.get_automations()

        assert isinstance(result, list)
        assert len(result) == 3
        entity_ids = [a["entity_id"] for a in result]
        assert "automation.morning_lights" in entity_ids
        assert "automation.evening_routine" in entity_ids
        assert "automation.motion_alert" in entity_ids

    def test_get_automations_empty(self, automation_manager, hass):
        """Test that get_automations returns empty list when no automations."""
        hass.states.async_all.return_value = []

        result = automation_manager.get_automations()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_automations_filters_by_domain(self, automation_manager, hass, sample_automation_states):
        """Test that get_automations only returns automation domain entities."""
        # Add some non-automation entities
        mixed_states = sample_automation_states + [
            MockState("light.test", "on", {}),
            MockState("sensor.test", "25", {}),
        ]
        hass.states.async_all.return_value = mixed_states

        result = automation_manager.get_automations()

        # Should only return automation entities
        for entity in result:
            assert entity["entity_id"].startswith("automation.")

    def test_get_automations_returns_proper_dict_structure(
        self, automation_manager, hass, sample_automation_states
    ):
        """Test that get_automations returns proper dict structure."""
        hass.states.async_all.return_value = sample_automation_states

        result = automation_manager.get_automations()

        assert len(result) > 0
        for automation in result:
            assert "entity_id" in automation
            assert "state" in automation
            assert "attributes" in automation


class TestToggleAutomationOn:
    """Tests for toggle_automation with enable=True."""

    @pytest.mark.asyncio
    async def test_toggle_automation_on(self, automation_manager, hass):
        """Test that toggle_automation with enable=True calls automation.turn_on."""
        entity_id = "automation.morning_lights"

        result = await automation_manager.toggle_automation(entity_id, enable=True)

        hass.services.async_call.assert_called_once_with(
            "automation",
            "turn_on",
            {"entity_id": entity_id},
        )
        assert result is not None
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_toggle_automation_on_returns_entity_id(self, automation_manager, hass):
        """Test that toggle_automation returns the entity_id in result."""
        entity_id = "automation.test_automation"

        result = await automation_manager.toggle_automation(entity_id, enable=True)

        assert result.get("entity_id") == entity_id


class TestToggleAutomationOff:
    """Tests for toggle_automation with enable=False."""

    @pytest.mark.asyncio
    async def test_toggle_automation_off(self, automation_manager, hass):
        """Test that toggle_automation with enable=False calls automation.turn_off."""
        entity_id = "automation.evening_routine"

        result = await automation_manager.toggle_automation(entity_id, enable=False)

        hass.services.async_call.assert_called_once_with(
            "automation",
            "turn_off",
            {"entity_id": entity_id},
        )
        assert result is not None
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_toggle_automation_off_returns_entity_id(self, automation_manager, hass):
        """Test that toggle_automation returns the entity_id in result."""
        entity_id = "automation.test_automation"

        result = await automation_manager.toggle_automation(entity_id, enable=False)

        assert result.get("entity_id") == entity_id


class TestAutomationManagerInitialization:
    """Tests for AutomationManager initialization."""

    def test_init_stores_hass(self, hass):
        """Test that AutomationManager stores hass reference."""
        manager = AutomationManager(hass)

        assert manager.hass is hass

    def test_init_with_none_hass_raises(self):
        """Test that AutomationManager raises error with None hass."""
        with pytest.raises(ValueError, match="hass is required"):
            AutomationManager(None)
