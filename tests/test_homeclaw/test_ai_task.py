"""Unit tests for Homeclaw AI Task Entity (ai_task.py).

Tests the HomeclawAITaskEntity bridge between HA's AI Task interface
and Homeclaw's agent infrastructure.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.ai_task import (
    HomeclawAITaskEntity,
    async_setup_entry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    provider: str = "openai",
    entry_id: str = "test_entry",
) -> HomeclawAITaskEntity:
    """Create a HomeclawAITaskEntity with mocked dependencies."""
    config_entry = MagicMock()
    config_entry.entry_id = entry_id
    config_entry.data = {"ai_provider": provider}

    agent = MagicMock()
    agent.hass = MagicMock()
    # Mock HomeclawAgent.process_query (the wrapper, not inner Agent)
    agent.process_query = AsyncMock(
        return_value={"success": True, "answer": "Hello world"}
    )

    entity = HomeclawAITaskEntity(config_entry, provider, agent)
    entity.hass = agent.hass
    return entity


def _make_task(
    instructions: str = "Generate a grocery list",
    name: str = "test_task",
    structure=None,
    attachments=None,
):
    """Create a fake GenDataTask."""
    task = MagicMock()
    task.instructions = instructions
    task.name = name
    task.structure = structure
    task.attachments = attachments
    return task


def _make_chat_log(conversation_id: str = "chat-123"):
    """Create a fake ChatLog."""
    chat_log = MagicMock()
    chat_log.conversation_id = conversation_id
    return chat_log


# ===========================================================================
# async_setup_entry
# ===========================================================================

class TestAsyncSetupEntry:

    @pytest.mark.asyncio
    async def test_creates_entity_for_valid_agent(self):
        hass = MagicMock()
        agent = MagicMock()
        hass.data = {DOMAIN: {"agents": {"openai": agent}}}

        config_entry = MagicMock()
        config_entry.data = {"ai_provider": "openai"}
        config_entry.entry_id = "entry-1"

        async_add_entities = MagicMock()

        await async_setup_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], HomeclawAITaskEntity)

    @pytest.mark.asyncio
    async def test_skips_when_no_agent(self):
        hass = MagicMock()
        hass.data = {DOMAIN: {"agents": {}}}

        config_entry = MagicMock()
        config_entry.data = {"ai_provider": "openai"}

        async_add_entities = MagicMock()

        await async_setup_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_empty_hass_data(self):
        hass = MagicMock()
        hass.data = {}

        config_entry = MagicMock()
        config_entry.data = {"ai_provider": "openai"}

        async_add_entities = MagicMock()

        await async_setup_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_not_called()


# ===========================================================================
# Entity Properties
# ===========================================================================

class TestEntityProperties:

    def test_name(self):
        entity = _make_entity()
        assert entity._attr_name == "AI Task"

    def test_unique_id(self):
        entity = _make_entity(entry_id="entry-42")
        assert entity._attr_unique_id == "entry-42-ai-task"

    def test_supported_features(self):
        from homeassistant.components.ai_task import AITaskEntityFeature

        entity = _make_entity()
        assert entity._attr_supported_features == AITaskEntityFeature.GENERATE_DATA

    def test_device_info(self):
        entity = _make_entity(provider="anthropic", entry_id="entry-99")
        device_info = entity._attr_device_info
        assert (DOMAIN, "entry-99") in device_info["identifiers"]
        assert "Anthropic" in device_info["name"]
        assert device_info["model"] == "anthropic"

    def test_device_info_provider_title_case(self):
        entity = _make_entity(provider="gemini_oauth")
        assert "Gemini Oauth" in entity._attr_device_info["name"]


# ===========================================================================
# _async_generate_data
# ===========================================================================

class TestAsyncGenerateData:

    @pytest.mark.asyncio
    async def test_text_response(self):
        entity = _make_entity()
        task = _make_task(instructions="Write a poem")
        chat_log = _make_chat_log()

        result = await entity._async_generate_data(task, chat_log)

        assert result.conversation_id == "chat-123"
        assert result.data == "Hello world"
        entity._agent.process_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_structured_json_response(self):
        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            return_value={"success": True, "answer": '{"items": ["milk", "eggs"]}'}
        )

        task = _make_task(
            instructions="Generate a grocery list",
            structure=MagicMock(),  # non-None signals structured output
        )
        chat_log = _make_chat_log()

        result = await entity._async_generate_data(task, chat_log)

        assert result.data == {"items": ["milk", "eggs"]}

    @pytest.mark.asyncio
    async def test_structured_json_parse_failure_returns_raw_text(self):
        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            return_value={"success": True, "answer": "not valid json"}
        )

        task = _make_task(structure=MagicMock())
        chat_log = _make_chat_log()

        result = await entity._async_generate_data(task, chat_log)

        # Should fall back to raw text when JSON parsing fails
        assert result.data == "not valid json"

    @pytest.mark.asyncio
    async def test_agent_error_raises_home_assistant_error(self):
        from homeassistant.exceptions import HomeAssistantError

        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            return_value={"success": False, "error": "API quota exceeded"}
        )

        task = _make_task()
        chat_log = _make_chat_log()

        with pytest.raises(HomeAssistantError, match="AI Task generation failed"):
            await entity._async_generate_data(task, chat_log)

    @pytest.mark.asyncio
    async def test_error_message_not_leaked_to_exception(self):
        """Internal error details should not appear in the user-facing exception."""
        from homeassistant.exceptions import HomeAssistantError

        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            return_value={"success": False, "error": "secret internal detail xyz"}
        )

        task = _make_task()
        chat_log = _make_chat_log()

        with pytest.raises(HomeAssistantError) as exc_info:
            await entity._async_generate_data(task, chat_log)

        assert "secret internal detail" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raised_exception_is_caught_and_sanitized(self):
        """Exceptions from process_query should be caught and re-raised sanitized."""
        from homeassistant.exceptions import HomeAssistantError

        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            side_effect=RuntimeError("Connection refused to provider API")
        )

        task = _make_task()
        chat_log = _make_chat_log()

        with pytest.raises(HomeAssistantError, match="AI Task generation failed"):
            await entity._async_generate_data(task, chat_log)

    @pytest.mark.asyncio
    async def test_raised_exception_details_not_leaked(self):
        """Internal exception details should not appear in the user-facing error."""
        from homeassistant.exceptions import HomeAssistantError

        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            side_effect=RuntimeError("secret provider key abc123")
        )

        task = _make_task()
        chat_log = _make_chat_log()

        with pytest.raises(HomeAssistantError) as exc_info:
            await entity._async_generate_data(task, chat_log)

        assert "secret provider key" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_system_prompt_includes_json_instruction_for_structured(self):
        entity = _make_entity()
        task = _make_task(structure=MagicMock())
        chat_log = _make_chat_log()

        await entity._async_generate_data(task, chat_log)

        call_kwargs = entity._agent.process_query.call_args
        system_prompt = call_kwargs.kwargs.get("system_prompt", "")
        assert "JSON" in system_prompt

    @pytest.mark.asyncio
    async def test_system_prompt_plain_for_unstructured(self):
        entity = _make_entity()
        task = _make_task(structure=None)
        chat_log = _make_chat_log()

        await entity._async_generate_data(task, chat_log)

        call_kwargs = entity._agent.process_query.call_args
        system_prompt = call_kwargs.kwargs.get("system_prompt", "")
        assert "JSON" not in system_prompt

    @pytest.mark.asyncio
    async def test_instructions_passed_as_query(self):
        entity = _make_entity()
        task = _make_task(instructions="Summarize today's events")
        chat_log = _make_chat_log()

        await entity._async_generate_data(task, chat_log)

        call_args = entity._agent.process_query.call_args
        assert call_args.kwargs["user_query"] == "Summarize today's events"

    @pytest.mark.asyncio
    async def test_empty_response(self):
        entity = _make_entity()
        entity._agent.process_query = AsyncMock(
            return_value={"success": True, "answer": ""}
        )

        task = _make_task()
        chat_log = _make_chat_log()

        result = await entity._async_generate_data(task, chat_log)

        assert result.data == ""
