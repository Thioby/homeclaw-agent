"""MessageIntake — centralized message entry point for all channels.

Owns the shared setup logic: agent lookup, streaming, non-streaming.
Channels and WebSocket handlers call this instead of duplicating boilerplate.
Uses ONLY public HomeclawAgent API (no _agent access).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator

from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..agent_compat import HomeclawAgent
    from ..core.events import AgentEvent

_LOGGER = logging.getLogger(__name__)


class MessageIntake:
    """Centralized message entry point for all channels.

    Resolves the correct HomeclawAgent from hass.data, then delegates
    to the agent's public API. No private attribute access.

    Usage:
        intake = MessageIntake(hass)
        async for event in intake.process_message_stream(
            "turn on kitchen lights",
            user_id="abc123",
            session_id="session-uuid",
        ):
            ...  # TextEvent, StatusEvent, CompletionEvent, etc.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def process_message_stream(
        self,
        text: str,
        *,
        user_id: str,
        session_id: str = "",
        provider: str | None = None,
        model: str | None = None,
        channel_source: str = "panel",
        conversation_history: list[dict] | None = None,
        attachments: list | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Unified streaming entry point.

        Resolves the agent from hass.data and delegates to
        ``HomeclawAgent.stream_query()`` (public API).

        Args:
            text: User message text.
            user_id: HA user ID (or shadow user ID for external channels).
            session_id: Session ID for context.
            provider: Provider name. If None, uses first available agent.
            model: Optional model override.
            channel_source: Origin channel (``"panel"``, ``"telegram"``, etc.).
            conversation_history: Optional conversation history from storage.
            attachments: Optional list of ProcessedAttachment objects.

        Yields:
            AgentEvent objects (TextEvent, StatusEvent, CompletionEvent, etc.).

        Raises:
            HomeAssistantError: If no AI agent is configured.
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

    async def process_message(
        self,
        text: str,
        *,
        user_id: str,
        session_id: str = "",
        provider: str | None = None,
        model: str | None = None,
        debug: bool = False,
        conversation_history: list[dict] | None = None,
        attachments: list | None = None,
        channel_source: str = "panel",
    ) -> dict[str, Any]:
        """Non-streaming entry point.

        Resolves the agent and calls ``HomeclawAgent.process_query()``.
        Returns the standard ``{success, answer, error}`` dict.

        Args:
            text: User message text.
            user_id: HA user ID.
            session_id: Session ID for context.
            provider: Provider name. If None, uses first available.
            model: Optional model override.
            debug: Enable debug mode.
            conversation_history: Optional history from storage.
            attachments: Optional attachments.
            channel_source: Origin channel identifier.

        Returns:
            Dict with ``success``, ``answer``, and optional ``error`` keys.

        Raises:
            HomeAssistantError: If no AI agent is configured.
        """
        agent = self._get_agent(provider)

        kwargs: dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "debug": debug,
        }
        if model:
            kwargs["model"] = model
        if conversation_history is not None:
            kwargs["conversation_history"] = conversation_history
        if attachments:
            kwargs["attachments"] = attachments
        if provider:
            kwargs["provider"] = provider

        return await agent.process_query(text, **kwargs)

    def _get_agent(self, provider: str | None = None) -> HomeclawAgent:
        """Look up agent from hass.data.

        Args:
            provider: Specific provider name, or None for first available.

        Returns:
            HomeclawAgent instance.

        Raises:
            HomeAssistantError: If no agent is found.
        """
        agents = self._hass.data.get(DOMAIN, {}).get("agents", {})

        if provider and provider in agents:
            return agents[provider]

        # Fall back to first available agent
        if agents:
            return next(iter(agents.values()))

        raise HomeAssistantError("No AI agent configured")
