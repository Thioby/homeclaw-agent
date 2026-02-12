"""AI Task platform for Homeclaw.

Implements the HA AI Task Entity interface, allowing Homeclaw to handle
structured data generation via the ai_task.generate_data service.

Architecture: Bridge pattern — thin adapter over existing Homeclaw infrastructure,
same approach as conversation.py.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from homeassistant.components import ai_task
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.components.conversation import ChatLog

    from .agent_compat import HomeclawAgent

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Homeclaw AI Task entities from a config entry."""
    provider = config_entry.data.get("ai_provider", "unknown")
    agent: HomeclawAgent | None = hass.data.get(DOMAIN, {}).get("agents", {}).get(
        provider
    )
    if agent is None:
        _LOGGER.warning(
            "No Homeclaw agent found for provider %s, skipping AI Task entity",
            provider,
        )
        return

    async_add_entities([HomeclawAITaskEntity(config_entry, provider, agent)])


class HomeclawAITaskEntity(ai_task.AITaskEntity):
    """Homeclaw AI Task entity.

    Bridges HA's AI Task interface to the existing Homeclaw agent infrastructure.
    Supports structured data generation (GENERATE_DATA).
    """

    _attr_has_entity_name = True
    _attr_supported_features = ai_task.AITaskEntityFeature.GENERATE_DATA

    def __init__(
        self,
        config_entry: ConfigEntry,
        provider_name: str,
        agent: HomeclawAgent,
    ) -> None:
        """Initialize the AI Task entity."""
        self._config_entry = config_entry
        self._provider_name = provider_name
        self._agent = agent
        self._attr_name = "AI Task"
        self._attr_unique_id = f"{config_entry.entry_id}-ai-task"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Homeclaw {provider_name.replace('_', ' ').title()}",
            manufacturer="Homeclaw",
            model=provider_name,
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    async def _async_generate_data(
        self,
        task: ai_task.GenDataTask,
        chat_log: ChatLog,
    ) -> ai_task.GenDataTaskResult:
        """Handle a data generation task.

        Delegates to HomeclawAgent.process_query() which provides the full
        agent pipeline: tools, RAG context, context window, memory flush.
        If task.structure is provided, instructs the LLM to respond with JSON
        and parses the response.
        """
        # Build system prompt — add JSON instructions for structured output
        system_prompt = "You are a helpful Home Assistant AI assistant."
        if task.structure:
            system_prompt += (
                "\n\nIMPORTANT: Respond ONLY with valid JSON matching the "
                "requested structure. No markdown fences, no explanation, "
                "just the raw JSON object."
            )

        try:
            # Use HomeclawAgent.process_query (full pipeline: tools, RAG, etc.)
            result = await self._agent.process_query(
                user_query=task.instructions,
                system_prompt=system_prompt,
            )
        except Exception as err:
            _LOGGER.error("AI Task generation raised an exception: %s", err)
            raise HomeAssistantError("AI Task generation failed") from err

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            _LOGGER.error("AI Task generation failed: %s", error)
            raise HomeAssistantError("AI Task generation failed")

        response_text = result.get("answer", "")

        # Parse structured output if schema was provided
        data = response_text
        if task.structure and response_text:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                _LOGGER.warning(
                    "Failed to parse AI Task response as JSON, returning raw text"
                )

        return ai_task.GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=data,
        )
