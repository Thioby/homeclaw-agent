# Plan: External Chat Channels (Telegram + Discord)

**Status**: REVIEWED — approved with changes by Codex (gpt-5.3) + Gemini (3-pro)
**Date**: 2026-02-16 (updated after review)
**Author**: Claude (architect)

---

## 1. Problem Statement

The Homeclaw HA integration currently has **6 message sources** (WS panel, Conversation Entity, AI Task, HA Services, Heartbeat, Subagent), each **duplicating the same ~50-line setup boilerplate**:

1. Get `HomeclawAgent` from `hass.data[DOMAIN]["agents"]`
2. `_get_tools_for_provider()`
3. `_get_rag_context(query, user_id=...)`
4. `_get_system_prompt(user_id)`
5. `get_context_window(provider, model)`
6. `memory_flush_fn` setup
7. `process_query_stream()` / `process_query()`

Adding a new external channel (Telegram, Discord) would mean copying this again.

## 2. Goals

- Enable bidirectional chat via **Telegram** and **Discord**
- Build a **Channel abstraction** that makes adding future channels trivial
- Extract shared setup into a single **MessageIntake** class
- Store external channel sessions in existing SessionStorage (visible in Svelte panel)
- **WhatsApp** deferred (no official HA integration, unofficial APIs risky)

## 3. Research Findings

### Home Assistant Native Integrations

| Platform     | Native HA | Receive Messages        | Bidirectional |
| ------------ | --------- | ----------------------- | ------------- |
| **Telegram** | Yes       | **Yes** (5 event types) | **Yes**       |
| **Discord**  | Yes       | **No** (send-only)      | **No**        |
| **WhatsApp** | **No**    | No                      | No            |

### Telegram in HA
- Full bidirectional via `telegram_bot` integration (polling mode, no internet exposure)
- Events: `telegram_text`, `telegram_command`, `telegram_callback`, `telegram_attachment`
- Event data: `text`, `chat_id`, `user_id`, `from_first`, `from_last`
- Response: `telegram_bot.send_message` service with `target: chat_id`
- Typing indicator: `telegram_bot.send_chat_action` with `action: typing`

### Discord in HA
- Native integration = send-only (`notify.discord`), useless for receiving
- **Decision**: Build custom lightweight Discord Gateway client (port from OpenClaw)
- Uses pure `aiohttp` WebSocket + REST — **zero external dependencies**

### OpenClaw Reference Architecture
- 21 channels via plugin-based `ChannelPlugin` interface
- Lightweight custom Discord client (not discord.js) — uses Discord Gateway API directly
- Unified `MsgContext` envelope for message normalization
- Central dispatcher: `dispatchInboundMessage()` → AI → `routeReply()`

## 4. Proposed Architecture

### 4.1 New Directory Structure

```
custom_components/homeclaw/channels/
├── __init__.py              # ChannelManager + auto-import channels
├── base.py                  # Channel ABC, MessageEnvelope, ChannelTarget
├── intake.py                # MessageIntake — extracted shared setup logic
├── manager.py               # ChannelManager — lifecycle, health, startup/shutdown
├── telegram.py              # TelegramChannel — hooks into HA telegram_bot events
└── discord/
    ├── __init__.py           # DiscordChannel (main)
    ├── gateway.py            # Discord Gateway WebSocket client (port from OpenClaw)
    └── rest.py               # Discord REST API client (send messages, etc.)
```

### 4.2 Pre-requisite Refactors (from review feedback)

Before implementing channels, these issues MUST be fixed:

#### 4.2.1 Expose public API on HomeclawAgent ✅

**Problem**: Current code accesses `agent._agent.process_query_stream()` (private).
`MessageIntake` and channels must NOT depend on private internals.

**Fix**: Add public methods to `HomeclawAgent`:

```python
class HomeclawAgent:
    # NEW public API — channels and intake use ONLY these
    async def stream_query(
        self,
        text: str,
        *,
        user_id: str,
        session_id: str = "",
        model: str | None = None,
        conversation_history: list[dict] | None = None,
        attachments: list | None = None,
        channel_source: str = "panel",
    ) -> AsyncGenerator[AgentEvent, None]:
        """Public streaming entry point. Builds all kwargs internally."""
        ...

    def build_query_kwargs(
        self, text: str, *, user_id: str, **overrides
    ) -> dict[str, Any]:
        """Public method to build kwargs. No more _get_* access needed."""
        ...
```

