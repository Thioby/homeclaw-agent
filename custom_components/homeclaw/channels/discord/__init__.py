"""Discord external channel for Homeclaw."""

from __future__ import annotations

import asyncio
import collections
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ...const import DOMAIN
from ...core.events import ErrorEvent, TextEvent
from ...storage import Message
from ..base import Channel, ChannelRegistry, ChannelTarget, MessageEnvelope
from .gateway import DiscordGateway
from .helpers import (
    chunk_text,
    set_last_target,
    get_storage,
    is_dm_allowed,
    is_group_allowed,
    normalize_id_list,
)
from .pairing import create_pairing_request, extract_pairing_code, get_request_by_code
from .rest import DiscordRestClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ...storage import SessionStorage
    from ..intake import MessageIntake

_LOGGER = logging.getLogger(__name__)

_SEEN_IDS_MAX = 1000

# Task supervision: max full-gateway restarts within a window.
_MAX_SUPERVISOR_RESTARTS = 3
_SUPERVISOR_WINDOW_S = 3600  # 1 hour


@ChannelRegistry.register("discord")
class DiscordChannel(Channel):
    """Discord channel implementation using Gateway + REST clients."""

    id = "discord"
    name = "Discord"

    def __init__(
        self,
        hass: HomeAssistant,
        intake: MessageIntake,
        config: dict[str, Any],
    ) -> None:
        super().__init__(hass, intake, config)
        self._bot_id = ""
        self._gateway: DiscordGateway | None = None
        self._rest: DiscordRestClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._supervisor_task: asyncio.Task[None] | None = None
        self._semaphore = asyncio.Semaphore(
            max(1, int(config.get("max_concurrent", 3)))
        )
        self._seen_message_ids: collections.OrderedDict[str, None] = (
            collections.OrderedDict()
        )
        self._shutting_down = False

    async def async_setup(self) -> None:
        """Start Discord gateway in the background."""
        token = self._config.get("bot_token") or self._config.get(
            "discord_bot_token", ""
        )
        if not token:
            _LOGGER.error("Discord bot token is missing, channel disabled")
            return

        # Diagnostic: log loaded pairing state so we can verify persistence.
        allowed = self._config.get("allowed_ids", [])
        mapping = self._config.get("user_mapping", {})
        _LOGGER.info(
            "Discord channel setup: allowed_ids=%d, user_mapping=%d, dm_policy=%s",
            len(allowed) if isinstance(allowed, (list, set)) else 0,
            len(mapping) if isinstance(mapping, dict) else 0,
            self._config.get("dm_policy", "pairing"),
        )

        self._rest = DiscordRestClient(token)
        self._gateway = DiscordGateway(
            token=token,
            intents=self._compute_intents(),
            on_message=self._handle_gateway_message,
            on_ready=self._on_ready,
        )
        self._shutting_down = False
        self._supervisor_task = asyncio.create_task(
            self._supervise_gateway(), name="homeclaw_discord_supervisor"
        )
        _LOGGER.info("Discord channel started")

    async def _supervise_gateway(self) -> None:
        """Supervise the gateway task, restarting on crash.

        If the gateway exhausts all reconnect attempts and exits, this
        supervisor will re-launch it (up to ``_MAX_SUPERVISOR_RESTARTS``
        within ``_SUPERVISOR_WINDOW_S``).  This mirrors OpenClaw's
        ``shouldStopOnError`` pattern where only fatal errors stop the bot.
        """
        restart_times: list[float] = []
        while not self._shutting_down:
            if not self._gateway:
                return
            self._task = asyncio.create_task(
                self._gateway.connect(), name="homeclaw_discord_gateway"
            )
            try:
                await self._task
            except asyncio.CancelledError:
                return
            except Exception:
                _LOGGER.exception("Discord gateway task crashed")

            if self._shutting_down:
                return

            # Prune restart timestamps outside the window.
            now = asyncio.get_event_loop().time()
            restart_times = [t for t in restart_times if now - t < _SUPERVISOR_WINDOW_S]

            if len(restart_times) >= _MAX_SUPERVISOR_RESTARTS:
                _LOGGER.critical(
                    "Discord gateway restarted %d times in %ds — giving up",
                    _MAX_SUPERVISOR_RESTARTS,
                    _SUPERVISOR_WINDOW_S,
                )
                return

            restart_times.append(now)
            _LOGGER.warning(
                "Discord gateway stopped — supervisor restarting (%d/%d in window)",
                len(restart_times),
                _MAX_SUPERVISOR_RESTARTS,
            )
            await asyncio.sleep(10)  # brief cooldown before full restart

    async def async_teardown(self) -> None:
        """Stop gateway and close REST client."""
        self._shutting_down = True
        if self._gateway:
            await self._gateway.close()
        if self._rest:
            await self._rest.close()
        for task in (self._task, self._supervisor_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._task = None
        self._supervisor_task = None

    @property
    def is_available(self) -> bool:
        """Whether Discord gateway is connected."""
        return bool(self._gateway and self._gateway.is_connected)

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        """Send Discord message, chunked to 2000 chars."""
        if not self._rest:
            return
        content = text.strip() or "(no response)"
        for chunk in chunk_text(content, 2000):
            await self._rest.create_message(target.target_id, chunk)

    async def send_typing_indicator(self, target: ChannelTarget) -> None:
        """Trigger typing indicator for channel target."""
        if not self._rest:
            return
        try:
            await self._rest.trigger_typing(target.target_id)
        except Exception as err:
            _LOGGER.debug("Discord typing indicator failed: %s", err)

    async def _on_ready(self, user_info: dict[str, Any]) -> None:
        """Save bot identity from READY payload."""
        self._bot_id = str(user_info.get("id", ""))
        _LOGGER.info(
            "Discord bot connected as %s", user_info.get("username", "unknown")
        )

    def _mark_seen(self, message_id: str) -> bool:
        """Record message ID and return True if already seen (duplicate)."""
        if message_id in self._seen_message_ids:
            return True
        self._seen_message_ids[message_id] = None
        while len(self._seen_message_ids) > _SEEN_IDS_MAX:
            self._seen_message_ids.popitem(last=False)
        return False

    async def _handle_gateway_message(self, message: dict[str, Any]) -> None:
        """Handle MESSAGE_CREATE from gateway and dispatch processing task."""
        msg_id = message.get("id")
        if msg_id and self._mark_seen(str(msg_id)):
            _LOGGER.debug("Discord drop: duplicate message id=%s", msg_id)
            return

        _LOGGER.debug(
            "Discord MESSAGE_CREATE id=%s channel=%s guild=%s",
            msg_id,
            message.get("channel_id"),
            message.get("guild_id"),
        )
        if await self._handle_pairing_message(message):
            return
        envelope = self._build_envelope(message)
        if envelope is None:
            return
        set_last_target(
            self._hass,
            ha_user_id=envelope.ha_user_id,
            target_id=envelope.target.target_id,
            sender_id=envelope.sender_id,
            is_group=envelope.is_group,
        )
        self._hass.async_create_task(self._process_with_limit(envelope))

    async def _handle_pairing_message(self, message: dict[str, Any]) -> bool:
        """Handle DM pairing flow for users blocked by pairing policy."""
        if message.get("guild_id") is not None:
            return False

        if str(self._config.get("dm_policy", "")).lower() != "pairing":
            return False

        author = message.get("author", {})
        sender_id = str(author.get("id", ""))
        if not sender_id or sender_id == self._bot_id or author.get("bot", False):
            return True

        channel_id = str(message.get("channel_id", ""))
        if not channel_id:
            return True

        if is_dm_allowed(self._config, sender_id, channel_id):
            _LOGGER.debug(
                "Discord DM allowed for sender=%s (already paired/allowed)", sender_id
            )
            return False

        _LOGGER.info(
            "Discord DM blocked by pairing policy sender=%s "
            "(allowed_ids=%d, user_mapping=%d)",
            sender_id,
            len(self._config.get("allowed_ids", [])),
            len(self._config.get("user_mapping", {})),
        )

        content = str(message.get("content", "")).strip()
        code = extract_pairing_code(content)
        if code and get_request_by_code(self._hass, code):
            await self.send_response(
                ChannelTarget(channel_id="discord", target_id=channel_id),
                "Pairing code received. Now open Homeclaw panel and ask: confirm discord pairing code "
                f"{code}",
            )
            _LOGGER.debug("Discord pairing code received sender=%s", sender_id)
            return True

        request = create_pairing_request(
            self._hass,
            sender_id=sender_id,
            target_id=channel_id,
        )
        await self.send_response(
            ChannelTarget(channel_id="discord", target_id=channel_id),
            "Discord pairing is required. In Homeclaw panel, ask: confirm discord pairing code "
            f"{request['code']}",
        )
        _LOGGER.info("Discord pairing request created sender=%s", sender_id)
        return True

    async def _process_with_limit(self, envelope: MessageEnvelope) -> None:
        """Process one message under channel concurrency limit."""
        async with self._semaphore:
            await self._process_and_respond(envelope)

    def _build_envelope(self, message: dict[str, Any]) -> MessageEnvelope | None:
        """Parse Discord payload into a normalized envelope."""
        author = message.get("author", {})
        sender_id = str(author.get("id", ""))
        if not sender_id or sender_id == self._bot_id or author.get("bot", False):
            _LOGGER.debug("Discord drop: bot/self message")
            return None

        guild_id = message.get("guild_id")
        channel_id = str(message.get("channel_id", ""))
        if not channel_id:
            _LOGGER.debug("Discord drop: missing channel_id")
            return None
        if guild_id is not None:
            if not is_group_allowed(self._config, sender_id, channel_id):
                _LOGGER.debug(
                    "Discord drop: group policy blocked sender=%s channel=%s",
                    sender_id,
                    channel_id,
                )
                return None
        elif not is_dm_allowed(self._config, sender_id, channel_id):
            _LOGGER.debug(
                "Discord drop: dm policy blocked sender=%s channel=%s",
                sender_id,
                channel_id,
            )
            return None

        if not self._rate_limiter.allow(sender_id):
            _LOGGER.debug("Discord drop: rate limited sender=%s", sender_id)
            return None
        if not self._should_respond(message):
            _LOGGER.debug("Discord drop: should_respond=false")
            return None

        text = self._strip_mention(message.get("content", ""))
        if not text.strip():
            _LOGGER.debug("Discord drop: empty content after mention strip")
            return None

        thread = message.get("thread") or {}
        thread_id = str(thread.get("id", "")) if thread else None
        envelope = MessageEnvelope(
            text=text,
            channel="discord",
            sender_id=sender_id,
            sender_name=author.get("username", "Discord User"),
            target=ChannelTarget(
                channel_id="discord",
                target_id=channel_id,
                extra={"guild_id": str(guild_id)} if guild_id else {},
            ),
            ha_user_id=self._resolve_user_id(sender_id),
            is_group=guild_id is not None,
            thread_id=thread_id,
        )
        _LOGGER.debug(
            "Discord envelope built sender=%s mapped_user=%s target=%s",
            sender_id,
            envelope.ha_user_id,
            channel_id,
        )
        return envelope

    def _should_respond(self, message: dict[str, Any]) -> bool:
        """Decide if channel should answer this message."""
        if message.get("guild_id") is None:
            return True

        if not bool(self._config.get("require_mention", True)):
            return True

        mentions = message.get("mentions", [])
        if any(str(m.get("id", "")) == self._bot_id for m in mentions):
            return True

        allowed_channels = normalize_id_list(
            self._config.get("auto_respond_channels")
            or self._config.get("discord_auto_respond_channels")
        )
        channel_id = str(message.get("channel_id", ""))
        return channel_id in allowed_channels

    def _strip_mention(self, content: str) -> str:
        """Strip direct bot mention from message content."""
        if not self._bot_id:
            return content.strip()
        pattern = rf"^\s*<@!?{re.escape(self._bot_id)}>\s*"
        return re.sub(pattern, "", content).strip()

    async def _process_and_respond(self, envelope: MessageEnvelope) -> None:
        """Run AI pipeline for one envelope and send response."""
        session_id = await self._get_or_create_session_id(envelope)
        if not session_id:
            return

        storage = get_storage(self._hass, envelope.ha_user_id)
        stop_typing = asyncio.Event()
        typing_task = self._hass.async_create_task(
            self._typing_loop(envelope.target, stop_typing)
        )
        await self._save_message(storage, session_id, "user", envelope.text)

        try:
            history = await self._load_history(storage, session_id)
            answer = await self._run_stream(envelope, session_id, history)
            await self.send_response(envelope.target, answer)
            _LOGGER.debug(
                "Discord sent reply session=%s target=%s len=%s",
                session_id,
                envelope.target.target_id,
                len(answer),
            )
            await self._save_message(storage, session_id, "assistant", answer)
        finally:
            stop_typing.set()
            if not typing_task.done():
                await typing_task

    async def _typing_loop(
        self, target: ChannelTarget, stop_event: asyncio.Event
    ) -> None:
        """Send periodic typing indicator while reply is being generated."""
        while not stop_event.is_set():
            await self.send_typing_indicator(target)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=7)
            except asyncio.TimeoutError:
                continue

    async def _resolve_provider_model(
        self, ha_user_id: str
    ) -> tuple[str | None, str | None]:
        """Resolve provider and model from user preferences with fallback.

        Returns:
            Tuple of (provider, model). Either or both may be None for fallback.
        """
        try:
            storage = get_storage(self._hass, ha_user_id)
            prefs = await storage.get_preferences()
        except Exception:
            _LOGGER.debug("Discord: could not load preferences for user=%s", ha_user_id)
            return None, None

        provider = prefs.get("default_provider")
        model = prefs.get("default_model")

        # Validate provider is actually available
        if provider:
            agents = self._hass.data.get(DOMAIN, {}).get("agents", {})
            if provider not in agents:
                _LOGGER.debug(
                    "Discord: preferred provider %s not available, falling back",
                    provider,
                )
                return None, None

        return provider or None, model or None

    async def _run_stream(
        self,
        envelope: MessageEnvelope,
        session_id: str,
        history: list[dict[str, Any]],
    ) -> str:
        """Execute message intake stream and return final assistant text.

        Tool calls are executed internally by the query processor's multi-turn
        loop. We only collect the final text — same as Web UI behavior.
        """
        provider, model = await self._resolve_provider_model(envelope.ha_user_id)
        accumulated = ""
        try:
            async for event in self._intake.process_message_stream(
                envelope.text,
                user_id=envelope.ha_user_id,
                session_id=session_id,
                provider=provider,
                model=model,
                channel_source="discord",
                conversation_history=history,
            ):
                if isinstance(event, TextEvent):
                    accumulated += event.content
                elif isinstance(event, ErrorEvent):
                    return "Sorry, I encountered an error."
        except Exception:
            _LOGGER.exception("Discord message processing failed")
            return "Sorry, something went wrong."
        return accumulated.strip() or "(no response)"

    async def _get_or_create_session_id(self, envelope: MessageEnvelope) -> str:
        """Resolve existing channel session or create a new one."""
        storage = get_storage(self._hass, envelope.ha_user_id)
        key = self._session_key(envelope)
        for session in await storage.list_sessions():
            if session.metadata.get("external_session_key") == key:
                return session.session_id

        pref_provider, _ = await self._resolve_provider_model(envelope.ha_user_id)
        provider = pref_provider or self._default_provider()
        metadata = {
            "channel": "discord",
            "external_session_key": key,
            "channel_target": {"channel_id": envelope.target.target_id},
            "sender_name": envelope.sender_name,
        }
        title = f"[Discord] {envelope.text[:30]}"
        created = await storage.create_session(
            provider=provider, title=title, metadata=metadata
        )
        return created.session_id

    async def _save_message(
        self,
        storage: SessionStorage,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Persist one message in session storage."""
        now = datetime.now(timezone.utc).isoformat()
        message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now,
            status="completed",
        )
        await storage.add_message(session_id, message)

    async def _load_history(
        self,
        storage: SessionStorage,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Load session history in query-processor format.

        Respects the channel's ``history_limit`` config to cap history size.
        Uses the same message reconstruction as Web Panel to properly handle
        tool_use/tool_result messages for the AI provider.
        """
        messages = await storage.get_session_messages(session_id)

        # Default to 40 messages (~20 turns) to prevent compaction re-trigger.
        # Without a limit, long sessions reload ALL messages from storage on
        # every turn, causing compaction to fire repeatedly (storage is not
        # modified by compaction — only the in-memory list is trimmed).
        limit = int(self._config.get("history_limit", 40))
        if limit and len(messages) > limit:
            messages = messages[-limit:]

        # Use same reconstruction as Web Panel for proper tool message handling
        from ...ws_handlers.chat import _build_conversation_history

        return await _build_conversation_history(self._hass, messages)

    def _default_provider(self) -> str:
        """Return configured provider or first available provider."""
        configured = self._config.get("provider")
        if configured:
            return str(configured)
        agents = self._hass.data.get(DOMAIN, {}).get("agents", {})
        return next(iter(agents.keys()), "anthropic")

    def _compute_intents(self) -> int:
        """Compute required Discord intents bitmask."""
        return (1 << 0) | (1 << 9) | (1 << 12) | (1 << 15)
