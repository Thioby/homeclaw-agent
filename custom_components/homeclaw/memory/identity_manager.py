"""Identity Manager — orchestrates agent identity and onboarding.

This manager handles:
- Identity storage (name, personality, emoji, user profile)
- System prompt construction with identity context
- Onboarding flow (first-run experience)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .identity_store import AgentIdentity, IdentityStore

_LOGGER = logging.getLogger(__name__)


@dataclass
class IdentityManager:
    """Facade for the Agent Identity system.

    Manages agent identity, user profile, and system prompt construction
    with identity context injection.

    Args:
        store: SqliteStore instance from the RAG system.
    """

    store: Any  # SqliteStore
    _identity_store: IdentityStore | None = field(default=None, repr=False)
    _initialized: bool = field(default=False, repr=False)

    async def async_initialize(self) -> None:
        """Initialize the identity system.

        Creates identity table in the existing SQLite database.
        """
        if self._initialized:
            return

        self._identity_store = IdentityStore(store=self.store)
        await self._identity_store.async_initialize()
        self._initialized = True
        _LOGGER.info("Identity manager initialized")

    def _ensure_initialized(self) -> None:
        """Ensure identity system is ready."""
        if not self._initialized or not self._identity_store:
            raise RuntimeError(
                "IdentityManager not initialized. Call async_initialize() first."
            )

    async def get_identity(self, user_id: str) -> AgentIdentity | None:
        """Get identity for a user.

        Args:
            user_id: User to fetch identity for.

        Returns:
            AgentIdentity if found, None if user hasn't been onboarded.
        """
        self._ensure_initialized()
        return await self._identity_store.get_identity(user_id)

    async def save_identity(self, user_id: str, **fields) -> None:
        """Update identity fields (partial update).

        Args:
            user_id: User whose identity to update.
            **fields: Fields to update (agent_name, agent_personality, etc.)
        """
        self._ensure_initialized()

        # Get existing identity or create new one
        identity = await self._identity_store.get_identity(user_id)
        if identity is None:
            identity = AgentIdentity(user_id=user_id)

        # Update fields
        for key, value in fields.items():
            if hasattr(identity, key):
                setattr(identity, key, value)

        await self._identity_store.save_identity(identity)

    async def is_onboarded(self, user_id: str) -> bool:
        """Check if user has completed onboarding.

        Args:
            user_id: User to check.

        Returns:
            True if onboarded, False otherwise.
        """
        self._ensure_initialized()
        return await self._identity_store.is_onboarded(user_id)

    async def complete_onboarding(self, user_id: str) -> None:
        """Mark onboarding as complete.

        Args:
            user_id: User who completed onboarding.
        """
        await self.save_identity(user_id, onboarding_completed=True)
        _LOGGER.info("Onboarding completed for user %s", user_id[:8])

    def build_system_prompt(self, identity: AgentIdentity | None) -> str:
        """Build full system prompt with identity context.

        Args:
            identity: User's agent identity (None if not onboarded).

        Returns:
            Full system prompt string with identity context if available,
            or onboarding prompt for new users.
        """
        from ..prompts import (
            BASE_SYSTEM_PROMPT,
            ONBOARDING_PROMPT,
        )

        # First-time user → onboarding flow
        if identity is None or not identity.onboarding_completed:
            return ONBOARDING_PROMPT

        # Onboarded user → inject identity context into base prompt
        identity_context = self.build_identity_context(identity)
        return f"{identity_context}\n\n{BASE_SYSTEM_PROMPT}"

    def build_identity_context(self, identity: AgentIdentity) -> str:
        """Build the identity section for system prompt injection.

        Args:
            identity: The agent identity to format.

        Returns:
            XML-formatted identity context.
        """
        parts = []

        # Agent name
        if identity.agent_name:
            parts.append(f"Your name is {identity.agent_name}.")

        # Agent personality
        if identity.agent_personality:
            parts.append(f"Your personality: {identity.agent_personality}")

        # Agent emoji
        if identity.agent_emoji:
            parts.append(f"Your emoji: {identity.agent_emoji}")

        # User name
        if identity.user_name:
            parts.append(f"You are speaking with {identity.user_name}.")

        # Language preference
        if identity.language and identity.language != "auto":
            parts.append(f"Preferred language: {identity.language}")

        # Additional user info
        if identity.user_info:
            parts.append(f"About the user: {identity.user_info}")

        context = "\n".join(parts)
        return f"<agent-identity>\n{context}\n</agent-identity>"
