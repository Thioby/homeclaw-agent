"""Basic tests that don't require Home Assistant."""

import pytest
from custom_components.homeclaw import const
from custom_components.homeclaw.config_flow import HomeclawConfigFlow

def test_domain_constant():
    """Test that the domain constant is defined correctly."""
    assert const.DOMAIN == "homeclaw"


def test_ai_providers_constant():
    """Test that AI providers are defined correctly."""
    assert isinstance(const.AI_PROVIDERS, list)
    assert len(const.AI_PROVIDERS) > 0
    assert "openai" in const.AI_PROVIDERS
    assert "anthropic" in const.AI_PROVIDERS


def test_version_constant():
    """Test version handling."""
    assert hasattr(HomeclawConfigFlow, "VERSION")
    assert HomeclawConfigFlow.VERSION == 1


def test_basic_functionality():
    """Test basic functionality."""
    # Basic validation
    assert isinstance(const.DOMAIN, str)
    assert len(const.DOMAIN) > 0
    assert isinstance(const.AI_PROVIDERS, list)
    assert len(const.AI_PROVIDERS) > 0