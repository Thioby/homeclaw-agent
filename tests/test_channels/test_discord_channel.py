"""Tests for DiscordChannel implementation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeclaw.channels.base import ChannelTarget
from custom_components.homeclaw.channels.discord import DiscordChannel
from custom_components.homeclaw.channels.discord.helpers import (
    chunk_text,
    is_dm_allowed,
    is_group_allowed,
    normalize_id_list,
)
from custom_components.homeclaw.core.events import (
    CompletionEvent,
    ErrorEvent,
    TextEvent,
)


def _make_channel(hass: FakeHass, intake: Any, config: dict[str, Any]) -> Any:
    return cast(Any, DiscordChannel(cast(Any, hass), intake, config=config))


class FakeHass:
    def __init__(self) -> None:
        self.data = {}
        self.tasks: list[asyncio.Task] = []

    def async_create_task(self, coro, name=None):  # noqa: ANN001
        task = asyncio.create_task(coro, name=name)
        self.tasks.append(task)
        return task


@dataclass
class FakeSession:
    session_id: str
    metadata: dict


@pytest.fixture
def hass() -> FakeHass:
    return FakeHass()


@pytest.fixture
def intake():
    mock = MagicMock()

    async def _stream(*_args, **_kwargs):
        yield TextEvent(content="hello")
        yield CompletionEvent(messages=[])

    mock.process_message_stream = _stream
    return mock


class TestDiscordChannel:
    @pytest.mark.asyncio
    async def test_setup_requires_token(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        await ch.async_setup()
        assert ch.is_available is False

    @pytest.mark.asyncio
    async def test_setup_and_teardown(self, hass, intake):
        ch = _make_channel(hass, intake, config={"bot_token": "abc"})
        await ch.async_setup()
        assert ch._gateway is not None
        assert ch._rest is not None
        await ch.async_teardown()

    @pytest.mark.asyncio
    async def test_send_response_chunks(self, hass, intake):
        ch = _make_channel(hass, intake, config={"bot_token": "abc"})
        ch._rest = MagicMock()
        ch._rest.create_message = AsyncMock()
        target = ChannelTarget(channel_id="discord", target_id="chan1")
        await ch.send_response(target, "x" * 4501)
        assert ch._rest.create_message.await_count == 3

    def test_strip_mention(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        ch._bot_id = "123"
        assert ch._strip_mention("<@123> hi") == "hi"
        assert ch._strip_mention("<@!123>  hello") == "hello"

    def test_should_respond_dm(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        assert ch._should_respond({"guild_id": None}) is True

    def test_should_respond_mention(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        ch._bot_id = "bot1"
        message = {"guild_id": "g1", "mentions": [{"id": "bot1"}], "channel_id": "c1"}
        assert ch._should_respond(message) is True

    def test_should_respond_config_channel(self, hass, intake):
        ch = _make_channel(
            hass,
            intake,
            config={"discord_auto_respond_channels": "c1\nc2"},
        )
        message = {"guild_id": "g1", "mentions": [], "channel_id": "c2"}
        assert ch._should_respond(message) is True

    def test_should_respond_without_mention_when_disabled(self, hass, intake):
        ch = _make_channel(hass, intake, config={"require_mention": False})
        message = {"guild_id": "g1", "mentions": [], "channel_id": "c2"}
        assert ch._should_respond(message) is True

    def test_build_envelope_success(self, hass, intake):
        ch = _make_channel(hass, intake, config={"dm_policy": "open"})
        ch._bot_id = "bot"
        ch._rate_limiter.allow = MagicMock(return_value=True)
        ch._should_respond = MagicMock(return_value=True)
        message = {
            "content": "hello",
            "channel_id": "c1",
            "guild_id": "g1",
            "author": {"id": "u1", "username": "Jan", "bot": False},
            "mentions": [],
        }
        env = ch._build_envelope(message)
        assert env is not None
        assert env.sender_id == "u1"
        assert env.target.target_id == "c1"
        assert env.ha_user_id == "discord_u1"

    def test_build_envelope_dm_open_policy(self, hass, intake):
        ch = _make_channel(hass, intake, config={"dm_policy": "open"})
        ch._bot_id = "bot"
        ch._rate_limiter.allow = MagicMock(return_value=True)
        ch._should_respond = MagicMock(return_value=True)
        message = {
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
            "mentions": [],
        }
        assert ch._build_envelope(message) is not None

    def test_build_envelope_dm_pairing_blocks_unlisted(self, hass, intake):
        ch = _make_channel(hass, intake, config={"dm_policy": "pairing"})
        ch._bot_id = "bot"
        ch._rate_limiter.allow = MagicMock(return_value=True)
        ch._should_respond = MagicMock(return_value=True)
        message = {
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
            "mentions": [],
        }
        assert ch._build_envelope(message) is None

    def test_build_envelope_ignores_bot(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        message = {
            "content": "hello",
            "channel_id": "c1",
            "author": {"id": "u1", "bot": True},
        }
        assert ch._build_envelope(message) is None

    @pytest.mark.asyncio
    async def test_run_stream_error_event(self, hass, intake):
        ch = _make_channel(hass, intake, config={})

        async def _stream(*_args, **_kwargs):
            yield TextEvent(content="partial")
            yield ErrorEvent(message="boom")

        intake.process_message_stream = _stream
        env = SimpleNamespace(text="x", ha_user_id="u1")
        answer = await ch._run_stream(env, "s1", [])
        assert answer == "Sorry, I encountered an error."

    @pytest.mark.asyncio
    async def test_get_or_create_session_reuses_existing(
        self, hass, intake, monkeypatch
    ):
        ch = _make_channel(hass, intake, config={})
        env = SimpleNamespace(
            sender_id="u1",
            target=SimpleNamespace(target_id="c1"),
            is_group=False,
            thread_id=None,
            sender_name="Jan",
            text="Hello",
            ha_user_id="discord_u1",
        )

        storage = MagicMock()
        storage.list_sessions = AsyncMock(
            return_value=[
                FakeSession("existing", {"external_session_key": "discord_u1"})
            ]
        )
        storage.create_session = AsyncMock()
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.get_storage",
            lambda _h, _u: storage,
        )

        session_id = await ch._get_or_create_session_id(env)
        assert session_id == "existing"
        storage.create_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new(self, hass, intake, monkeypatch):
        hass.data["homeclaw"] = {"agents": {"openai": object()}}
        ch = _make_channel(hass, intake, config={})
        env = SimpleNamespace(
            sender_id="u2",
            target=SimpleNamespace(target_id="c2"),
            is_group=False,
            thread_id=None,
            sender_name="Ala",
            text="Question",
            ha_user_id="discord_u2",
        )

        storage = MagicMock()
        storage.list_sessions = AsyncMock(return_value=[])
        storage.create_session = AsyncMock(return_value=FakeSession("new1", {}))
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.get_storage",
            lambda _h, _u: storage,
        )

        session_id = await ch._get_or_create_session_id(env)
        assert session_id == "new1"
        args = storage.create_session.await_args.kwargs
        assert args["provider"] == "openai"
        assert args["metadata"]["channel"] == "discord"


class TestDiscordHelpers:
    def test_chunk_text(self):
        chunks = chunk_text("abcdef", 2)
        assert chunks == ["ab", "cd", "ef"]

    def test_normalize_id_list(self):
        assert normalize_id_list("1,2\n3") == {"1", "2", "3"}
        assert normalize_id_list([1, " 2 "]) == {"1", "2"}

    def test_is_group_allowed_open(self):
        assert is_group_allowed({"group_policy": "open"}, "u1", "c1") is True

    def test_is_group_allowed_allowlist(self):
        cfg = {"group_policy": "allowlist", "allowed_ids": ["u1"]}
        assert is_group_allowed(cfg, "u1", "c1") is True
        assert is_group_allowed(cfg, "u2", "c1") is False

    def test_is_dm_allowed_open(self):
        assert is_dm_allowed({"dm_policy": "open"}, "u1", "dm1") is True

    def test_is_dm_allowed_pairing(self):
        cfg = {"dm_policy": "pairing", "allowed_ids": ["u1"]}
        assert is_dm_allowed(cfg, "u1", "dm1") is True
        assert is_dm_allowed(cfg, "u2", "dm1") is False
