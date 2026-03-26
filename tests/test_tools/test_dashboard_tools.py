"""Tests for dashboard management tools."""

from __future__ import annotations

import json

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.homeclaw.tools.base import ToolRegistry, ToolResult, ToolTier


@pytest.fixture
def mock_hass():
    """Minimal hass mock for tool tests."""
    h = MagicMock()
    h.config.path = MagicMock(side_effect=lambda x: f"/config/{x}")
    h.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a) if a else f())
    h.data = {}
    return h


@pytest.fixture
def mock_config():
    """Minimal config dict."""
    return {}


class TestCreateDashboardTool:
    """Tests for CreateDashboard tool."""

    def test_tool_registered(self):
        """Test that create_dashboard is registered in ToolRegistry."""
        tool_cls = ToolRegistry.get_tool_class("create_dashboard")
        assert tool_cls is not None

    def test_tool_is_core_tier(self):
        """Test that create_dashboard is CORE tier."""
        tool_cls = ToolRegistry.get_tool_class("create_dashboard")
        assert tool_cls.tier == ToolTier.CORE

    @pytest.mark.asyncio
    async def test_dry_run_true_returns_preview(self, mock_hass, mock_config):
        """Test dry_run=true returns YAML preview."""
        mock_result = {
            "dry_run": True,
            "title": "Security",
            "url_path": "security",
            "preview": "title: Security\n",
            "validation": {"valid": True, "warnings": [], "errors": []},
        }
        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.create_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("create_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(
                title="Security",
                url_path="security",
                views=[{"title": "Cameras", "cards": []}],
                dry_run=True,
            )
        assert result.success
        output = json.loads(result.output)
        assert output["dry_run"] is True

    @pytest.mark.asyncio
    async def test_dry_run_false_creates(self, mock_hass, mock_config):
        """Test dry_run=false creates dashboard."""
        mock_result = {
            "success": True,
            "message": "Dashboard created.",
            "url_path": "security",
            "restart_required": True,
        }
        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.create_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("create_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(
                title="Security",
                url_path="security",
                views=[{"title": "Cameras", "cards": []}],
                dry_run=False,
            )
        assert result.success
        output = json.loads(result.output)
        assert output["success"] is True


class TestUpdateDashboardTool:
    """Tests for UpdateDashboard tool."""

    def test_tool_registered(self):
        """Test that update_dashboard is registered."""
        tool_cls = ToolRegistry.get_tool_class("update_dashboard")
        assert tool_cls is not None

    @pytest.mark.asyncio
    async def test_dry_run_returns_diff(self, mock_hass, mock_config):
        """Test dry_run returns current vs new config."""
        mock_result = {
            "dry_run": True,
            "dashboard_url": "energy",
            "current_config": "title: Old\n",
            "new_config": "title: New\n",
            "validation": {"valid": True, "warnings": [], "errors": []},
        }
        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.update_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("update_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(
                dashboard_url="energy",
                title="New Energy",
                views=[],
                dry_run=True,
            )
        assert result.success
        output = json.loads(result.output)
        assert output["dry_run"] is True


class TestDeleteDashboardTool:
    """Tests for DeleteDashboard tool."""

    def test_tool_registered(self):
        """Test that delete_dashboard is registered."""
        tool_cls = ToolRegistry.get_tool_class("delete_dashboard")
        assert tool_cls is not None

    @pytest.mark.asyncio
    async def test_dry_run_returns_info(self, mock_hass, mock_config):
        """Test dry_run returns info about what will be deleted."""
        mock_result = {
            "dry_run": True,
            "exists": True,
            "dashboard_url": "energy",
            "file": "/config/ui-lovelace-energy.yaml",
            "title": "Energy",
            "preview": "title: Energy\n",
        }
        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.delete_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("delete_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(dashboard_url="energy", dry_run=True)
        assert result.success
        output = json.loads(result.output)
        assert output["exists"] is True

    @pytest.mark.asyncio
    async def test_dry_run_false_deletes(self, mock_hass, mock_config):
        """Test dry_run=false deletes dashboard."""
        mock_result = {
            "success": True,
            "message": "Dashboard deleted.",
            "restart_required": True,
        }
        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager.delete_dashboard",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            tool = ToolRegistry.get_tool("delete_dashboard", hass=mock_hass, config=mock_config)
            result = await tool.execute(dashboard_url="energy", dry_run=False)
        assert result.success
        output = json.loads(result.output)
        assert output["success"] is True
