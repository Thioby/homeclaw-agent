"""Minimal Discord Gateway client (v10) for Homeclaw channels.

Resilient WebSocket client with exponential backoff, HELLO timeout
(zombie detection), and reconnect attempt limits modeled on OpenClaw's
Carbon gateway patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Awaitable, Callable

import aiohttp

_LOGGER = logging.getLogger(__name__)

OP_DISPATCH = 0
OP_HEARTBEAT = 1
OP_IDENTIFY = 2
OP_RESUME = 6
OP_RECONNECT = 7
OP_INVALID_SESSION = 9
OP_HELLO = 10
OP_HEARTBEAT_ACK = 11

# Reconnect tuning — aligned with OpenClaw defaults.
_MAX_RECONNECT_ATTEMPTS = 50
_BASE_RECONNECT_DELAY = 5.0  # seconds
_MAX_RECONNECT_DELAY = 120.0  # seconds
_JITTER_FACTOR = 0.25
_HELLO_TIMEOUT_S = 30.0  # zombie detection


class _ReconnectRequested(Exception):
    """Internal signal to reconnect the gateway loop."""


class DiscordGateway:
    """Lightweight Discord Gateway websocket client.

    Handles HELLO/IDENTIFY/RESUME, heartbeat, reconnects, and forwards
    MESSAGE_CREATE events to callback handlers.
    """

    GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"

    def __init__(
        self,
        *,
        token: str,
        intents: int,
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
        on_ready: Callable[[dict[str, Any]], Awaitable[None]],
        reconnect_delay: float = _BASE_RECONNECT_DELAY,
        max_reconnect_attempts: int = _MAX_RECONNECT_ATTEMPTS,
    ) -> None:
        self._token = token.strip()
        self._intents = intents
        self._on_message = on_message
        self._on_ready = on_ready
        self._base_reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts

        self._running = False
        self._is_connected = False
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None

        self._sequence: int | None = None
        self._last_dispatched_seq: int | None = None
        self._session_id: str | None = None
        self._resume_url: str | None = None

        self._heartbeat_interval = 0.0
        self._heartbeat_ack = True
        self._heartbeat_task: asyncio.Task[None] | None = None

        self._reconnect_attempts = 0
        self._hello_received = False

    @property
    def is_connected(self) -> bool:
        """Whether websocket is currently connected and running."""
        return self._is_connected and self._running

    async def connect(self) -> None:
        """Run the gateway loop until ``close()`` is called or attempts exhausted."""
        self._running = True
        self._reconnect_attempts = 0
        while self._running:
            is_resume = bool(self._session_id and self._sequence is not None)
            try:
                await self._connect_once()
            except _ReconnectRequested:
                self._reconnect_attempts += 1
                _LOGGER.info(
                    "Discord gateway reconnect requested (attempt %d/%d, %s)",
                    self._reconnect_attempts,
                    self._max_reconnect_attempts,
                    "resume" if is_resume else "fresh",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self._reconnect_attempts += 1
                _LOGGER.exception(
                    "Discord gateway error (attempt %d/%d)",
                    self._reconnect_attempts,
                    self._max_reconnect_attempts,
                )
                # Stale resume endpoint — force fresh identify.
                self._resume_url = None
                # Close old session to avoid stale DNS / dead pool.
                await self._close_session()
            finally:
                await self._reset_connection_state()

            if not self._running:
                break

            if self._reconnect_attempts >= self._max_reconnect_attempts:
                _LOGGER.critical(
                    "Discord gateway exhausted %d reconnect attempts — stopping",
                    self._max_reconnect_attempts,
                )
                self._running = False
                break

            delay = self._backoff_delay()
            _LOGGER.info("Discord gateway reconnecting in %.1fs", delay)
            await asyncio.sleep(delay)

        # Clean up aiohttp session when the loop exits permanently.
        await self._close_session()

    async def close(self) -> None:
        """Stop reconnect loop and close active websocket/session."""
        self._running = False
        await self._stop_heartbeat()
        await self._close_ws()
        await self._close_session()

    async def _connect_once(self) -> None:
        """Open one websocket connection and process events until disconnect.

        Includes a HELLO timeout to detect zombie connections where the WS
        opens but Discord never sends OP_HELLO (modeled on OpenClaw).
        """
        self._hello_received = False
        url = self._resume_url or self.GATEWAY_URL
        session = await self._get_session()

        hello_timer: asyncio.TimerHandle | None = None
        loop = asyncio.get_running_loop()

        def _hello_timeout_cb() -> None:
            if not self._hello_received and self._ws and not self._ws.closed:
                _LOGGER.warning(
                    "Discord HELLO not received within %.0fs — forcing reconnect",
                    _HELLO_TIMEOUT_S,
                )
                # Fire-and-forget with exception suppression to avoid
                # "Task exception was never retrieved" warnings.
                task = asyncio.ensure_future(self._close_ws())
                task.add_done_callback(
                    lambda t: t.exception() if not t.cancelled() else None
                )

        async with session.ws_connect(url, heartbeat=30) as ws:
            self._ws = ws
            self._is_connected = True

            # Start HELLO timeout (zombie detection).
            hello_timer = loop.call_later(_HELLO_TIMEOUT_S, _hello_timeout_cb)

            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_payload(msg.data)
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSE,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        raise _ReconnectRequested
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        raise _ReconnectRequested
            finally:
                if hello_timer is not None:
                    hello_timer.cancel()

    async def _handle_payload(self, raw_payload: str) -> None:
        """Parse and process one gateway payload."""
        payload = json.loads(raw_payload)
        op = payload.get("op")
        data = payload.get("d")
        event_type = payload.get("t")
        seq = payload.get("s")

        if seq is not None:
            self._sequence = seq

        if op == OP_HELLO:
            interval_ms = data.get("heartbeat_interval", 45_000)
            await self._handle_hello(interval_ms)
            return

        if op == OP_HEARTBEAT_ACK:
            self._heartbeat_ack = True
            return

        if op == OP_RECONNECT:
            raise _ReconnectRequested

        if op == OP_INVALID_SESSION:
            await self._handle_invalid_session(data)
            return

        if op == OP_HEARTBEAT:
            await self._send_heartbeat()
            return

        if op != OP_DISPATCH:
            return

        if (
            seq is not None
            and self._last_dispatched_seq is not None
            and seq <= self._last_dispatched_seq
        ):
            _LOGGER.debug(
                "Discord gateway drop duplicated dispatch seq=%s last=%s type=%s",
                seq,
                self._last_dispatched_seq,
                event_type,
            )
            return

        await self._handle_dispatch(event_type, data or {})
        if seq is not None:
            self._last_dispatched_seq = seq

    async def _handle_hello(self, heartbeat_interval_ms: int) -> None:
        """Start heartbeats and send IDENTIFY or RESUME."""
        self._hello_received = True
        self._heartbeat_interval = heartbeat_interval_ms / 1000.0
        self._heartbeat_ack = True
        await self._start_heartbeat()

        if self._session_id and self._sequence is not None:
            _LOGGER.info("Discord gateway resuming session %s", self._session_id)
            await self._send_resume()
            return
        _LOGGER.info("Discord gateway identifying (fresh session)")
        await self._send_identify()

    async def _handle_invalid_session(self, resumable: bool) -> None:
        """React to INVALID_SESSION opcode."""
        if not resumable:
            self._session_id = None
            self._sequence = None
            self._last_dispatched_seq = None
            self._resume_url = None
        await asyncio.sleep(1)
        raise _ReconnectRequested

    async def _handle_dispatch(
        self, event_type: str | None, data: dict[str, Any]
    ) -> None:
        """Dispatch gateway events to Homeclaw callbacks."""
        if event_type == "READY":
            self._session_id = data.get("session_id")
            self._resume_url = data.get("resume_gateway_url")
            self._reconnect_attempts = 0  # connected OK — reset counter
            _LOGGER.info("Discord gateway READY (session=%s)", self._session_id)
            await self._on_ready(data.get("user", {}))
            return

        if event_type == "RESUMED":
            self._reconnect_attempts = 0  # resumed OK — reset counter
            _LOGGER.info("Discord gateway RESUMED successfully")
            return

        if event_type == "MESSAGE_CREATE":
            await self._on_message(data)

    async def _start_heartbeat(self) -> None:
        """Start heartbeat task if not already running."""
        await self._stop_heartbeat()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _stop_heartbeat(self) -> None:
        """Cancel and await heartbeat task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """Send gateway heartbeats and detect missing ACKs."""
        while self._running and self._is_connected:
            await asyncio.sleep(self._heartbeat_interval)
            if not self._heartbeat_ack:
                _LOGGER.warning("Discord heartbeat ACK timeout, reconnecting")
                await self._close_ws()
                return
            self._heartbeat_ack = False
            await self._send_heartbeat()

    async def _send_identify(self) -> None:
        """Send IDENTIFY payload to Discord."""
        payload = {
            "op": OP_IDENTIFY,
            "d": {
                "token": self._token,
                "intents": self._intents,
                "properties": {
                    "os": "linux",
                    "browser": "homeclaw",
                    "device": "homeclaw",
                },
            },
        }
        await self._send(payload)

    async def _send_resume(self) -> None:
        """Send RESUME payload for session continuation."""
        payload = {
            "op": OP_RESUME,
            "d": {
                "token": self._token,
                "session_id": self._session_id,
                "seq": self._sequence,
            },
        }
        await self._send(payload)

    async def _send_heartbeat(self) -> None:
        """Send HEARTBEAT payload."""
        payload = {"op": OP_HEARTBEAT, "d": self._sequence}
        await self._send(payload)

    async def _send(self, payload: dict[str, Any]) -> None:
        """Send one JSON payload to current websocket."""
        if self._ws is None:
            return
        await self._ws.send_json(payload)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Create or return reusable aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _close_ws(self) -> None:
        """Close current websocket if open."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._ws = None

    async def _close_session(self) -> None:
        """Close and discard the aiohttp session so a fresh one is created."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    def _backoff_delay(self) -> float:
        """Exponential backoff with jitter (capped at ``_MAX_RECONNECT_DELAY``)."""
        exp = min(
            self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
            _MAX_RECONNECT_DELAY,
        )
        jitter = exp * _JITTER_FACTOR * random.random()
        return exp + jitter

    async def _reset_connection_state(self) -> None:
        """Reset state after disconnect while keeping resume data."""
        self._is_connected = False
        await self._stop_heartbeat()
        await self._close_ws()