#### 4.2.2 Fix global `_current_user_id` race condition ✅

**Problem**: `hass.data[DOMAIN]["_current_user_id"]` is set/cleared around requests.
Concurrent messages from Telegram + Panel can cross-contaminate.

**Fix**: Pass `user_id` explicitly through tool execution context:

```python
# In tool_executor.py — pass user_id as call context, not global
async def execute_tool_calls(self, calls, *, user_id: str, **kwargs):
    ...
```

#### 4.2.3 Add `Session.metadata` field + storage migration ✅

**Problem**: `Session` dataclass has no `metadata` field, but channels need
`session.metadata["channel"]` for badges and routing.

**Fix**: Add field + bump storage version:

```python
@dataclass
class Session:
    # ... existing fields ...
    metadata: dict = field(default_factory=dict)  # NEW
```

Storage migration: version 1 → 2, add empty `metadata: {}` to existing sessions.

#### 4.2.4 Shadow user isolation

**Problem**: Unmapped external users fall back to `user_id="default"`, sharing storage.

**Fix**: Generate isolated shadow user IDs:

```python
# In channel base class
def _resolve_user_id(self, sender_id: str) -> str:
    """Map external sender to HA user, or create isolated shadow user."""
    mapped = self._config.get("user_mapping", {}).get(sender_id)
    if mapped:
        return mapped
    # Isolated shadow user — never shares with other users
    return f"{self.id}_{sender_id}"  # e.g. "telegram_123456789"
```

### 4.3 MessageIntake — Extracted Shared Setup

```python
class MessageIntake:
    """Centralized message entry point for all channels.

    Owns the shared setup logic: agent lookup, tools, RAG, system prompt,
    context window, memory flush. Channels call this instead of duplicating.
    Uses ONLY public HomeclawAgent API (no _agent access).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def process_message_stream(
        self,
        text: str,
        *,
        user_id: str,
        session_id: str,
        provider: str | None = None,
        model: str | None = None,
        channel_source: str = "panel",
        conversation_history: list[dict] | None = None,
        attachments: list | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Unified streaming entry point.

        Delegates to HomeclawAgent.stream_query() (public API).
        """
        agent = self._get_agent(provider)
        async for event in agent.stream_query(
            text,
            user_id=user_id,
            session_id=session_id,
            model=model,
            conversation_history=conversation_history,
            attachments=attachments,
            channel_source=channel_source,
        ):
            yield event

    async def process_message(self, text: str, **kwargs) -> dict[str, Any]:
        """Non-streaming variant. Returns {success, answer, error}."""
        agent = self._get_agent(kwargs.get("provider"))
        return await agent.process_query(text, **kwargs)

    def _get_agent(self, provider: str | None) -> HomeclawAgent:
        """Look up agent from hass.data."""
        agents = self._hass.data.get(DOMAIN, {}).get("agents", {})
        if provider and provider in agents:
            return agents[provider]
        # Fall back to first available
        if agents:
            return next(iter(agents.values()))
        raise HomeAssistantError("No AI agent configured")
```

### 4.4 ChannelManager — Lifecycle Owner

```python
class ChannelManager:
    """Manages channel lifecycle, independent of per-provider config entries.

    Owns startup/shutdown of all enabled channels. Provides health status.
    Stored at hass.data[DOMAIN]["channel_manager"].
    """

    def __init__(self, hass: HomeAssistant, intake: MessageIntake) -> None:
        self._hass = hass
        self._intake = intake
        self._channels: dict[str, Channel] = {}

    async def async_setup(self, config: dict) -> None:
        """Start all enabled channels."""
        for channel_id, channel_cls in ChannelRegistry.all().items():
            ch_config = config.get(f"channel_{channel_id}", {})
            if not ch_config.get("enabled", False):
                continue
            channel = channel_cls(self._hass, self._intake, ch_config)
            try:
                await channel.async_setup()
                self._channels[channel_id] = channel
                _LOGGER.info("Channel %s started", channel_id)
            except Exception:
                _LOGGER.exception("Failed to start channel %s", channel_id)

    async def async_teardown(self) -> None:
        """Stop all running channels (safe for HA unload)."""
        for channel_id, channel in self._channels.items():
            try:
                await channel.async_teardown()
            except Exception:
                _LOGGER.exception("Error stopping channel %s", channel_id)
        self._channels.clear()

    def get_status(self) -> dict[str, Any]:
        """Health status of all channels."""
        return {
            cid: {"available": ch.is_available, "name": ch.name}
            for cid, ch in self._channels.items()
        }
```

