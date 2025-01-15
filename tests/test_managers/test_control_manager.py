"""Tests for ControlManager.

Tests control operations extracted from the God Class.
Uses TDD approach - tests written first.
"""

import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.homeclaw.managers.control_manager import ControlManager


@pytest.fixture
def control_manager(hass):
    """Create a ControlManager with real hass."""
    return ControlManager(hass)


class TestCallService:
    """Tests for call_service method."""

    @pytest.mark.asyncio
    async def test_call_service(self, control_manager, hass):
        """Test that call_service calls hass.services.async_call."""
        calls = async_mock_service(hass, "light", "turn_on")

        result = await control_manager.call_service(
            domain="light",
            service="turn_on",
            target={"entity_id": "light.living_room"},
            data={"brightness": 255},
        )

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"
        assert calls[0].data["brightness"] == 255

    @pytest.mark.asyncio
    async def test_call_service_not_found(self, control_manager, hass):
        """Test that call_service returns error for unknown service."""
        # Don't mock the service - it won't exist
        result = await control_manager.call_service(
            domain="nonexistent",
            service="fake_service",
        )

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_call_service_with_only_target(self, control_manager, hass):
        """Test call_service with target but no additional data."""
        calls = async_mock_service(hass, "switch", "turn_off")

        result = await control_manager.call_service(
            domain="switch",
            service="turn_off",
            target={"entity_id": "switch.fan"},
        )

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "switch.fan"

    @pytest.mark.asyncio
    async def test_call_service_with_no_target_or_data(self, control_manager, hass):
        """Test call_service with no target or data."""
        calls = async_mock_service(hass, "homeassistant", "restart")

        result = await control_manager.call_service(
            domain="homeassistant",
            service="restart",
        )

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data == {}

    @pytest.mark.asyncio
    async def test_call_service_handles_exception(self, control_manager, hass):
        """Test that call_service completes even when service handler raises exception.

        Note: Home Assistant's service infrastructure catches exceptions in service handlers
        and logs them, so the async_call itself completes successfully from the caller's
        perspective. This test verifies that behavior with real HA fixtures.
        """
        # Register a service that will raise an exception
        async def failing_service(call):
            raise Exception("Service call failed")

        hass.services.async_register("light", "turn_on", failing_service)

        # With real HA, async_call catches exceptions in service handlers
        # so the call appears successful to the caller
        result = await control_manager.call_service(
            domain="light",
            service="turn_on",
            target={"entity_id": "light.test"},
        )

        # The call completes successfully even though the handler raised
        assert result["success"] is True


class TestTurnOn:
    """Tests for turn_on method."""

    @pytest.mark.asyncio
    async def test_turn_on(self, control_manager, hass):
        """Test that turn_on calls domain.turn_on."""
        calls = async_mock_service(hass, "light", "turn_on")

        result = await control_manager.turn_on("light.living_room")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_turn_on_with_kwargs(self, control_manager, hass):
        """Test that turn_on passes additional kwargs to service call."""
        calls = async_mock_service(hass, "light", "turn_on")

        result = await control_manager.turn_on(
            "light.living_room", brightness=200, color_temp=400
        )

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"
        assert calls[0].data["brightness"] == 200
        assert calls[0].data["color_temp"] == 400

    @pytest.mark.asyncio
    async def test_turn_on_switch(self, control_manager, hass):
        """Test that turn_on works with switch domain."""
        calls = async_mock_service(hass, "switch", "turn_on")

        result = await control_manager.turn_on("switch.fan")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "switch.fan"


class TestTurnOff:
    """Tests for turn_off method."""

    @pytest.mark.asyncio
    async def test_turn_off(self, control_manager, hass):
        """Test that turn_off calls domain.turn_off."""
        calls = async_mock_service(hass, "light", "turn_off")

        result = await control_manager.turn_off("light.living_room")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_turn_off_with_kwargs(self, control_manager, hass):
        """Test that turn_off passes additional kwargs to service call."""
        calls = async_mock_service(hass, "light", "turn_off")

        result = await control_manager.turn_off("light.living_room", transition=5)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"
        assert calls[0].data["transition"] == 5

    @pytest.mark.asyncio
    async def test_turn_off_switch(self, control_manager, hass):
        """Test that turn_off works with switch domain."""
        calls = async_mock_service(hass, "switch", "turn_off")

        result = await control_manager.turn_off("switch.fan")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "switch.fan"


