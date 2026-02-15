"""Conversation agent support for Homeclaw.

This module implements the HA Conversation Entity interface, allowing Homeclaw
to be used as a conversation agent in Assist pipelines, voice assistants,
and the conversation.process service.

Architecture: Bridge pattern — thin adapter over existing Homeclaw infrastructure.
The custom panel, WebSocket API, and services continue to work unchanged.

Streaming: Uses Agent.process_query_stream() which handles the full tool calling
loop internally. The _transform_provider_stream() adapter converts Homeclaw's
chunk format to HA ChatLog delta format for real-time streaming to the UI.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .storage import Message, SessionStorage

if TYPE_CHECKING:
    from .agent_compat import HomeclawAgent

_LOGGER = logging.getLogger(__name__)

# Cache prefix for SessionStorage instances (same as ws_handlers/_common.py)
_STORAGE_CACHE_PREFIX = "homeclaw_storage_"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Homeclaw conversation entities from a config entry."""
    provider = config_entry.data.get("ai_provider", "unknown")
    agent: HomeclawAgent | None = (
        hass.data.get(DOMAIN, {}).get("agents", {}).get(provider)
    )
    if agent is None:
        _LOGGER.warning(
            "No Homeclaw agent found for provider %s, skipping conversation entity",
            provider,
        )
        return

    async_add_entities([HomeclawConversationEntity(config_entry, provider, agent)])


class HomeclawConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Homeclaw conversation agent entity.

    Bridges HA's Conversation Entity interface to the existing Homeclaw
    agent infrastructure (HomeclawAgent -> Agent -> QueryProcessor -> AIProvider).

    Streaming: Enabled. Text chunks are streamed to the UI in real time.
    Tool calling is handled internally by Homeclaw's ToolRegistry + ToolExecutor.
    """

    _attr_has_entity_name = True
    _attr_supports_streaming = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        provider_name: str,
        agent: HomeclawAgent,
    ) -> None:
        """Initialize the conversation entity."""
        self._config_entry = config_entry
        self._provider_name = provider_name
        self._agent = agent
        # With has_entity_name=True, _attr_name is appended to device name.
        # Device name = "Homeclaw Openai", entity name = "Conversation"
        # -> full entity_id: conversation.homeclaw_openai_conversation
        self._attr_name = "Conversation"
        self._attr_unique_id = f"{config_entry.entry_id}-conversation"
        self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Homeclaw {provider_name.replace('_', ' ').title()}",
            manufacturer="Homeclaw",
            model=provider_name,
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        # Maps (user_id, conversation_id) -> Homeclaw session_id for voice persistence
        self._voice_sessions: dict[tuple[str, str], str] = {}

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Handle an incoming message from Assist / Voice / conversation.process.

        Uses streaming via Agent.process_query_stream() which handles:
        - System prompt with identity context
        - Tool calling with ToolRegistry (full loop, max 20 iterations)
        - RAG context injection
        - Context window management and compaction
        - Memory flush

        Voice session persistence: User and assistant messages are saved to
        Homeclaw SessionStorage so they appear in the Svelte chat panel.
        """
        try:
            user_id = user_input.context.user_id or "default"

            # Build system prompt with identity context
            system_prompt = await self._agent._get_system_prompt(user_id)

            # Append extra_system_prompt if provided by the pipeline
            if user_input.extra_system_prompt:
                system_prompt = f"{system_prompt}\n\n{user_input.extra_system_prompt}"

            # Set the system content in chat_log
            if chat_log.content and isinstance(
                chat_log.content[0], conversation.SystemContent
            ):
                chat_log.content[0] = conversation.SystemContent(content=system_prompt)

            # Voice session persistence: get or create a Homeclaw session
            hc_session_id = await self._get_or_create_voice_session(
                user_id=user_id,
                conversation_id=user_input.conversation_id,
                first_message=user_input.text,
            )

            # Save user message to SessionStorage
            if hc_session_id:
                await self._save_voice_message(
                    user_id=user_id,
                    session_id=hc_session_id,
                    role="user",
                    content=user_input.text,
                )

            # Convert chat_log history to provider messages.
            # Exclude the last UserContent — HA already appended the current
            # user message to chat_log, but process_query_stream will add it
            # again via QueryProcessor._build_messages().
            conversation_history = self._convert_chat_log_to_messages(
                chat_log, exclude_last_user=True
            )

            # Fetch RAG context (async) before building kwargs
            rag_context = None
            if self._agent._rag_manager:
                rag_context = await self._agent._get_rag_context(
                    user_input.text, user_id=user_id
                )

            # Build kwargs for Agent.process_query_stream()
            stream_kwargs = self._build_stream_kwargs(
                user_id=user_id,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                rag_context=rag_context,
                session_id=user_input.conversation_id or "",
            )

            # Get the provider stream from Agent
            provider_stream = self._agent._agent.process_query_stream(
                user_input.text, **stream_kwargs
            )

            # Transform and sanitize provider stream for ChatLog.
            # During tool execution the generator simply suspends — no
            # deltas flow, so the TTS pipeline stays idle until real
            # text arrives (matching the OpenAI reference pattern).
            delta_stream = self._transform_provider_stream(provider_stream, chat_log)
            sanitized_stream = self._tts_sanitizer_stream(delta_stream)

            async for _content in chat_log.async_add_delta_content_stream(
                self.entity_id,
                sanitized_stream,
            ):
                pass

            # Save assistant response to SessionStorage
            if hc_session_id:
                assistant_text = self._extract_last_assistant_text(chat_log)
                if assistant_text:
                    await self._save_voice_message(
                        user_id=user_id,
                        session_id=hc_session_id,
                        role="assistant",
                        content=assistant_text,
                    )

        except Exception as err:
            _LOGGER.error(
                "Error processing conversation message: %s", err, exc_info=True
            )
            chat_log.async_add_assistant_content_without_tools(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content="Sorry, I encountered an error processing your request.",
                )
            )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    def _build_stream_kwargs(
        self,
        user_id: str,
        system_prompt: str,
        conversation_history: list[dict[str, str]] | None,
        rag_context: str | None = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Build kwargs for Agent.process_query_stream().

        Mirrors the setup logic from HomeclawAgent.process_query() but
        adapts it for the streaming path.
        """
        kwargs: dict[str, Any] = {
            "hass": self._agent.hass,
            "user_id": user_id,
            "system_prompt_override": system_prompt,
            "session_id": session_id,
        }

        # Always pass conversation_history (even empty list) to prevent
        # process_query_stream from falling back to global in-memory history.
        if conversation_history is not None:
            kwargs["conversation_history"] = conversation_history

        # Add tools for native function calling
        tools = self._agent._get_tools_for_provider()
        if tools:
            kwargs["tools"] = tools

        # Context window for compaction
        from .models import get_context_window

        kwargs["context_window"] = get_context_window(self._provider_name, None)

        # RAG context — pre-fetched async in _async_handle_message
        if rag_context:
            kwargs["rag_context"] = rag_context

        # Memory flush function for pre-compaction capture
        if self._agent._rag_manager and self._agent._rag_manager.is_initialized:
            mem_mgr = getattr(self._agent._rag_manager, "_memory_manager", None)
            if mem_mgr:
                kwargs["memory_flush_fn"] = mem_mgr.flush_from_messages

        return kwargs

    # --- Voice session persistence helpers ---

    def _get_storage(self, user_id: str) -> SessionStorage:
        """Get or create a cached SessionStorage instance for a user."""
        cache_key = f"{_STORAGE_CACHE_PREFIX}{user_id}"
        if cache_key not in self.hass.data:
            self.hass.data[cache_key] = SessionStorage(self.hass, user_id)
        return self.hass.data[cache_key]

    async def _get_or_create_voice_session(
        self,
        user_id: str,
        conversation_id: str | None,
        first_message: str,
    ) -> str | None:
        """Get or create a Homeclaw session for a voice conversation.

        Maps HA conversation_id to a Homeclaw session_id. Creates a new
        session on first message with title "Voice: <first words>".

        Returns the Homeclaw session_id, or None if storage fails.
        """
        if not conversation_id:
            return None

        # Check if we already have a mapping for this user + conversation
        key = (user_id, conversation_id)
        if key in self._voice_sessions:
            return self._voice_sessions[key]

        try:
            storage = self._get_storage(user_id)
            # Create a new voice session with distinguishing title
            preview = first_message[:50].strip()
            title = f"Voice: {preview}"
            session = await storage.create_session(
                provider=self._provider_name,
                title=title,
            )
            self._voice_sessions[key] = session.session_id
            _LOGGER.debug(
                "Created voice session %s for conversation %s",
                session.session_id,
                conversation_id,
            )
            return session.session_id
        except Exception:
            _LOGGER.warning(
                "Failed to create voice session for conversation %s",
                conversation_id,
                exc_info=True,
            )
            return None

    async def _save_voice_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Save a message to SessionStorage for voice session persistence."""
        try:
            storage = self._get_storage(user_id)
            now = datetime.now(timezone.utc).isoformat()
            message = Message(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                timestamp=now,
                status="completed",
                metadata={"source": "voice"},
            )
            await storage.add_message(session_id, message)
        except Exception:
            _LOGGER.warning(
                "Failed to save voice %s message to session %s",
                role,
                session_id,
                exc_info=True,
            )

    @staticmethod
    def _extract_last_assistant_text(
        chat_log: conversation.ChatLog,
    ) -> str:
        """Extract the last assistant response text from the ChatLog."""
        for content in reversed(chat_log.content):
            if isinstance(content, conversation.AssistantContent) and content.content:
                return content.content
        return ""

    @staticmethod
    async def _tts_sanitizer_stream(
        stream: AsyncGenerator[dict[str, Any], None],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Sanitize text chunks for TTS in real-time.

        Removes emojis and markdown markers to prevent the TTS engine from
        reading them aloud or pausing unnaturally.
        """
        async for delta in stream:
            if "content" in delta:
                content = delta["content"]
                if content:
                    # 1. Remove emojis (Unicode range)
                    content = re.sub(r"[\U00010000-\U0010ffff]", "", content)
                    # 2. Strip common markdown formatting
                    content = (
                        content.replace("**", "")
                        .replace("__", "")
                        .replace("*", "")
                        .replace("_", "")
                        .replace("`", "")
                    )
                    # 3. Strip headers
                    content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
                    delta["content"] = content
            yield delta

    async def _transform_provider_stream(
        self,
        stream: AsyncGenerator[Any, None],
        chat_log: conversation.ChatLog,
    ) -> AsyncGenerator[
        conversation.AssistantContentDeltaDict
        | conversation.ToolResultContentDeltaDict,
        None,
    ]:
        """Transform Homeclaw provider stream to HA ChatLog delta format.

        Converts Homeclaw chunk events to ChatLog delta dicts. Only text
        content is forwarded; status/tool events are handled internally by
        process_query_stream. The {"role": "assistant"} marker is emitted
        once, alongside the first real text chunk.

        During tool execution the generator simply suspends (no yields),
        keeping the TTS pipeline idle until real text arrives.
        """
        from .core.events import (
            TextEvent,
            StatusEvent,
            ErrorEvent,
            CompletionEvent,
            ToolCallEvent,
            ToolResultEvent,
        )

        assistant_started = False

        async for chunk in stream:
            if isinstance(chunk, TextEvent):
                content = chunk.content
                if not content:
                    continue

                if not assistant_started:
                    yield {"role": "assistant"}
                    assistant_started = True

                yield {"content": content}

            elif isinstance(chunk, StatusEvent):
                _LOGGER.debug("Tool status: %s", chunk.message)

            elif isinstance(chunk, ErrorEvent):
                error_msg = chunk.message
                _LOGGER.error("Provider stream error: %s", error_msg)

                if not assistant_started:
                    yield {"role": "assistant"}
                    assistant_started = True

                yield {
                    "content": "Sorry, I encountered an error processing your request."
                }

            elif isinstance(chunk, CompletionEvent):
                _LOGGER.debug("Provider stream complete")
            
            elif isinstance(chunk, ToolCallEvent):
                _LOGGER.debug("Tool call event: %s(%s)", chunk.tool_name, chunk.tool_args)
                
                if not assistant_started:
                    yield {"role": "assistant"}
                    assistant_started = True

                # Signal the tool call to HA so it shows up in UI
                tool_calls = [
                    llm.ToolInput(
                        id=chunk.tool_call_id,
                        tool_name=chunk.tool_name,
                        tool_args=chunk.tool_args,
                        external=True, # We handle execution internally
                    )
                ]
                yield {"tool_calls": tool_calls}

            elif isinstance(chunk, ToolResultEvent):
                _LOGGER.debug("Tool result event: %s -> %s...", chunk.tool_name, str(chunk.tool_result)[:50])
                # Append tool result to chat log history directly
                # This ensures the tool result is recorded, even if we are currently
                # updating the Assistant message.
                chat_log.async_add_tool_result_content(
                    conversation.ToolResultContent(
                        agent_id=self.entity_id,
                        tool_call_id=chunk.tool_call_id,
                        tool_name=chunk.tool_name,
                        tool_result={"result": chunk.tool_result},
                    )
                )

        # HA requires at least one AssistantContent in chat_log. If the stream
        # produced no text (e.g. tools-only response or empty stream), emit
        # a minimal assistant delta so ChatLog doesn't raise.
        if not assistant_started:
            yield {"role": "assistant"}
            yield {"content": ""}

    def _convert_chat_log_to_messages(
        self,
        chat_log: conversation.ChatLog,
        exclude_last_user: bool = False,
    ) -> list[dict[str, str]]:
        """Convert ChatLog content to simple message dicts for the provider.

        Skips SystemContent (handled separately via system_prompt).
        Converts UserContent and AssistantContent to {role, content} dicts.

        Args:
            chat_log: The HA ChatLog with conversation history.
            exclude_last_user: If True, skip the last UserContent entry
                to avoid sending the current user message twice.
        """
        messages: list[dict[str, str]] = []
        for content in chat_log.content:
            if isinstance(content, conversation.SystemContent):
                continue
            elif isinstance(content, conversation.UserContent):
                messages.append({"role": "user", "content": content.content})
            elif isinstance(content, conversation.AssistantContent):
                if content.content:
                    messages.append({"role": "assistant", "content": content.content})

        # Remove the last user message to avoid duplication — HA adds the current
        # user utterance to chat_log before _async_handle_message, but
        # process_query_stream also prepends it via QueryProcessor._build_messages.
        if exclude_last_user and messages:
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    messages.pop(i)
                    break

        return messages