### 4.5 Channel ABC

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ChannelTarget:
    """Identifies where to send a response back."""
    channel_id: str           # "telegram", "discord"
    target_id: str            # chat_id (Telegram) or channel_id (Discord)
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class MessageEnvelope:
    """Normalized inbound message from any channel."""
    text: str
    channel: str              # "telegram", "discord"
    sender_id: str            # Platform-specific sender ID
    sender_name: str          # Display name
    target: ChannelTarget     # Where to send the response
    ha_user_id: str           # Resolved HA user ID (NEVER "default")
    is_group: bool = False    # True if from group chat
    thread_id: str | None = None  # Thread/topic ID if applicable
    attachments: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

class Channel(ABC):
    """Base class for all external message channels."""

    id: str                   # "telegram", "discord"
    name: str                 # Display name

    def __init__(self, hass: HomeAssistant, intake: MessageIntake, config: dict) -> None:
        self._hass = hass
        self._intake = intake
        self._config = config
        self._rate_limiter = ChannelRateLimiter(
            max_per_minute=config.get("rate_limit", 10),
            max_per_hour=config.get("rate_limit_hour", 60),
        )

    @abstractmethod
    async def async_setup(self) -> None:
        """Start listening for inbound messages."""

    @abstractmethod
    async def async_teardown(self) -> None:
        """Stop listening, cleanup resources."""

    @abstractmethod
    async def send_response(self, target: ChannelTarget, text: str) -> None:
        """Send a text response back to the originating channel."""

    async def send_typing_indicator(self, target: ChannelTarget) -> None:
        """Show typing indicator. Override if supported."""

    async def send_media(self, target: ChannelTarget, data: bytes, mime: str) -> None:
        """Send media back. Override if supported."""

    @property
    def is_available(self) -> bool:
        """Whether this channel is connected and operational."""
        return True

    # --- Shared helpers (used by all channels) ---

    def _resolve_user_id(self, sender_id: str) -> str:
        """Map external sender to HA user or create isolated shadow user."""
        mapped = self._config.get("user_mapping", {}).get(sender_id)
        return mapped if mapped else f"{self.id}_{sender_id}"

    def _session_key(self, envelope: MessageEnvelope) -> str:
        """Deterministic session key based on channel context.

        DM:     "{channel}_{sender_id}"
        Group:  "{channel}_group_{target_id}"
        Thread: "{channel}_thread_{thread_id}"
        """
        if envelope.thread_id:
            return f"{self.id}_thread_{envelope.thread_id}"
        if envelope.is_group:
            return f"{self.id}_group_{envelope.target.target_id}"
        return f"{self.id}_{envelope.sender_id}"

    def _is_allowed(self, sender_id: str, target_id: str) -> bool:
        """Check if sender/target is in allowlist."""
        allowed = self._config.get("allowed_ids", [])
        if not allowed:
            return True  # No allowlist = allow all (opt-in security)
        return sender_id in allowed or target_id in allowed
