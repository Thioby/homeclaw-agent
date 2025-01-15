"""Tests for the configuration flow."""

import pytest
from unittest.mock import MagicMock
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homeclaw.config_flow import HomeclawConfigFlow
from custom_components.homeclaw.const import DOMAIN, AI_PROVIDERS


class TestConfigFlow:
    """Test the config flow."""

    def test_config_flow_import(self):
        """Test that config flow can be imported without errors."""
        assert HomeclawConfigFlow is not None
        assert hasattr(HomeclawConfigFlow, 'VERSION')
        assert HomeclawConfigFlow.VERSION == 1

    def test_config_flow_class_structure(self):
        """Test config flow class structure."""
        flow_class = HomeclawConfigFlow
        
        # Check that required methods exist
        assert hasattr(flow_class, 'async_step_user')
        assert hasattr(flow_class, 'async_step_configure')
        assert hasattr(flow_class, 'async_step_anthropic_oauth')
        assert hasattr(flow_class, 'async_step_gemini_oauth')

    def test_config_flow_domain(self):
        """Test config flow domain constants."""
        assert DOMAIN == "homeclaw"

    def test_config_flow_ai_providers(self):
        """Test that AI providers are defined."""
        expected_providers = ["llama", "openai", "gemini", "openrouter", "anthropic", "local"]
        assert all(provider in AI_PROVIDERS for provider in expected_providers)

    def test_config_flow_schema_structure(self):
        """Test that config flow has proper schema structure."""
        flow = HomeclawConfigFlow()
        assert flow is not None
        assert flow.VERSION == 1