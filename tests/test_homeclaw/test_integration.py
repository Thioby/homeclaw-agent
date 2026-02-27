"""Integration tests for Homeclaw."""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.homeclaw import async_setup_entry, async_unload_entry


class TestIntegration:
    """Test the full integration functionality with real HA fixtures."""

    @pytest.fixture(autouse=True)
    def mock_platform_forwarding(self):
        """Mock platform forwarding since direct async_setup_entry calls bypass entry state management."""
        with (
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                new_callable=AsyncMock,
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            yield

    @pytest.mark.asyncio
    async def test_full_integration_setup(self, hass, homeclaw_config_entry):
        """Test the full integration setup process with real hass."""
        homeclaw_config_entry.add_to_hass(hass)

        # Mock hass.http since it's not set up in the basic hass fixture
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch(
            "custom_components.homeclaw.agent_compat.HomeclawAgent"
        ) as mock_agent_class:
            # Mock agent instance
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent

            result = await async_setup_entry(hass, homeclaw_config_entry)
            assert result is True

            # Verify services were registered
            assert hass.services.has_service("homeclaw", "query")

    @pytest.mark.asyncio
    async def test_service_calls(self, hass, homeclaw_config_entry):
        """Test service call functionality with real service registry."""
        homeclaw_config_entry.add_to_hass(hass)

        # Mock hass.http since it's not set up in the basic hass fixture
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        # Create a mock agent with process_query method
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "success": True,
                "answer": "The light is on",
            }
        )

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            # Setup the integration
            await async_setup_entry(hass, homeclaw_config_entry)
            await hass.async_block_till_done()

            # Verify query service is registered
            assert hass.services.has_service("homeclaw", "query")

            # Set up a test entity state
            hass.states.async_set("light.test", "on", {"brightness": 255})

            # Call the query service with correct parameter name
            await hass.services.async_call(
                "homeclaw",
                "query",
                {"prompt": "Is the light on?"},
                blocking=True,
            )

            # Verify the agent's process_query was called
            mock_agent.process_query.assert_called_once()
            # Verify the call arguments include the prompt
            call_args = mock_agent.process_query.call_args
            assert call_args[0][0] == "Is the light on?"

    @pytest.mark.asyncio
    async def test_frontend_panel_registration(self, hass, homeclaw_config_entry):
        """Test frontend panel registration with real hass.http."""
        homeclaw_config_entry.add_to_hass(hass)

        # Mock hass.http since it's not set up in the basic hass fixture
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch(
            "custom_components.homeclaw.agent_compat.HomeclawAgent"
        ) as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent

            result = await async_setup_entry(hass, homeclaw_config_entry)
            assert result is True

            # Verify static paths were registered for frontend
            hass.http.async_register_static_paths.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_entry(self, hass, homeclaw_config_entry):
        """Test unloading the integration with real config entry."""
        homeclaw_config_entry.add_to_hass(hass)

        # Mock hass.http since it's not set up in the basic hass fixture
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch(
            "custom_components.homeclaw.agent_compat.HomeclawAgent"
        ) as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent

            # Setup first
            await async_setup_entry(hass, homeclaw_config_entry)
            await hass.async_block_till_done()

            # Verify service was registered
            assert hass.services.has_service("homeclaw", "query")

            # Then unload
            result = await async_unload_entry(hass, homeclaw_config_entry)
            assert result is True

    def test_manifest_validation(self):
        """Test that manifest.json is valid."""
        import json

        manifest_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "custom_components",
            "homeclaw",
            "manifest.json",
        )

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        # Check required fields
        assert "domain" in manifest
        assert "name" in manifest
        assert "version" in manifest
        assert "requirements" in manifest
        assert "dependencies" in manifest
        assert "config_flow" in manifest
        assert manifest["config_flow"] is True

    def test_services_yaml_validation(self):
        """Test that services.yaml is valid."""
        import yaml

        services_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "custom_components",
            "homeclaw",
            "services.yaml",
        )

        with open(services_path, "r") as f:
            services = yaml.safe_load(f)

        # Check that query service is defined
        assert "query" in services
        assert "description" in services["query"]
        assert "fields" in services["query"]