```

### 4.6 TelegramChannel Implementation

```python
@ChannelRegistry.register("telegram")
class TelegramChannel(Channel):
    """Telegram channel via HA's native telegram_bot integration.

    Hooks into HA event bus for telegram events.
    Requires telegram_bot integration configured in HA (polling mode recommended).
    """

    id = "telegram"
    name = "Telegram"

    async def async_setup(self) -> None:
        """Subscribe to HA telegram events."""
        # Guard: verify telegram_bot is available
        if not self._hass.services.has_service("telegram_bot", "send_message"):
            _LOGGER.error(
                "telegram_bot integration not configured. "
                "Telegram channel cannot start."
            )
            return

        self._unsubs = [
            self._hass.bus.async_listen("telegram_text", self._handle_text),
            self._hass.bus.async_listen("telegram_command", self._handle_command),
            self._hass.bus.async_listen("telegram_callback", self._handle_callback),
        ]
        _LOGGER.info("Telegram channel started, listening for events")

    async def async_teardown(self) -> None:
        for unsub in getattr(self, "_unsubs", []):
            unsub()

    async def _handle_text(self, event) -> None:
        """Handle incoming Telegram text message."""
        envelope = self._parse_event(event)
        if not envelope:
            return
        await self._process_and_respond(envelope)

    async def _handle_command(self, event) -> None:
        """Handle /command messages."""
        data = event.data
        command = data.get("command", "")
        args = data.get("args", "")
        # Treat commands as regular text for now
        envelope = self._parse_event(event, text_override=f"{command} {args}".strip())
        if not envelope:
            return
        await self._process_and_respond(envelope)

    async def _handle_callback(self, event) -> None:
        """Handle inline keyboard callback. Phase 2 feature."""
        pass  # TODO: implement when we add interactive responses

    def _parse_event(self, event, text_override: str | None = None) -> MessageEnvelope | None:
        """Parse HA telegram event into MessageEnvelope."""
        data = event.data
        chat_id = str(data.get("chat_id", ""))
        user_id_tg = str(data.get("user_id", ""))
        text = text_override or data.get("text", "")

        if not text or not chat_id:
            return None

        # Check allowlist
        if not self._is_allowed(user_id_tg, chat_id):
            _LOGGER.debug("Telegram message from non-allowed user %s", user_id_tg)
            return None

        # Rate limit check
        if not self._rate_limiter.allow(user_id_tg):
            _LOGGER.warning("Rate limit exceeded for Telegram user %s", user_id_tg)
            return None

        sender_name = f"{data.get('from_first', '')} {data.get('from_last', '')}".strip()
        is_group = data.get("chat", {}).get("type") in ("group", "supergroup")

        return MessageEnvelope(
            text=text,
            channel="telegram",
            sender_id=user_id_tg,
            sender_name=sender_name or f"Telegram User {user_id_tg}",
            target=ChannelTarget(channel_id="telegram", target_id=chat_id),
            ha_user_id=self._resolve_user_id(user_id_tg),
            is_group=is_group,
        )

    async def _process_and_respond(self, envelope: MessageEnvelope) -> None:
        """Process message through AI and respond."""
        # Show typing indicator
        await self.send_typing_indicator(envelope.target)

        # Get/create session
        session_id = await self._get_or_create_session(envelope)

        # Save user message
        await self._save_message(envelope.ha_user_id, session_id, "user", envelope.text)

        # Load conversation history
        history = await self._load_history(envelope.ha_user_id, session_id)

        # Stream through MessageIntake (non-blocking via task)
        accumulated_text = ""
        try:
            async for event in self._intake.process_message_stream(
                text=envelope.text,
                user_id=envelope.ha_user_id,
                session_id=session_id,
                channel_source="telegram",
                conversation_history=history,
            ):
                if isinstance(event, TextEvent):
                    accumulated_text += event.content
                elif isinstance(event, ErrorEvent):
                    accumulated_text = "Sorry, I encountered an error."
                    break
        except Exception as err:
            _LOGGER.exception("Error processing Telegram message: %s", err)
            accumulated_text = "Sorry, something went wrong."

        # Send response (chunked for Telegram's 4096 char limit)
        await self.send_response(envelope.target, accumulated_text)

        # Save assistant message
        await self._save_message(
            envelope.ha_user_id, session_id, "assistant", accumulated_text
        )

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        """Send message via telegram_bot.send_message (chunked if needed)."""
        max_len = 4096  # Telegram limit
        chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
        for chunk in chunks:
            try:
                await self._hass.services.async_call(
                    "telegram_bot", "send_message",
                    {"message": chunk, "target": int(target.target_id)},
                )
            except Exception as err:
                _LOGGER.error("Failed to send Telegram message: %s", err)

    async def send_typing_indicator(self, target: ChannelTarget) -> None:
        try:
            await self._hass.services.async_call(
                "telegram_bot", "send_chat_action",
                {"action": "typing", "target": int(target.target_id)},
            )
        except Exception:
            pass  # Non-critical
