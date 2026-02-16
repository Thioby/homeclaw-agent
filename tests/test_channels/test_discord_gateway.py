"""Tests for Discord gateway client."""

from __future__ import annotations

import pytest

from custom_components.homeclaw.channels.discord.gateway import (
    OP_DISPATCH,
    OP_HEARTBEAT_ACK,
    OP_HELLO,
    OP_INVALID_SESSION,
    OP_RECONNECT,
    DiscordGateway,
    _ReconnectRequested,
)


@pytest.fixture
def gateway():
    async def _on_message(_msg):
        return None

    async def _on_ready(_user):
        return None

    return DiscordGateway(
        token="abc",
        intents=1,
        on_message=_on_message,
        on_ready=_on_ready,
    )


@pytest.mark.asyncio
class TestDiscordGateway:
    async def test_hello_sends_identify(self, gateway, monkeypatch):
        called = {"identify": 0, "resume": 0}

        async def _identify():
            called["identify"] += 1

        async def _resume():
            called["resume"] += 1

        monkeypatch.setattr(gateway, "_start_heartbeat", _identify)
        monkeypatch.setattr(gateway, "_send_identify", _identify)
        monkeypatch.setattr(gateway, "_send_resume", _resume)

        payload = '{"op": 10, "d": {"heartbeat_interval": 45000}}'
        await gateway._handle_payload(payload)
        assert called["identify"] == 2
        assert called["resume"] == 0

    async def test_hello_sends_resume_when_session_known(self, gateway, monkeypatch):
        gateway._session_id = "sid"
        gateway._sequence = 42
        called = {"resume": 0}

        async def _noop():
            return None

        async def _resume():
            called["resume"] += 1

        monkeypatch.setattr(gateway, "_start_heartbeat", _noop)
        monkeypatch.setattr(gateway, "_send_identify", _noop)
        monkeypatch.setattr(gateway, "_send_resume", _resume)

        payload = '{"op": 10, "d": {"heartbeat_interval": 1000}}'
        await gateway._handle_payload(payload)
        assert called["resume"] == 1

    async def test_heartbeat_ack_sets_flag(self, gateway):
        gateway._heartbeat_ack = False
        payload = f'{{"op": {OP_HEARTBEAT_ACK}, "d": null}}'
        await gateway._handle_payload(payload)
        assert gateway._heartbeat_ack is True

    async def test_dispatch_ready_updates_resume_state(self, gateway):
        seen = {"ready": False}

        async def _on_ready(user):
            seen["ready"] = user["id"] == "u1"

        gateway._on_ready = _on_ready
        payload = (
            '{"op": 0, "t": "READY", "s": 7, '
            '"d": {"session_id": "sid", "resume_gateway_url": "wss://x", "user": {"id": "u1"}}}'
        )
        await gateway._handle_payload(payload)
        assert gateway._session_id == "sid"
        assert gateway._resume_url == "wss://x"
        assert gateway._sequence == 7
        assert seen["ready"] is True

    async def test_dispatch_message_create_calls_handler(self, gateway):
        seen = {"called": False}

        async def _on_message(message):
            seen["called"] = message["id"] == "m1"

        gateway._on_message = _on_message
        payload = '{"op": 0, "t": "MESSAGE_CREATE", "d": {"id": "m1"}}'
        await gateway._handle_payload(payload)
        assert seen["called"] is True

    async def test_dispatch_drops_duplicate_sequence(self, gateway):
        calls = {"count": 0}

        async def _on_message(_message):
            calls["count"] += 1

        gateway._on_message = _on_message
        first = '{"op": 0, "t": "MESSAGE_CREATE", "s": 10, "d": {"id": "m1"}}'
        dup = '{"op": 0, "t": "MESSAGE_CREATE", "s": 10, "d": {"id": "m1"}}'

        await gateway._handle_payload(first)
        await gateway._handle_payload(dup)

        assert calls["count"] == 1

    async def test_invalid_session_resets_last_dispatched_seq(self, gateway):
        gateway._last_dispatched_seq = 99
        payload = f'{{"op": {OP_INVALID_SESSION}, "d": false}}'
        with pytest.raises(_ReconnectRequested):
            await gateway._handle_payload(payload)
        assert gateway._last_dispatched_seq is None

    async def test_reconnect_opcode_raises(self, gateway):
        payload = f'{{"op": {OP_RECONNECT}, "d": null}}'
        with pytest.raises(_ReconnectRequested):
            await gateway._handle_payload(payload)

    async def test_invalid_session_clears_state(self, gateway):
        gateway._session_id = "sid"
        gateway._sequence = 4
        gateway._resume_url = "wss://resume"
        payload = f'{{"op": {OP_INVALID_SESSION}, "d": false}}'
        with pytest.raises(_ReconnectRequested):
            await gateway._handle_payload(payload)
        assert gateway._session_id is None
        assert gateway._sequence is None
        assert gateway._resume_url is None

    async def test_unknown_dispatch_is_ignored(self, gateway):
        payload = f'{{"op": {OP_DISPATCH}, "t": "OTHER", "d": {{}}}}'
        await gateway._handle_payload(payload)

    async def test_connect_clears_resume_url_on_generic_error(
        self, gateway, monkeypatch
    ):
        gateway._resume_url = "wss://broken-resume"

        async def _connect_once():
            raise RuntimeError("boom")

        async def _reset_state():
            gateway._running = False

        monkeypatch.setattr(gateway, "_connect_once", _connect_once)
        monkeypatch.setattr(gateway, "_reset_connection_state", _reset_state)

        await gateway.connect()
        assert gateway._resume_url is None
