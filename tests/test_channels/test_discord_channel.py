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
    get_last_target,
    is_dm_allowed,
    is_group_allowed,
    normalize_id_list,
    set_last_target,
)
from custom_components.homeclaw.channels.discord.pairing import get_request_by_code
from custom_components.homeclaw.core.events import (
    CompletionEvent,
    ErrorEvent,
    TextEvent,
)
from custom_components.homeclaw.storage import Message


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
    async def test_pairing_message_creates_request(self, hass, intake):
        ch = _make_channel(hass, intake, config={"dm_policy": "pairing"})
        ch._bot_id = "bot"
        ch.send_response = AsyncMock()
        message = {
            "id": "m1",
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }

        handled = await ch._handle_pairing_message(message)

        assert handled is True
        ch.send_response.assert_awaited_once()
        payload = ch.send_response.await_args_list[-1].args[1]
        assert "confirm discord pairing code" in payload
        code = payload.rsplit(" ", 1)[-1]
        assert get_request_by_code(hass, code) is not None

    @pytest.mark.asyncio
    async def test_pairing_message_acks_existing_code(self, hass, intake):
        ch = _make_channel(hass, intake, config={"dm_policy": "pairing"})
        ch._bot_id = "bot"
        ch.send_response = AsyncMock()
        first = {
            "id": "m1",
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }
        await ch._handle_pairing_message(first)
        first_text = ch.send_response.await_args_list[-1].args[1]
        code = first_text.rsplit(" ", 1)[-1]
        ch.send_response.reset_mock()

        second = {
            "id": "m2",
            "content": f"pair {code}",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }

        handled = await ch._handle_pairing_message(second)

        assert handled is True
        ch.send_response.assert_awaited_once()
        assert "Pairing code received" in ch.send_response.await_args_list[-1].args[1]

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

    def test_is_dm_allowed_pairing_via_user_mapping(self):
        """Paired user in user_mapping is allowed even without allowed_ids."""
        cfg = {"dm_policy": "pairing", "user_mapping": {"u2": "ha_user_1"}}
        assert is_dm_allowed(cfg, "u2", "dm1") is True
        assert is_dm_allowed(cfg, "u3", "dm1") is False

    def test_is_dm_allowed_pairing_via_external_user_mapping(self):
        """Paired user in external_user_mapping is allowed."""
        cfg = {"dm_policy": "pairing", "external_user_mapping": {"u2": "ha_user_1"}}
        assert is_dm_allowed(cfg, "u2", "dm1") is True

    def test_is_dm_allowed_pairing_mapping_takes_priority(self):
        """user_mapping grants access even when allowed_ids is empty."""
        cfg = {
            "dm_policy": "pairing",
            "allowed_ids": [],
            "user_mapping": {"u5": "ha_user_5"},
        }
        assert is_dm_allowed(cfg, "u5", "dm1") is True
        assert is_dm_allowed(cfg, "u6", "dm1") is False

    def test_last_target_cache(self, hass):
        set_last_target(
            hass,
            ha_user_id="discord_u1",
            target_id="chan1",
            sender_id="u1",
            is_group=False,
        )
        target = get_last_target(hass, "discord_u1")
        assert target is not None
        assert target["target_id"] == "chan1"