```

### 4.7 DiscordChannel — Lightweight Custom Client

**Decision**: Instead of heavy `discord.py` dependency (~15MB), we port OpenClaw's
lightweight Discord Gateway client to Python/asyncio using only `aiohttp` (already in HA).

**Zero new dependencies.**

```python
@ChannelRegistry.register("discord")
class DiscordChannel(Channel):
    """Discord channel via lightweight custom Gateway + REST client.

    Architecture (ported from OpenClaw):
    - gateway.py: WebSocket connection to Discord Gateway API v10
      (identify, heartbeat, resume, reconnect)
    - rest.py: HTTP client for Discord REST API
      (send messages, get channel info, trigger typing)
    - This class: orchestrates gateway events → AI pipeline → responses

    Requires: Bot token from Discord Developer Portal.
    Bot must have MESSAGE_CONTENT intent enabled.
    """

    id = "discord"
    name = "Discord"

    async def async_setup(self) -> None:
        """Start Discord Gateway connection in background."""
        from .discord.gateway import DiscordGateway
        from .discord.rest import DiscordRestClient

        token = self._config.get("bot_token", "")
        if not token:
            _LOGGER.error("Discord bot token not configured")
            return

        self._rest = DiscordRestClient(token)
        self._gateway = DiscordGateway(
            token=token,
            intents=self._compute_intents(),
            on_message=self._handle_message,
            on_ready=self._on_ready,
        )

        # Bounded concurrency: max N concurrent AI requests
        self._semaphore = asyncio.Semaphore(
            self._config.get("max_concurrent", 3)
        )

        # Start gateway in background task
        self._task = self._hass.async_create_task(
            self._gateway.connect(),
            name="discord_gateway",
        )

    async def async_teardown(self) -> None:
        if hasattr(self, "_gateway"):
            await self._gateway.close()
        if hasattr(self, "_rest"):
            await self._rest.close()
        if hasattr(self, "_task"):
            self._task.cancel()

    @property
    def is_available(self) -> bool:
        return hasattr(self, "_gateway") and self._gateway.is_connected

    async def _on_ready(self, user_info: dict) -> None:
        _LOGGER.info("Discord bot connected as %s", user_info.get("username"))
        self._bot_id = user_info.get("id")

    async def _handle_message(self, message: dict) -> None:
        """Handle MESSAGE_CREATE from Discord Gateway."""
        author = message.get("author", {})
        if author.get("id") == self._bot_id:
            return  # Ignore own messages
        if author.get("bot", False):
            return  # Ignore other bots

        content = message.get("content", "")
        channel_id = message.get("channel_id", "")
        guild_id = message.get("guild_id")  # None for DMs

        # Check if we should respond (DM, mention, or configured channel)
        if not self._should_respond(message):
            return

        # Strip bot mention from content
        content = self._strip_mention(content)
        if not content.strip():
            return

        # Rate limit
        sender_id = author.get("id", "")
        if not self._rate_limiter.allow(sender_id):
            return

        envelope = MessageEnvelope(
            text=content,
            channel="discord",
            sender_id=sender_id,
            sender_name=author.get("username", "Unknown"),
            target=ChannelTarget(
                channel_id="discord",
                target_id=channel_id,
                extra={"guild_id": guild_id} if guild_id else {},
            ),
            ha_user_id=self._resolve_user_id(sender_id),
            is_group=guild_id is not None,
            thread_id=message.get("thread", {}).get("id") if message.get("thread") else None,
        )

        # Process with bounded concurrency
        async with self._semaphore:
            await self._process_and_respond(envelope)

    async def _process_and_respond(self, envelope: MessageEnvelope) -> None:
        """Process message through AI pipeline."""
        await self.send_typing_indicator(envelope.target)
        session_id = await self._get_or_create_session(envelope)
        await self._save_message(envelope.ha_user_id, session_id, "user", envelope.text)
        history = await self._load_history(envelope.ha_user_id, session_id)

        accumulated_text = ""
        try:
            async for event in self._intake.process_message_stream(
                text=envelope.text,
                user_id=envelope.ha_user_id,
                session_id=session_id,
                channel_source="discord",
                conversation_history=history,
            ):
                if isinstance(event, TextEvent):
                    accumulated_text += event.content
                elif isinstance(event, ErrorEvent):
                    accumulated_text = "Sorry, I encountered an error."
                    break
        except Exception:
            _LOGGER.exception("Error processing Discord message")
            accumulated_text = "Sorry, something went wrong."

        await self.send_response(envelope.target, accumulated_text)
        await self._save_message(envelope.ha_user_id, session_id, "assistant", accumulated_text)

    async def send_response(self, target: ChannelTarget, text: str) -> None:
        """Send via Discord REST API (chunked for 2000 char limit)."""
        max_len = 2000
        chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
        for chunk in chunks:
            await self._rest.create_message(target.target_id, chunk)

    async def send_typing_indicator(self, target: ChannelTarget) -> None:
        await self._rest.trigger_typing(target.target_id)

    def _should_respond(self, message: dict) -> bool:
        """Respond to DMs, mentions, or configured auto-respond channels."""
        guild_id = message.get("guild_id")
        if guild_id is None:
            return True  # DM
        # Check if bot mentioned
        mentions = message.get("mentions", [])
        if any(m.get("id") == self._bot_id for m in mentions):
            return True
        # Check configured channels
        channel_id = message.get("channel_id", "")
        return channel_id in self._config.get("auto_respond_channels", [])
