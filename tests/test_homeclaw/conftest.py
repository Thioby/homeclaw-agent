"""Shared fixtures for Homeclaw integration tests."""

import pytest
import pytest_asyncio

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest_asyncio.fixture(autouse=True)
async def setup_homeassistant_component(hass: HomeAssistant):
    """Set up the 'homeassistant' core component before tests.

    This populates hass.data["homeassistant.exposed_entities"] which is
    required by the 'conversation' component (a dependency of homeclaw).
    Without this, any test that triggers HA dependency loading will fail
    with KeyError: 'homeassistant.exposed_entities'.
    """
    await async_setup_component(hass, "homeassistant", {})


@pytest.fixture(autouse=True)
def enable_custom_integrations_for_all(enable_custom_integrations):
    """Enable custom integrations for all tests in this directory.

    Required so the HA loader can find the 'homeclaw' custom component
    when async_forward_entry_setups or async_init triggers integration loading.
    """
    yield