class TestMessageDedup:
    """Regression tests for Bug 2: duplicate message processing."""

    def test_mark_seen_returns_false_for_new_id(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        assert ch._mark_seen("msg_001") is False

    def test_mark_seen_returns_true_for_duplicate(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        ch._mark_seen("msg_001")
        assert ch._mark_seen("msg_001") is True

    def test_mark_seen_bounded_eviction(self, hass, intake):
        ch = _make_channel(hass, intake, config={})
        # Fill the cache beyond limit
        for i in range(1100):
            ch._mark_seen(f"msg_{i}")
        # Oldest IDs should be evicted
        assert ch._mark_seen("msg_0") is False  # evicted, treated as new
        # Recent IDs should still be tracked
        assert ch._mark_seen("msg_1099") is True

    @pytest.mark.asyncio
    async def test_duplicate_message_skipped(self, hass, intake):
        ch = _make_channel(hass, intake, config={"dm_policy": "open"})
        ch._bot_id = "bot"
        ch._rate_limiter.allow = MagicMock(return_value=True)
        ch._should_respond = MagicMock(return_value=True)
        hass.data["homeclaw"] = {"agents": {"openai": object()}}

        message = {
            "id": "dup1",
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }

        # First call dispatches normally
        await ch._handle_gateway_message(message)
        assert len(hass.tasks) == 1

        # Second call with same ID is dropped
        await ch._handle_gateway_message(message)
        assert len(hass.tasks) == 1  # no new task created

    @pytest.mark.asyncio
    async def test_message_without_id_still_processed(self, hass, intake):
        """Messages without 'id' field should not crash dedup."""
        ch = _make_channel(hass, intake, config={"dm_policy": "open"})
        ch._bot_id = "bot"
        ch._rate_limiter.allow = MagicMock(return_value=True)
        ch._should_respond = MagicMock(return_value=True)
        hass.data["homeclaw"] = {"agents": {"openai": object()}}

        message = {
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }
        await ch._handle_gateway_message(message)
        assert len(hass.tasks) == 1


class TestPairingSpamPrevention:
    """Regression tests for Bug 1: pairing prompt after confirmed mapping."""

    @pytest.mark.asyncio
    async def test_paired_user_in_mapping_skips_pairing(self, hass, intake):
        """User present in user_mapping never sees a pairing prompt."""
        config = {
            "dm_policy": "pairing",
            "user_mapping": {"u1": "ha_user_1"},
        }
        ch = _make_channel(hass, intake, config=config)
        ch._bot_id = "bot"
        ch.send_response = AsyncMock()

        message = {
            "id": "m1",
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }

        handled = await ch._handle_pairing_message(message)
        assert handled is False  # not handled by pairing = proceeds to normal path
        ch.send_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_paired_user_builds_envelope(self, hass, intake):
        """User in user_mapping can build envelope even without allowed_ids."""
        config = {
            "dm_policy": "pairing",
            "user_mapping": {"u1": "ha_user_1"},
        }
        ch = _make_channel(hass, intake, config=config)
        ch._bot_id = "bot"
        ch._rate_limiter.allow = MagicMock(return_value=True)
        ch._should_respond = MagicMock(return_value=True)

        message = {
            "id": "m1",
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }
        envelope = ch._build_envelope(message)
        assert envelope is not None
        assert envelope.sender_id == "u1"


class TestDiscordProviderModel:
    """Regression tests for Bug 3: provider/model from user preferences."""

    @pytest.mark.asyncio
    async def test_resolve_provider_model_from_prefs(self, hass, intake, monkeypatch):
        """_resolve_provider_model returns prefs when provider is available."""
        hass.data["homeclaw"] = {"agents": {"gemini_oauth": object()}}
        ch = _make_channel(hass, intake, config={})

        storage = MagicMock()
        storage.get_preferences = AsyncMock(
            return_value={
                "default_provider": "gemini_oauth",
                "default_model": "gemini-2.5-pro",
            }
        )
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.get_storage",
            lambda _h, _u: storage,
        )

        provider, model = await ch._resolve_provider_model("user1")
        assert provider == "gemini_oauth"
        assert model == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_resolve_provider_model_fallback_unavailable(
        self, hass, intake, monkeypatch
    ):
        """Falls back to None when preferred provider is not in agents."""
        hass.data["homeclaw"] = {"agents": {"openai": object()}}
        ch = _make_channel(hass, intake, config={})

        storage = MagicMock()
        storage.get_preferences = AsyncMock(
            return_value={
                "default_provider": "nonexistent_provider",
                "default_model": "x",
            }
        )
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.get_storage",
            lambda _h, _u: storage,
        )

        provider, model = await ch._resolve_provider_model("user1")
        assert provider is None
        assert model is None

    @pytest.mark.asyncio
    async def test_resolve_provider_model_empty_prefs(self, hass, intake, monkeypatch):
        """Returns (None, None) when no preferences set."""
        hass.data["homeclaw"] = {"agents": {"openai": object()}}
        ch = _make_channel(hass, intake, config={})

        storage = MagicMock()
        storage.get_preferences = AsyncMock(return_value={})
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.get_storage",
            lambda _h, _u: storage,
        )

        provider, model = await ch._resolve_provider_model("user1")
        assert provider is None
        assert model is None

    @pytest.mark.asyncio
    async def test_run_stream_passes_provider_model(self, hass, intake, monkeypatch):
        """_run_stream passes resolved provider/model to intake."""
        hass.data["homeclaw"] = {"agents": {"gemini_oauth": object()}}
        ch = _make_channel(hass, intake, config={})

        storage = MagicMock()
        storage.get_preferences = AsyncMock(
            return_value={
                "default_provider": "gemini_oauth",
                "default_model": "gemini-2.5-pro",
            }
        )
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.get_storage",
            lambda _h, _u: storage,
        )

        captured_kwargs = {}

        async def _capture_stream(*args, **kwargs):
            captured_kwargs.update(kwargs)
            yield TextEvent(content="ok")
            yield CompletionEvent(messages=[])

        intake.process_message_stream = _capture_stream

        env = SimpleNamespace(text="hi", ha_user_id="user1")
        await ch._run_stream(env, "s1", [])

        assert captured_kwargs.get("provider") == "gemini_oauth"
        assert captured_kwargs.get("model") == "gemini-2.5-pro"