```

### 4.8 Discord Gateway Client (channels/discord/gateway.py)

Lightweight Discord Gateway v10 client, ported from OpenClaw logic:

```python
class DiscordGateway:
    """Minimal Discord Gateway v10 WebSocket client.

    Ported from OpenClaw's battle-tested implementation.
    Uses only aiohttp (already in HA, zero new deps).

    Lifecycle:
    1. connect() → wss://gateway.discord.gg/?v=10&encoding=json
    2. Receive HELLO (op=10) → start heartbeat at given interval
    3. Send IDENTIFY (op=2) with token + intents
    4. Receive READY (op=0, t=READY) → store session_id + resume_url
    5. Loop: receive DISPATCH events → call handlers
    6. On disconnect: RESUME (op=6) or re-IDENTIFY
    7. Heartbeat ACK tracking → zombie detection → reconnect

    Key opcodes:
    - 0: DISPATCH (events)
    - 1: HEARTBEAT
    - 2: IDENTIFY
    - 6: RESUME
    - 7: RECONNECT (server requests reconnect)
    - 9: INVALID_SESSION
    - 10: HELLO
    - 11: HEARTBEAT_ACK
    """

    GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"

    def __init__(self, token, intents, on_message, on_ready):
        self._token = token
        self._intents = intents
        self._on_message = on_message
        self._on_ready = on_ready
        self._session_id: str | None = None
        self._resume_url: str | None = None
        self._sequence: int | None = None
        self._ws = None
        self._heartbeat_task = None
        self._running = False

    async def connect(self):
        """Main connection loop with auto-reconnect."""
        self._running = True
        while self._running:
            try:
                url = self._resume_url or self.GATEWAY_URL
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url) as ws:
                        self._ws = ws
                        await self._handle_connection(ws)
            except Exception:
                _LOGGER.exception("Discord gateway error, reconnecting in 5s")
                await asyncio.sleep(5)

    async def close(self):
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._ws:
            await self._ws.close()
```

### 4.9 Discord REST Client (channels/discord/rest.py)

```python
class DiscordRestClient:
    """Minimal Discord REST API v10 client using aiohttp."""

    BASE = "https://discord.com/api/v10"

    def __init__(self, token: str) -> None:
        self._token = token
        self._session: aiohttp.ClientSession | None = None

    async def create_message(self, channel_id: str, content: str) -> dict:
        """POST /channels/{id}/messages"""
        ...

    async def trigger_typing(self, channel_id: str) -> None:
        """POST /channels/{id}/typing"""
        ...

    async def close(self) -> None:
        if self._session:
            await self._session.close()
