"""Tests for channels/manager.py — ChannelManager lifecycle and health."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.channels.base import (
    Channel,
    ChannelRegistry,
    ChannelTarget,
)
from custom_components.homeclaw.channels.manager import ChannelManager


# ---------------------------------------------------------------------------
# Test channel implementations
# ---------------------------------------------------------------------------


class GoodChannel(Channel):
    """Channel that starts and stops cleanly."""

    id = "good"
    name = "Good Channel"

    def __init__(self, hass, intake, config):
        super().__init__(hass, intake, config)
        self.setup_called = False
        self.teardown_called = False

    async def async_setup(self) -> None:
        self.setup_called = True

    async def async_teardown(self) -> None:
        self.teardown_called = True

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        pass


class FailingSetupChannel(Channel):
    """Channel that raises on setup."""

    id = "failing"
    name = "Failing Channel"

    async def async_setup(self) -> None:
        raise RuntimeError("Setup exploded")

    async def async_teardown(self) -> None:
        pass

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        pass


class FailingTeardownChannel(Channel):
    """Channel that raises on teardown."""

    id = "bad_teardown"
    name = "Bad Teardown"

    async def async_setup(self) -> None:
        pass

    async def async_teardown(self) -> None:
        raise RuntimeError("Teardown exploded")

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        pass


class UnavailableChannel(Channel):
    """Channel that reports itself as not available."""

    id = "unavail"
    name = "Unavailable Channel"

    async def async_setup(self) -> None:
        pass

    async def async_teardown(self) -> None:
        pass

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        pass

    @property
    def is_available(self) -> bool:
        return False


class CrashingAvailableChannel(Channel):
    """Channel whose is_available property raises an exception."""

    id = "crashing"
    name = "Crashing Channel"

    async def async_setup(self) -> None:
        pass

    async def async_teardown(self) -> None:
        pass

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        pass

    @property
    def is_available(self) -> bool:
        raise RuntimeError("is_available exploded")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure clean registry for every test."""
    ChannelRegistry.clear()
    yield
    ChannelRegistry.clear()


@pytest.fixture
def fake_hass():
    return MagicMock()


@pytest.fixture
def fake_intake():
    return MagicMock()


@pytest.fixture
def manager(fake_hass, fake_intake):
    return ChannelManager(fake_hass, fake_intake)


# ---------------------------------------------------------------------------
# Setup tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChannelManagerSetup:
    async def test_no_channels_registered(self, manager):
        """With empty registry, setup does nothing."""
        await manager.async_setup({})
        assert manager.active_channels == []

    async def test_channel_not_enabled(self, manager):
        """Disabled channels are skipped."""
        ChannelRegistry.register("good")(GoodChannel)
        await manager.async_setup({"channel_good": {"enabled": False}})
        assert manager.active_channels == []

    async def test_channel_missing_config(self, manager):
        """Channels with no config entry are skipped (enabled defaults to False)."""
        ChannelRegistry.register("good")(GoodChannel)
        await manager.async_setup({})
        assert manager.active_channels == []

    async def test_enabled_channel_starts(self, manager):
        """Enabled channel gets instantiated and started."""
        ChannelRegistry.register("good")(GoodChannel)
        await manager.async_setup({"channel_good": {"enabled": True}})
        assert "good" in manager.active_channels
        ch = manager.get_channel("good")
        assert ch is not None
        assert ch.setup_called is True

    async def test_failing_setup_does_not_crash(self, manager, caplog):
        """A channel that raises on setup is logged but doesn't block others."""
        ChannelRegistry.register("failing")(FailingSetupChannel)
        ChannelRegistry.register("good")(GoodChannel)

        await manager.async_setup(
            {
                "channel_failing": {"enabled": True},
                "channel_good": {"enabled": True},
            }
        )

        # Good channel should still be running
        assert "good" in manager.active_channels
        # Failing channel should not be in active list
        assert "failing" not in manager.active_channels
        assert "Failed to start channel failing" in caplog.text

    async def test_multiple_channels(self, manager):
        """Multiple enabled channels all start."""
        ChannelRegistry.register("good")(GoodChannel)
        ChannelRegistry.register("unavail")(UnavailableChannel)

        await manager.async_setup(
            {
                "channel_good": {"enabled": True},
                "channel_unavail": {"enabled": True},
            }
        )

        assert len(manager.active_channels) == 2


# ---------------------------------------------------------------------------
# Teardown tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChannelManagerTeardown:
    async def test_teardown_stops_all_channels(self, manager):
        ChannelRegistry.register("good")(GoodChannel)
        await manager.async_setup({"channel_good": {"enabled": True}})
        ch = manager.get_channel("good")

        await manager.async_teardown()

        assert ch.teardown_called is True
        assert manager.active_channels == []

    async def test_teardown_with_no_channels(self, manager):
        """Teardown on empty manager is a no-op."""
        await manager.async_teardown()
        assert manager.active_channels == []

    async def test_failing_teardown_does_not_crash(self, manager, caplog):
        """A channel that raises on teardown is logged but doesn't prevent others."""
        ChannelRegistry.register("bad_teardown")(FailingTeardownChannel)
        ChannelRegistry.register("good")(GoodChannel)

        await manager.async_setup(
            {
                "channel_bad_teardown": {"enabled": True},
                "channel_good": {"enabled": True},
            }
        )

        await manager.async_teardown()

        assert manager.active_channels == []
        assert "Error stopping channel bad_teardown" in caplog.text


# ---------------------------------------------------------------------------
# Status / query tests
# ---------------------------------------------------------------------------


class TestChannelManagerStatus:
    @pytest.mark.asyncio
    async def test_status_empty(self, manager):
        assert manager.get_status() == {}

    @pytest.mark.asyncio
    async def test_status_with_channels(self, manager):
        ChannelRegistry.register("good")(GoodChannel)
        ChannelRegistry.register("unavail")(UnavailableChannel)

        await manager.async_setup(
            {
                "channel_good": {"enabled": True},
                "channel_unavail": {"enabled": True},
            }
        )

        status = manager.get_status()
        assert status["good"] == {"available": True, "name": "Good Channel"}
        assert status["unavail"] == {"available": False, "name": "Unavailable Channel"}

    @pytest.mark.asyncio
    async def test_get_channel_returns_none_for_unknown(self, manager):
        assert manager.get_channel("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_channel_returns_instance(self, manager):
        ChannelRegistry.register("good")(GoodChannel)
        await manager.async_setup({"channel_good": {"enabled": True}})
        ch = manager.get_channel("good")
        assert isinstance(ch, GoodChannel)

    @pytest.mark.asyncio
    async def test_status_survives_crashing_is_available(self, manager, caplog):
        """get_status should not crash if a channel's is_available raises."""
        ChannelRegistry.register("crashing")(CrashingAvailableChannel)
        ChannelRegistry.register("good")(GoodChannel)

        await manager.async_setup(
            {
                "channel_crashing": {"enabled": True},
                "channel_good": {"enabled": True},
            }
        )

        status = manager.get_status()
        assert status["crashing"]["available"] is False
        assert status["good"]["available"] is True
        assert "Error checking availability" in caplog.text