class TestDuplicateNeverProducesMixedBehavior:
    """Regression test for Bug 4: same message ID cannot produce both pairing + LLM."""

    @pytest.mark.asyncio
    async def test_duplicate_id_single_path_only(self, hass, intake):
        """Even if config changes between calls, dedup prevents dual processing."""
        config = {"dm_policy": "pairing"}
        ch = _make_channel(hass, intake, config=config)
        ch._bot_id = "bot"
        ch.send_response = AsyncMock()

        message = {
            "id": "race1",
            "content": "hello",
            "channel_id": "dm1",
            "guild_id": None,
            "author": {"id": "u1", "username": "Jan", "bot": False},
        }

        # First call: pairing path (user not in allowed_ids)
        await ch._handle_gateway_message(message)
        pairing_calls = ch.send_response.await_count
        assert pairing_calls == 1  # pairing prompt sent

        # Simulate config update (user paired between calls)
        ch._config["user_mapping"] = {"u1": "ha_user_1"}
        ch._config["allowed_ids"] = ["u1"]

        # Second call with same message ID: dedup blocks it entirely
        await ch._handle_gateway_message(message)
        assert ch.send_response.await_count == pairing_calls  # no new sends
        assert len(hass.tasks) == 0  # no LLM task created


class TestHistoryLimit:
    """Tests for history_limit config in _load_history."""

    @pytest.mark.asyncio
    async def test_load_history_respects_history_limit(self, hass, intake):
        """_load_history truncates to history_limit from config."""
        ch = _make_channel(hass, intake, config={"history_limit": 3})
        storage = MagicMock()

        messages = [
            Message(
                message_id=f"m{i}",
                session_id="s1",
                role="user",
                content=f"msg {i}",
                timestamp=f"t{i}",
            )
            for i in range(10)
        ]
        storage.get_session_messages = AsyncMock(return_value=messages)
        history = await ch._load_history(storage, "s1")

        assert len(history) == 3
        # Should be the LAST 3 messages
        assert history[0]["content"] == "msg 7"
        assert history[2]["content"] == "msg 9"

    @pytest.mark.asyncio
    async def test_load_history_no_limit_returns_all(self, hass, intake):
        """_load_history returns all messages when history_limit is 0 or absent."""
        ch = _make_channel(hass, intake, config={})
        storage = MagicMock()

        messages = [
            Message(
                message_id=f"m{i}",
                session_id="s1",
                role="user",
                content=f"msg {i}",
                timestamp=f"t{i}",
            )
            for i in range(10)
        ]
        storage.get_session_messages = AsyncMock(return_value=messages)
        history = await ch._load_history(storage, "s1")

        assert len(history) == 10