```

### 4.10 Session Model

Sessions from external channels stored in existing `SessionStorage`:

```python
# Session.metadata for external channels (NEW field, requires migration)
session.metadata = {
    "channel": "telegram",           # or "discord", "panel", "voice"
    "channel_target": {
        "chat_id": "123456789",      # Telegram
    },
    "sender_name": "Jan Kowalski",
}

# Session title format
title = "[Telegram] Zapytanie o automatyzację..."
title = "[Discord] Sterowanie światłami..."

# Session keying strategy:
# DM:     session key = "{channel}_{sender_id}"       → one session per DM user
# Group:  session key = "{channel}_group_{target_id}"  → one session per group chat
# Thread: session key = "{channel}_thread_{thread_id}" → one session per thread
```

### 4.11 Security Model

```python
class ChannelRateLimiter:
    """Per-user rate limiter for external channels."""

    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 60):
        self._minute_buckets: dict[str, list[float]] = {}
        self._hour_buckets: dict[str, list[float]] = {}
        self._max_minute = max_per_minute
        self._max_hour = max_per_hour

    def allow(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        now = time.time()
        # Clean old entries + check limits
        ...
        return True

# Per-channel tool policy:
# External channels get RESTRICTED tool set by default (read-only).
# Panel and Voice get full tools.
CHANNEL_TOOL_POLICY = {
    "panel": None,       # All tools allowed
    "voice": None,       # All tools allowed
    "telegram": {        # Read-only by default
        "denied_tools": ["create_automation", "delete_automation",
                         "create_dashboard", "subagent_spawn"],
    },
    "discord": {         # Read-only by default
        "denied_tools": ["create_automation", "delete_automation",
                         "create_dashboard", "subagent_spawn"],
    },
}
```

### 4.12 Configuration (Config Flow)

Separate OptionsFlow substeps per channel (not CSV strings):

```python
# Step 1: Channel selection
async def async_step_channels(self, user_input):
    """Enable/disable channels."""
    return self.async_show_form(
        step_id="channels",
        data_schema=vol.Schema({
            vol.Optional("telegram_enabled"): BooleanSelector(),
            vol.Optional("discord_enabled"): BooleanSelector(),
        }),
    )

# Step 2: Telegram config (shown only if enabled)
async def async_step_telegram(self, user_input):
    """Configure Telegram channel."""
    return self.async_show_form(
        step_id="telegram",
        data_schema=vol.Schema({
            vol.Optional("telegram_allowed_chat_ids"): TextSelector(
                TextSelectorConfig(multiline=True)
            ),  # One per line, validated as integers
            vol.Optional("telegram_rate_limit", default=10): int,
        }),
    )

# Step 3: Discord config (shown only if enabled)
async def async_step_discord(self, user_input):
    """Configure Discord channel."""
    return self.async_show_form(
        step_id="discord",
        data_schema=vol.Schema({
            vol.Required("discord_bot_token"): TextSelector(
                TextSelectorConfig(type="password")
            ),
            vol.Optional("discord_auto_respond_channels"): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            vol.Optional("discord_rate_limit", default=10): int,
            vol.Optional("discord_max_concurrent", default=3): int,
        }),
    )
```

### 4.13 Frontend Changes (Svelte Panel)

- Session list shows channel badge: `[TG]`, `[DC]`, `[Voice]`
- Badge color-coded via `session.metadata.channel`
- No changes to chat area — messages render identically
- Future: channel filter in sidebar

## 5. Message Flow (Complete)

```
[Telegram HA Events]  [Discord Gateway WS]  [Svelte Panel WS]  [Voice/Assist]
        |                      |                    |                  |
        v                      v                    |                  |
  TelegramChannel        DiscordChannel             |                  |
  (HA event bus)       (custom gateway.py)          |                  |
        |                      |                    |                  |
        +----------+-----------+                    |                  |
                   |                                |                  |
                   v                                v                  v
             MessageIntake  <---------- ws_handlers/chat.py   conversation.py
                   |                    (refactored to use Intake)
                   v
             HomeclawAgent.stream_query()  ← PUBLIC API (no _agent access)
                   |
                   v
             Agent.process_query_stream()
                   |
                   v
             AgentEvent stream
                   |
                   v
             Channel.send_response()  /  WS event  /  ChatLog delta
```

## 6. Implementation Phases

| Phase | Scope | Effort | Dependencies |
| ----- | ----- | ------ | ------------ |
| **0. Pre-requisites** ✅ | Fix `_current_user_id` race, add `Session.metadata`, expose public API on `HomeclawAgent`, storage migration v1→v2 | 1-2 days | None |
| **1. MessageIntake** ✅ | Extract shared setup into `channels/intake.py`. Refactor `chat.py` to use it. All existing tests pass. | 1-2 days | Phase 0 |
| **2. Channel ABC + Manager** ✅ | `channels/base.py` (ABC, dataclasses, rate limiter), `channels/manager.py` (ChannelManager). Wire into `__init__.py`. | 1 day | Phase 1 |
| **3. TelegramChannel** | `channels/telegram.py` — HA event hooks, auto-sessions, send_message, typing, allowlist, rate limits. | 1-2 days | Phase 2 + `telegram_bot` in HA |
| **4. Discord Gateway** | `channels/discord/gateway.py` — lightweight WS client (port from OpenClaw). `channels/discord/rest.py` — REST client. | 2-3 days | Phase 2 |
| **5. DiscordChannel** | `channels/discord/__init__.py` — wire gateway + rest + AI pipeline. Semaphore, session mgmt. | 1-2 days | Phase 4 + bot token |
| **6. Config flow** | OptionsFlow substeps per channel. Validated inputs, no CSV. | 1 day | Phase 3 or 5 |
| **7. Frontend badges** | Show channel badges on sessions in Svelte sidebar. | 0.5 day | Phase 3 or 5 |

## 7. Dependencies

### Python packages
- **None new** — uses only `aiohttp` (already in HA) for Discord Gateway + REST
- Telegram uses existing HA `telegram_bot` services

### HA integrations required
- `telegram_bot` — must be configured in HA (polling mode recommended)

### External setup
- **Telegram**: Create bot via @BotFather → get token → configure `telegram_bot` in HA
- **Discord**: Create Application in Discord Developer Portal → get bot token → enable MESSAGE_CONTENT intent → add bot to server

## 8. Security Model

| Layer | Mechanism | Default |
| ----- | --------- | ------- |
| **Access** | Allowlist (chat_ids / guild_ids) | Allow all (opt-in) |
| **Identity** | Shadow user isolation (`telegram_123`) | Always isolated |
| **Rate limiting** | Per-user: 10/min, 60/hour | Configurable |
| **Tool policy** | External channels = read-only tools | Restricted |
| **Concurrency** | Semaphore per channel (Discord: 3) | Configurable |
| **Tokens** | Stored in HA config entries (encrypted) | — |
| **Logging** | Debug level only, content truncated | — |

## 9. Risks & Mitigations (from review)

| Risk | Level | Mitigation |
| ---- | ----- | ---------- |
| `_current_user_id` race condition | HIGH | Phase 0: pass user_id explicitly |
| Session.metadata missing | HIGH | Phase 0: add field + migration |
| Private API coupling | HIGH | Phase 0: expose public `stream_query()` |
| Discord Gateway complexity | MEDIUM | Port battle-tested OpenClaw logic |
| telegram_bot not configured | MEDIUM | Guard in `async_setup()`, log error |
| Config UX (CSV strings) | MEDIUM | Separate substeps, validated inputs |
| Session key ambiguity | MEDIUM | Explicit DM/group/thread strategy |

## 10. Test Plan

| Area | Tests |
| ---- | ----- |
| **MessageIntake** | Unit: builds correct kwargs, delegates to agent. Integration: existing chat.py tests still pass. |
| **Channel ABC** | Unit: session keying, user resolution, rate limiter, allowlist. |
| **TelegramChannel** | Unit: event parsing, envelope building, chunking. Mock: HA event bus + service calls. |
| **Discord Gateway** | Unit: opcode handling, heartbeat, resume. Integration: mock WebSocket server. |
| **DiscordChannel** | Unit: message filtering, mention stripping, semaphore. Mock: gateway + rest. |
| **Storage migration** | Unit: v1→v2 migration adds metadata to existing sessions. |
| **HA lifecycle** | Integration: setup/teardown/reload with channels active. |
