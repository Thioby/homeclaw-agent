"""Tests for channels/base.py — Channel ABC, dataclasses, rate limiter, registry."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeclaw.channels.base import (
    Channel,
    ChannelRateLimiter,
    ChannelRegistry,
    ChannelTarget,
    MessageEnvelope,
)


# ---------------------------------------------------------------------------
# Concrete test channel (needed because Channel is abstract)
# ---------------------------------------------------------------------------


class FakeChannel(Channel):
    """Minimal concrete Channel subclass for testing."""

    id = "fake"
    name = "Fake Channel"

    def __init__(self, hass, intake, config):
        super().__init__(hass, intake, config)
        self.setup_called = False
        self.teardown_called = False
        self.sent_messages: list[tuple[ChannelTarget, str]] = []

    async def async_setup(self) -> None:
        self.setup_called = True

    async def async_teardown(self) -> None:
        self.teardown_called = True

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        self.sent_messages.append((target, text))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_hass():
    return MagicMock()


@pytest.fixture
def fake_intake():
    return MagicMock()


@pytest.fixture
def fake_channel(fake_hass, fake_intake):
    return FakeChannel(fake_hass, fake_intake, config={})


# ---------------------------------------------------------------------------
# ChannelTarget / MessageEnvelope dataclass tests
# ---------------------------------------------------------------------------


class TestChannelTarget:
    def test_basic_fields(self):
        t = ChannelTarget(channel_id="telegram", target_id="12345")
        assert t.channel_id == "telegram"
        assert t.target_id == "12345"
        assert t.extra == {}

    def test_extra_dict(self):
        t = ChannelTarget(
            channel_id="discord", target_id="ch-1", extra={"guild_id": "g1"}
        )
        assert t.extra["guild_id"] == "g1"


class TestMessageEnvelope:
    def test_basic_fields(self):
        target = ChannelTarget(channel_id="telegram", target_id="chat123")
        e = MessageEnvelope(
            text="hello",
            channel="telegram",
            sender_id="user1",
            sender_name="Jan",
            target=target,
            ha_user_id="telegram_user1",
        )
        assert e.text == "hello"
        assert e.channel == "telegram"
        assert e.sender_id == "user1"
        assert e.sender_name == "Jan"
        assert e.ha_user_id == "telegram_user1"
        assert e.is_group is False
        assert e.thread_id is None
        assert e.attachments == []
        assert e.metadata == {}

    def test_group_message(self):
        target = ChannelTarget(channel_id="discord", target_id="ch-1")
        e = MessageEnvelope(
            text="hi",
            channel="discord",
            sender_id="u1",
            sender_name="Bot",
            target=target,
            ha_user_id="discord_u1",
            is_group=True,
            thread_id="thread-42",
        )
        assert e.is_group is True
        assert e.thread_id == "thread-42"


# ---------------------------------------------------------------------------
# ChannelRateLimiter tests
# ---------------------------------------------------------------------------


class TestChannelRateLimiter:
    def test_allows_within_limit(self):
        limiter = ChannelRateLimiter(max_per_minute=3, max_per_hour=10)
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is True

    def test_blocks_over_minute_limit(self):
        limiter = ChannelRateLimiter(max_per_minute=2, max_per_hour=100)
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is True
        # 3rd should be blocked
        assert limiter.allow("user1") is False

    def test_blocks_over_hour_limit(self):
        limiter = ChannelRateLimiter(max_per_minute=100, max_per_hour=2)
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is True
        # 3rd should be blocked by hour limit
        assert limiter.allow("user1") is False

    def test_different_users_isolated(self):
        limiter = ChannelRateLimiter(max_per_minute=1, max_per_hour=10)
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is False
        # Different user should still be allowed
        assert limiter.allow("user2") is True

    def test_reset_specific_user(self):
        limiter = ChannelRateLimiter(max_per_minute=1, max_per_hour=10)
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is False
        limiter.reset("user1")
        assert limiter.allow("user1") is True

    def test_reset_all(self):
        limiter = ChannelRateLimiter(max_per_minute=1, max_per_hour=10)
        limiter.allow("user1")
        limiter.allow("user2")
        limiter.reset()
        assert limiter.allow("user1") is True
        assert limiter.allow("user2") is True

    def test_expired_entries_cleaned(self, monkeypatch):
        """After 60+ seconds, minute bucket entries should be pruned."""
        limiter = ChannelRateLimiter(max_per_minute=1, max_per_hour=100)

        # First request at time 0
        fake_time = 1000.0
        monkeypatch.setattr(time, "monotonic", lambda: fake_time)
        assert limiter.allow("user1") is True
        assert limiter.allow("user1") is False

        # Advance 61 seconds — minute window should have cleared
        fake_time = 1061.0
        monkeypatch.setattr(time, "monotonic", lambda: fake_time)
        assert limiter.allow("user1") is True


# ---------------------------------------------------------------------------
# Channel ABC helpers tests
# ---------------------------------------------------------------------------


class TestChannelResolveUserId:
    def test_no_mapping_returns_shadow(self, fake_hass, fake_intake):
        ch = FakeChannel(fake_hass, fake_intake, config={})
        assert ch._resolve_user_id("12345") == "fake_12345"

    def test_mapped_user(self, fake_hass, fake_intake):
        config = {"user_mapping": {"12345": "ha-user-uuid-abc"}}
        ch = FakeChannel(fake_hass, fake_intake, config)
        assert ch._resolve_user_id("12345") == "ha-user-uuid-abc"

    def test_unmapped_user_with_mapping_table(self, fake_hass, fake_intake):
        config = {"user_mapping": {"other_id": "ha-user-uuid-abc"}}
        ch = FakeChannel(fake_hass, fake_intake, config)
        assert ch._resolve_user_id("12345") == "fake_12345"

    def test_shadow_user_format_uses_channel_id(self, fake_hass, fake_intake):
        """Shadow user IDs must include the channel id to avoid cross-channel collisions."""

        class DiscordFake(FakeChannel):
            id = "discord"

        ch = DiscordFake(fake_hass, fake_intake, config={})
        assert ch._resolve_user_id("999") == "discord_999"


class TestChannelSessionKey:
    def _make_envelope(self, **overrides) -> MessageEnvelope:
        defaults = {
            "text": "hi",
            "channel": "fake",
            "sender_id": "user1",
            "sender_name": "Test",
            "target": ChannelTarget(channel_id="fake", target_id="chat1"),
            "ha_user_id": "fake_user1",
        }
        defaults.update(overrides)
        return MessageEnvelope(**defaults)

    def test_dm_key(self, fake_channel):
        env = self._make_envelope()
        assert fake_channel._session_key(env) == "fake_user1"

    def test_group_key(self, fake_channel):
        env = self._make_envelope(is_group=True)
        assert fake_channel._session_key(env) == "fake_group_chat1"

    def test_thread_key(self, fake_channel):
        env = self._make_envelope(thread_id="t-42")
        assert fake_channel._session_key(env) == "fake_thread_t-42"

    def test_thread_takes_priority_over_group(self, fake_channel):
        """If both thread_id and is_group are set, thread wins."""
        env = self._make_envelope(is_group=True, thread_id="t-99")
        assert fake_channel._session_key(env) == "fake_thread_t-99"


class TestChannelIsAllowed:
    def test_no_allowlist_allows_all(self, fake_hass, fake_intake):
        ch = FakeChannel(fake_hass, fake_intake, config={})
        assert ch._is_allowed("any_sender", "any_target") is True

    def test_empty_allowlist_allows_all(self, fake_hass, fake_intake):
        ch = FakeChannel(fake_hass, fake_intake, config={"allowed_ids": []})
        assert ch._is_allowed("any_sender", "any_target") is True

    def test_sender_in_allowlist(self, fake_hass, fake_intake):
        ch = FakeChannel(fake_hass, fake_intake, config={"allowed_ids": ["user1"]})
        assert ch._is_allowed("user1", "chat99") is True

    def test_target_in_allowlist(self, fake_hass, fake_intake):
        ch = FakeChannel(fake_hass, fake_intake, config={"allowed_ids": ["chat99"]})
        assert ch._is_allowed("user1", "chat99") is True

    def test_neither_in_allowlist(self, fake_hass, fake_intake):
        ch = FakeChannel(fake_hass, fake_intake, config={"allowed_ids": ["other"]})
        assert ch._is_allowed("user1", "chat99") is False

    def test_int_sender_still_matches_string_allowlist(self, fake_hass, fake_intake):
        """Sender IDs from platforms can be ints; _is_allowed should stringify."""
        ch = FakeChannel(fake_hass, fake_intake, config={"allowed_ids": ["12345"]})
        assert ch._is_allowed(12345, "chat1") is True

    def test_string_allowlist_treated_as_single_id(self, fake_hass, fake_intake):
        """A bare string (not list) should be treated as one ID, not iterable of chars."""
        ch = FakeChannel(fake_hass, fake_intake, config={"allowed_ids": "12345"})
        assert ch._is_allowed("12345", "chat1") is True
        # "1" is a substring but should NOT match when properly normalized
        assert ch._is_allowed("1", "chat1") is False


class TestChannelDefaultBehavior:
    @pytest.mark.asyncio
    async def test_send_typing_is_noop(self, fake_channel):
        """Default send_typing_indicator does nothing (no error)."""
        target = ChannelTarget(channel_id="fake", target_id="123")
        await fake_channel.send_typing_indicator(target)

    @pytest.mark.asyncio
    async def test_send_media_is_noop(self, fake_channel):
        target = ChannelTarget(channel_id="fake", target_id="123")
        await fake_channel.send_media(target, b"data", "image/png")

    def test_is_available_default_true(self, fake_channel):
        assert fake_channel.is_available is True

    def test_rate_limiter_uses_config(self, fake_hass, fake_intake):
        config = {"rate_limit": 5, "rate_limit_hour": 20}
        ch = FakeChannel(fake_hass, fake_intake, config)
        assert ch._rate_limiter._max_minute == 5
        assert ch._rate_limiter._max_hour == 20

    def test_rate_limiter_defaults(self, fake_channel):
        assert fake_channel._rate_limiter._max_minute == 10
        assert fake_channel._rate_limiter._max_hour == 60


# ---------------------------------------------------------------------------
# ChannelRegistry tests
# ---------------------------------------------------------------------------


class TestChannelRegistry:
    def setup_method(self):
        """Clear the registry before each test to avoid cross-test pollution."""
        ChannelRegistry.clear()

    def teardown_method(self):
        ChannelRegistry.clear()

    def test_register_and_get(self):
        @ChannelRegistry.register("test_ch")
        class TestChannel(FakeChannel):
            id = "test_ch"

        assert ChannelRegistry.get("test_ch") is TestChannel

    def test_get_unknown_returns_none(self):
        assert ChannelRegistry.get("nonexistent") is None

    def test_all_returns_copy(self):
        @ChannelRegistry.register("ch1")
        class Ch1(FakeChannel):
            id = "ch1"

        @ChannelRegistry.register("ch2")
        class Ch2(FakeChannel):
            id = "ch2"

        all_channels = ChannelRegistry.all()
        assert "ch1" in all_channels
        assert "ch2" in all_channels
        # It should be a copy — mutating it shouldn't affect the registry
        all_channels.pop("ch1")
        assert ChannelRegistry.get("ch1") is Ch1

    def test_overwrite_warns(self, caplog):
        @ChannelRegistry.register("dup")
        class First(FakeChannel):
            id = "dup"

        @ChannelRegistry.register("dup")
        class Second(FakeChannel):
            id = "dup"

        assert ChannelRegistry.get("dup") is Second
        assert "already registered" in caplog.text

    def test_clear(self):
        @ChannelRegistry.register("temp")
        class Temp(FakeChannel):
            id = "temp"

        assert ChannelRegistry.get("temp") is not None
        ChannelRegistry.clear()
        assert ChannelRegistry.get("temp") is None