class TestToggle:
    """Tests for toggle method."""

    @pytest.mark.asyncio
    async def test_toggle(self, control_manager, hass):
        """Test that toggle calls domain.toggle."""
        calls = async_mock_service(hass, "light", "toggle")

        result = await control_manager.toggle("light.living_room")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_toggle_with_kwargs(self, control_manager, hass):
        """Test that toggle passes additional kwargs to service call."""
        calls = async_mock_service(hass, "light", "toggle")

        result = await control_manager.toggle("light.living_room", transition=2)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "light.living_room"
        assert calls[0].data["transition"] == 2

    @pytest.mark.asyncio
    async def test_toggle_switch(self, control_manager, hass):
        """Test that toggle works with switch domain."""
        calls = async_mock_service(hass, "switch", "toggle")

        result = await control_manager.toggle("switch.fan")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "switch.fan"


class TestSetValueInputNumber:
    """Tests for set_value with input_number entities."""

    @pytest.mark.asyncio
    async def test_set_value_input_number(self, control_manager, hass):
        """Test that set_value calls input_number.set_value."""
        calls = async_mock_service(hass, "input_number", "set_value")

        result = await control_manager.set_value("input_number.target_temp", 22.5)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_number.target_temp"
        assert calls[0].data["value"] == 22.5

    @pytest.mark.asyncio
    async def test_set_value_input_number_integer(self, control_manager, hass):
        """Test that set_value works with integer values."""
        calls = async_mock_service(hass, "input_number", "set_value")

        result = await control_manager.set_value("input_number.volume", 50)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_number.volume"
        assert calls[0].data["value"] == 50


class TestSetValueInputBoolean:
    """Tests for set_value with input_boolean entities."""

    @pytest.mark.asyncio
    async def test_set_value_input_boolean_true(self, control_manager, hass):
        """Test that set_value calls input_boolean.turn_on for truthy value."""
        calls = async_mock_service(hass, "input_boolean", "turn_on")

        result = await control_manager.set_value("input_boolean.vacation_mode", True)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_boolean.vacation_mode"

    @pytest.mark.asyncio
    async def test_set_value_input_boolean_false(self, control_manager, hass):
        """Test that set_value calls input_boolean.turn_off for falsy value."""
        calls = async_mock_service(hass, "input_boolean", "turn_off")

        result = await control_manager.set_value("input_boolean.vacation_mode", False)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_boolean.vacation_mode"

    @pytest.mark.asyncio
    async def test_set_value_input_boolean_truthy_string(self, control_manager, hass):
        """Test that set_value turns on for truthy string values."""
        calls = async_mock_service(hass, "input_boolean", "turn_on")

        result = await control_manager.set_value("input_boolean.vacation_mode", "on")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_boolean.vacation_mode"

    @pytest.mark.asyncio
    async def test_set_value_input_boolean_falsy_zero(self, control_manager, hass):
        """Test that set_value turns off for zero value."""
        calls = async_mock_service(hass, "input_boolean", "turn_off")

        result = await control_manager.set_value("input_boolean.vacation_mode", 0)

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_boolean.vacation_mode"


class TestSetValueInputSelect:
    """Tests for set_value with input_select entities."""

    @pytest.mark.asyncio
    async def test_set_value_input_select(self, control_manager, hass):
        """Test that set_value calls input_select.select_option."""
        calls = async_mock_service(hass, "input_select", "select_option")

        result = await control_manager.set_value("input_select.hvac_mode", "cooling")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_select.hvac_mode"
        assert calls[0].data["option"] == "cooling"

    @pytest.mark.asyncio
    async def test_set_value_input_select_different_option(self, control_manager, hass):
        """Test that set_value works with different select options."""
        calls = async_mock_service(hass, "input_select", "select_option")

        result = await control_manager.set_value("input_select.scene", "Movie Night")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_select.scene"
        assert calls[0].data["option"] == "Movie Night"


class TestSetValueInputText:
    """Tests for set_value with input_text entities."""

    @pytest.mark.asyncio
    async def test_set_value_input_text(self, control_manager, hass):
        """Test that set_value calls input_text.set_value."""
        calls = async_mock_service(hass, "input_text", "set_value")

        result = await control_manager.set_value("input_text.message", "Hello World")

        assert result["success"] is True
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "input_text.message"
        assert calls[0].data["value"] == "Hello World"


class TestControlManagerInitialization:
    """Tests for ControlManager initialization."""

    def test_init_stores_hass(self, hass):
        """Test that ControlManager stores hass reference."""
        manager = ControlManager(hass)

        assert manager.hass is hass

    def test_init_with_none_hass_raises(self):
        """Test that ControlManager raises error with None hass."""
        with pytest.raises(ValueError, match="hass is required"):
            ControlManager(None)
