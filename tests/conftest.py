"""Fixtures for Homeclaw tests."""

import pytest
import pytest_asyncio
from homeassistant.util import logging as ha_logging

from tests.fixtures import *

pytest_plugins = "pytest_homeassistant_custom_component"


def pytest_configure(config):
    """Configure pytest-asyncio mode to auto for better HA compatibility."""
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pytest.PytestRemovedIn9Warning",
    )


@pytest_asyncio.fixture
async def hass(request):
    """Wrap the HA hass fixture with pytest_asyncio decorator for compatibility.

    This ensures the hass fixture from pytest-homeassistant-custom-component
    works correctly with pytest-asyncio's strict mode.
    """
    # Get the original hass fixture from pytest-homeassistant-custom-component
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.setup import async_setup_component

    # Access the original async generator fixture
    hass_fixture = request.getfixturevalue("hass")

    # If it's an async generator, iterate through it
    if hasattr(hass_fixture, "__anext__"):
        hass_instance = await hass_fixture.__anext__()
        yield hass_instance
        try:
            await hass_fixture.__anext__()
        except StopAsyncIteration:
            pass
    else:
        yield hass_fixture


@pytest.fixture
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test directory.

    Use this fixture explicitly in tests that need custom integrations enabled.
    Not autouse to avoid requiring hass fixture for all tests.
    """
    yield


@pytest.fixture(autouse=True)
def fail_on_log_exception(request, monkeypatch):
    """Fixture to fail if a callback wrapped by catch_log_exception or
    coroutine wrapped by async_create_catching_coro throws.
    """
    if "no_fail_on_log_exception" in request.keywords:
        return

    def log_exception(format_err, *args):
        raise RuntimeError(f"Log exception: {format_err}")

    # Use the imported module object directly
    monkeypatch.setattr(ha_logging, "log_exception", log_exception)
