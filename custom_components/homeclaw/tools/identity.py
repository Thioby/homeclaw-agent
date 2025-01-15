"""Identity tools for Homeclaw.

Provides tools for the AI agent to set and update its own identity and
user profile during the onboarding conversation. These tools allow the agent
to save its chosen name, personality, emoji, and information about the user.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..const import DOMAIN
from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)


def _get_identity_manager(hass: Any) -> Any | None:
    """Get the IdentityManager from hass.data.

    Returns None if RAG/identity is not initialized.
    """
    if not hass or DOMAIN not in hass.data:
        return None

    rag_manager = hass.data[DOMAIN].get("rag_manager")
    if not rag_manager or not rag_manager.is_initialized:
        return None

    return getattr(rag_manager, "identity_manager", None)


def _get_current_user_id(hass: Any) -> str:
    """Get the current user ID from conversation context.

    The websocket handler stores the current user_id in hass.data[DOMAIN]
    before tool execution. Falls back to 'default' if not available.
    """
    if not hass or DOMAIN not in hass.data:
        return "default"

    return hass.data[DOMAIN].get("_current_user_id", "default")


@ToolRegistry.register
class IdentitySetTool(Tool):
    """Set or update agent identity and user profile.

    Use this tool during onboarding to save the agent's chosen name,
    personality, emoji, and user preferences. Also marks onboarding as
    complete when all essential fields are set.
    """

    id = "identity_set"
    description = (
        "Set or update agent identity and user profile. Use during onboarding "
        "to save the agent's chosen name, personality, emoji, and user preferences. "
        "Call this after learning about the user to save the information."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="agent_name",
            type="string",
            description="The agent's name (e.g., 'Luna', 'Jarvis')",
            required=False,
        ),
        ToolParameter(
            name="agent_personality",
            type="string",
            description="The agent's personality description (e.g., 'Warm and friendly')",
            required=False,
        ),
        ToolParameter(
            name="agent_emoji",
            type="string",
            description="The agent's signature emoji (e.g., '🌙', '🤖')",
            required=False,
        ),
        ToolParameter(
            name="user_name",
            type="string",
            description="How to address the user (e.g., 'Artur', 'Dr. Smith')",
            required=False,
        ),
        ToolParameter(
            name="user_info",
            type="string",
            description="Additional information about the user (e.g., 'Lives in Warsaw, prefers automation')",
            required=False,
        ),
        ToolParameter(
            name="language",
            type="string",
            description="Preferred language code (e.g., 'pl', 'en', 'auto')",
            required=False,
            default="auto",
        ),
        ToolParameter(
            name="mark_onboarding_complete",
            type="boolean",
            description="Mark the onboarding process as complete",
            required=False,
            default=False,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Set or update identity fields."""
        identity_manager = _get_identity_manager(self.hass)
        if not identity_manager:
            return ToolResult(
                output="Identity system not available",
                error="identity_not_initialized",
                success=False,
            )

        user_id = _get_current_user_id(self.hass)

        try:
            # Extract fields to update (only non-None values)
            fields_to_update = {}

            for field in [
                "agent_name",
                "agent_personality",
                "agent_emoji",
                "user_name",
                "user_info",
                "language",
            ]:
                value = kwargs.get(field)
                if value is not None:
                    fields_to_update[field] = value

            # Save identity fields
            if fields_to_update:
                await identity_manager.save_identity(user_id, **fields_to_update)

            # Mark onboarding complete if requested
            mark_complete = kwargs.get("mark_onboarding_complete", False)
            if mark_complete:
                await identity_manager.complete_onboarding(user_id)

            # Get current identity to return
            identity = await identity_manager.get_identity(user_id)

            result = {
                "success": True,
                "updated_fields": list(fields_to_update.keys()),
                "onboarding_completed": identity.onboarding_completed if identity else False,
                "agent_name": identity.agent_name if identity else None,
            }

            return ToolResult(
                output=json.dumps(result),
                metadata=result,
            )

        except Exception as e:
            _LOGGER.error("identity_set tool failed: %s", e)
            return ToolResult(
                output=f"Failed to set identity: {e}",
                error=str(e),
                success=False,
            )
