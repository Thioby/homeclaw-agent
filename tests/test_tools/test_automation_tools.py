"""Tests for the create_automation tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.tools.base import ToolRegistry, ToolTier


@pytest.fixture
def mock_hass():
    """Minimal hass mock for tool tests."""
    h = MagicMock()
    h.config.path = MagicMock(side_effect=lambda x: f"/config/{x}")
    h.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a) if a else f())
    h.data = {}
    return h


AUTOMATION = {
    "alias": "Test",
    "triggers": [{"trigger": "state", "entity_id": "sensor.x"}],
    "actions": [{"action": "light.turn_on"}],
}


class TestCreateAutomationTool:
    """Tests for CreateAutomation tool."""

    def test_tool_registered(self):
        assert ToolRegistry.get_tool_class("create_automation") is not None

    def test_tool_requires_confirmation(self):
        tool_cls = ToolRegistry.get_tool_class("create_automation")
        assert tool_cls.requires_confirmation is True

    def test_tool_is_core_tier(self):
        tool_cls = ToolRegistry.get_tool_class("create_automation")
        assert tool_cls.tier == ToolTier.CORE

    @pytest.mark.asyncio
    async def test_dry_run_defaults_to_true(self, mock_hass):
        with patch(
            "custom_components.homeclaw.managers.automation_manager.AutomationManager.create_automation",
            new_callable=AsyncMock,
            return_value={"success": True, "dry_run": True, "id": "abc", "preview": "x"},
        ) as create:
            tool = ToolRegistry.get_tool("create_automation", hass=mock_hass, config={})
            result = await tool.execute(automation=AUTOMATION)

        create.assert_awaited_once_with(AUTOMATION, dry_run=True)
        assert result.success is True
        assert json.loads(result.output)["dry_run"] is True

    @pytest.mark.asyncio
    async def test_dry_run_false_passed_through(self, mock_hass):
        with patch(
            "custom_components.homeclaw.managers.automation_manager.AutomationManager.create_automation",
            new_callable=AsyncMock,
            return_value={"success": True, "id": "abc"},
        ) as create:
            tool = ToolRegistry.get_tool("create_automation", hass=mock_hass, config={})
            result = await tool.execute(automation=AUTOMATION, dry_run=False)

        create.assert_awaited_once_with(AUTOMATION, dry_run=False)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_manager_error_becomes_failed_result(self, mock_hass):
        with patch(
            "custom_components.homeclaw.managers.automation_manager.AutomationManager.create_automation",
            new_callable=AsyncMock,
            return_value={"success": False, "error": "boom"},
        ):
            tool = ToolRegistry.get_tool("create_automation", hass=mock_hass, config={})
            result = await tool.execute(automation=AUTOMATION)

        assert result.success is False
        assert result.error == "boom"
