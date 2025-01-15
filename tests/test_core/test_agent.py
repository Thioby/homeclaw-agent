"""Tests for Agent orchestrator class."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.core.agent import Agent


class MockProvider:
    """Mock AI provider for testing."""

    def __init__(self, response: str = "Test response") -> None:
        """Initialize with a canned response."""
        self._response = response
        self.get_response = AsyncMock(return_value=response)
        self.supports_tools = True


class MockHass:
    """Mock Home Assistant instance."""

    def __init__(self) -> None:
        """Initialize mock hass."""
        self.states = MagicMock()
        self.services = MagicMock()
        self.data = {}
        self.config = MagicMock()


class TestAgentInitWithProvider:
    """Tests for Agent initialization with AI provider."""

    def test_init_with_provider(self) -> None:
        """Test that Agent initializes with an AI provider."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        assert agent.hass is hass
        assert agent.provider is provider

    def test_init_creates_query_processor(self) -> None:
        """Test that Agent creates a QueryProcessor on init."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        assert agent._query_processor is not None
        assert agent._query_processor.provider is provider

    def test_init_creates_response_parser(self) -> None:
        """Test that Agent creates a ResponseParser on init."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        assert agent._response_parser is not None

    def test_init_creates_conversation_manager(self) -> None:
        """Test that Agent creates a ConversationManager on init."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        assert agent._conversation is not None

    def test_init_with_custom_max_iterations(self) -> None:
        """Test that Agent passes max_iterations to QueryProcessor."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider, max_iterations=5)

        assert agent._query_processor.max_iterations == 5

    def test_init_with_system_prompt(self) -> None:
        """Test that Agent stores system_prompt."""
        hass = MockHass()
        provider = MockProvider()
        prompt = "You are a helpful home assistant."

        agent = Agent(hass=hass, provider=provider, system_prompt=prompt)

        assert agent._system_prompt == prompt


class TestAgentInitWithManagers:
    """Tests for Agent initialization with manager instances."""

    def test_init_with_entity_manager(self) -> None:
        """Test that Agent accepts an EntityManager instance."""
        hass = MockHass()
        provider = MockProvider()
        entity_manager = MagicMock()

        agent = Agent(hass=hass, provider=provider, entity_manager=entity_manager)

        assert agent._entity_manager is entity_manager

    def test_init_with_registry_manager(self) -> None:
        """Test that Agent accepts a RegistryManager instance."""
        hass = MockHass()
        provider = MockProvider()
        registry_manager = MagicMock()

        agent = Agent(hass=hass, provider=provider, registry_manager=registry_manager)

        assert agent._registry_manager is registry_manager

    def test_init_with_automation_manager(self) -> None:
        """Test that Agent accepts an AutomationManager instance."""
        hass = MockHass()
        provider = MockProvider()
        automation_manager = MagicMock()

        agent = Agent(hass=hass, provider=provider, automation_manager=automation_manager)

        assert agent._automation_manager is automation_manager

    def test_init_with_dashboard_manager(self) -> None:
        """Test that Agent accepts a DashboardManager instance."""
        hass = MockHass()
        provider = MockProvider()
        dashboard_manager = MagicMock()

        agent = Agent(hass=hass, provider=provider, dashboard_manager=dashboard_manager)

        assert agent._dashboard_manager is dashboard_manager

    def test_init_with_control_manager(self) -> None:
        """Test that Agent accepts a ControlManager instance."""
        hass = MockHass()
        provider = MockProvider()
        control_manager = MagicMock()

        agent = Agent(hass=hass, provider=provider, control_manager=control_manager)

        assert agent._control_manager is control_manager

    def test_init_with_all_managers(self) -> None:
        """Test that Agent accepts all managers."""
        hass = MockHass()
        provider = MockProvider()
        entity_manager = MagicMock()
        registry_manager = MagicMock()
        automation_manager = MagicMock()
        dashboard_manager = MagicMock()
        control_manager = MagicMock()

        agent = Agent(
            hass=hass,
            provider=provider,
            entity_manager=entity_manager,
            registry_manager=registry_manager,
            automation_manager=automation_manager,
            dashboard_manager=dashboard_manager,
            control_manager=control_manager,
        )

        assert agent._entity_manager is entity_manager
        assert agent._registry_manager is registry_manager
        assert agent._automation_manager is automation_manager
        assert agent._dashboard_manager is dashboard_manager
        assert agent._control_manager is control_manager


class TestProcessQueryDelegatesToProcessor:
    """Tests for process_query delegating to QueryProcessor."""

    @pytest.mark.asyncio
    async def test_process_query_delegates_to_processor(self) -> None:
        """Test that process_query delegates to QueryProcessor.process()."""
        hass = MockHass()
        provider = MockProvider(response="AI response")

        agent = Agent(hass=hass, provider=provider)
        result = await agent.process_query("What is the weather?")

        assert result["success"] is True
        assert result["response"] == "AI response"
        provider.get_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_query_uses_conversation_history(self) -> None:
        """Test that process_query includes conversation history."""
        hass = MockHass()
        provider = MockProvider(response="Response 1")

        agent = Agent(hass=hass, provider=provider)

        # First query
        await agent.process_query("First question")

        # Second query
        provider.get_response.reset_mock()
        provider.get_response.return_value = "Response 2"
        await agent.process_query("Second question")

        # Verify the second call includes history
        call_args = provider.get_response.call_args.args[0]
        # Should have first user message, first assistant response, and second user message
        assert len(call_args) >= 3

    @pytest.mark.asyncio
    async def test_process_query_uses_system_prompt(self) -> None:
        """Test that process_query uses the configured system prompt."""
        hass = MockHass()
        provider = MockProvider(response="Helpful response")
        prompt = "You are a home automation assistant."

        agent = Agent(hass=hass, provider=provider, system_prompt=prompt)
        await agent.process_query("Turn on the lights")

        # Verify system prompt was passed
        call_args = provider.get_response.call_args.args[0]
        assert call_args[0]["role"] == "system"
        assert call_args[0]["content"] == prompt

    @pytest.mark.asyncio
    async def test_process_query_passes_kwargs(self) -> None:
        """Test that extra kwargs are passed to processor."""
        hass = MockHass()
        provider = MockProvider(response="Response with tools")

        agent = Agent(hass=hass, provider=provider)
        tools = [{"name": "test_tool", "description": "A test tool"}]
        await agent.process_query("Use a tool", tools=tools)

        # Verify tools were passed
        call_kwargs = provider.get_response.call_args.kwargs
        assert call_kwargs.get("tools") == tools


class TestGetEntityStateDelegatesToManager:
    """Tests for get_entity_state delegating to EntityManager."""

    def test_get_entity_state_delegates_to_manager(self) -> None:
        """Test that get_entity_state delegates to EntityManager."""
        hass = MockHass()
        provider = MockProvider()
        entity_manager = MagicMock()
        entity_manager.get_entity_state.return_value = {
            "entity_id": "light.living_room",
            "state": "on",
        }

        agent = Agent(hass=hass, provider=provider, entity_manager=entity_manager)
        result = agent.get_entity_state("light.living_room")

        entity_manager.get_entity_state.assert_called_once_with("light.living_room")
        assert result["entity_id"] == "light.living_room"
        assert result["state"] == "on"

    def test_get_entity_state_lazy_init(self) -> None:
        """Test that EntityManager is lazily initialized if not provided."""
        hass = MockHass()
        provider = MockProvider()

        # Mock the entity manager import and creation
        with patch(
            "custom_components.homeclaw.managers.entity_manager.EntityManager"
        ) as MockEntityManager:
            mock_em = MagicMock()
            mock_em.get_entity_state.return_value = {"entity_id": "light.test", "state": "off"}
            MockEntityManager.return_value = mock_em

            agent = Agent(hass=hass, provider=provider)
            result = agent.get_entity_state("light.test")

            MockEntityManager.assert_called_once_with(hass)
            mock_em.get_entity_state.assert_called_once_with("light.test")

    def test_get_entities_by_domain_delegates(self) -> None:
        """Test that get_entities_by_domain delegates to EntityManager."""
        hass = MockHass()
        provider = MockProvider()
        entity_manager = MagicMock()
        entity_manager.get_entities_by_domain.return_value = [
            {"entity_id": "light.one", "state": "on"},
            {"entity_id": "light.two", "state": "off"},
        ]

        agent = Agent(hass=hass, provider=provider, entity_manager=entity_manager)
        result = agent.get_entities_by_domain("light")

        entity_manager.get_entities_by_domain.assert_called_once_with("light")
        assert len(result) == 2


class TestCallServiceDelegatesToControl:
    """Tests for call_service delegating to ControlManager."""

    @pytest.mark.asyncio
    async def test_call_service_delegates_to_control(self) -> None:
        """Test that call_service delegates to ControlManager."""
        hass = MockHass()
        provider = MockProvider()
        control_manager = MagicMock()
        control_manager.call_service = AsyncMock(return_value={"success": True})

        agent = Agent(hass=hass, provider=provider, control_manager=control_manager)
        result = await agent.call_service("light", "turn_on", target={"entity_id": "light.test"})

        control_manager.call_service.assert_called_once_with(
            "light", "turn_on", target={"entity_id": "light.test"}, data=None
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_turn_on_delegates_to_control(self) -> None:
        """Test that turn_on delegates to ControlManager."""
        hass = MockHass()
        provider = MockProvider()
        control_manager = MagicMock()
        control_manager.turn_on = AsyncMock(return_value={"success": True})

        agent = Agent(hass=hass, provider=provider, control_manager=control_manager)
        result = await agent.turn_on("light.living_room", brightness=255)

        control_manager.turn_on.assert_called_once_with("light.living_room", brightness=255)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_turn_off_delegates_to_control(self) -> None:
        """Test that turn_off delegates to ControlManager."""
        hass = MockHass()
        provider = MockProvider()
        control_manager = MagicMock()
        control_manager.turn_off = AsyncMock(return_value={"success": True})

        agent = Agent(hass=hass, provider=provider, control_manager=control_manager)
        result = await agent.turn_off("light.living_room")

        control_manager.turn_off.assert_called_once_with("light.living_room")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_call_service_lazy_init(self) -> None:
        """Test that ControlManager is lazily initialized if not provided."""
        hass = MockHass()
        provider = MockProvider()

        with patch(
            "custom_components.homeclaw.managers.control_manager.ControlManager"
        ) as MockControlManager:
            mock_cm = MagicMock()
            mock_cm.call_service = AsyncMock(return_value={"success": True})
            MockControlManager.return_value = mock_cm

            agent = Agent(hass=hass, provider=provider)
            result = await agent.call_service("switch", "toggle")

            MockControlManager.assert_called_once_with(hass)
            mock_cm.call_service.assert_called_once()


class TestCreateAutomationDelegatesToManager:
    """Tests for create_automation delegating to AutomationManager."""

    @pytest.mark.asyncio
    async def test_create_automation_delegates_to_manager(self) -> None:
        """Test that create_automation delegates to AutomationManager."""
        hass = MockHass()
        provider = MockProvider()
        automation_manager = MagicMock()
        automation_manager.create_automation = AsyncMock(
            return_value={"success": True, "id": "auto_123"}
        )

        agent = Agent(hass=hass, provider=provider, automation_manager=automation_manager)
        config = {"trigger": [{"platform": "sun"}], "action": [{"service": "light.turn_on"}]}
        result = await agent.create_automation(config)

        automation_manager.create_automation.assert_called_once_with(config)
        assert result["success"] is True
        assert result["id"] == "auto_123"

    def test_get_automations_delegates_to_manager(self) -> None:
        """Test that get_automations delegates to AutomationManager."""
        hass = MockHass()
        provider = MockProvider()
        automation_manager = MagicMock()
        automation_manager.get_automations.return_value = [
            {"entity_id": "automation.test", "state": "on"}
        ]

        agent = Agent(hass=hass, provider=provider, automation_manager=automation_manager)
        result = agent.get_automations()

        automation_manager.get_automations.assert_called_once()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_automation_lazy_init(self) -> None:
        """Test that AutomationManager is lazily initialized if not provided."""
        hass = MockHass()
        provider = MockProvider()

        with patch(
            "custom_components.homeclaw.managers.automation_manager.AutomationManager"
        ) as MockAutomationManager:
            mock_am = MagicMock()
            mock_am.create_automation = AsyncMock(return_value={"success": True, "id": "new"})
            MockAutomationManager.return_value = mock_am

            agent = Agent(hass=hass, provider=provider)
            config = {"trigger": [], "action": []}
            await agent.create_automation(config)

            MockAutomationManager.assert_called_once_with(hass)


class TestGetDashboardDelegatesToManager:
    """Tests for dashboard operations delegating to DashboardManager."""

    @pytest.mark.asyncio
    async def test_get_dashboards_delegates_to_manager(self) -> None:
        """Test that get_dashboards delegates to DashboardManager."""
        hass = MockHass()
        provider = MockProvider()
        dashboard_manager = MagicMock()
        dashboard_manager.get_dashboards = AsyncMock(
            return_value=[{"url_path": "test", "title": "Test Dashboard"}]
        )

        agent = Agent(hass=hass, provider=provider, dashboard_manager=dashboard_manager)
        result = await agent.get_dashboards()

        dashboard_manager.get_dashboards.assert_called_once()
        assert len(result) == 1
        assert result[0]["title"] == "Test Dashboard"

    @pytest.mark.asyncio
    async def test_create_dashboard_delegates_to_manager(self) -> None:
        """Test that create_dashboard delegates to DashboardManager."""
        hass = MockHass()
        provider = MockProvider()
        dashboard_manager = MagicMock()
        dashboard_manager.create_dashboard = AsyncMock(
            return_value={"success": True, "url_path": "new-dash"}
        )

        agent = Agent(hass=hass, provider=provider, dashboard_manager=dashboard_manager)
        config = {"title": "New Dashboard", "views": []}
        result = await agent.create_dashboard(config, dashboard_id="new-dash")

        dashboard_manager.create_dashboard.assert_called_once_with(config, "new-dash")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_dashboards_lazy_init(self) -> None:
        """Test that DashboardManager is lazily initialized if not provided."""
        hass = MockHass()
        provider = MockProvider()

        with patch(
            "custom_components.homeclaw.managers.dashboard_manager.DashboardManager"
        ) as MockDashboardManager:
            mock_dm = MagicMock()
            mock_dm.get_dashboards = AsyncMock(return_value=[])
            MockDashboardManager.return_value = mock_dm

            agent = Agent(hass=hass, provider=provider)
            await agent.get_dashboards()

            MockDashboardManager.assert_called_once_with(hass)


class TestConversationHistoryManaged:
    """Tests for conversation history management."""

    def test_conversation_history_managed(self) -> None:
        """Test that Agent uses ConversationManager for history."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        # Conversation manager should be initialized
        assert agent._conversation is not None
        assert agent.get_conversation_history() == []

    @pytest.mark.asyncio
    async def test_successful_query_updates_history(self) -> None:
        """Test that successful queries update conversation history."""
        hass = MockHass()
        provider = MockProvider(response="Hello there!")

        agent = Agent(hass=hass, provider=provider)
        await agent.process_query("Hi")

        history = agent.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hi"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hello there!"

    @pytest.mark.asyncio
    async def test_failed_query_does_not_update_history(self) -> None:
        """Test that failed queries do not update conversation history."""
        hass = MockHass()
        provider = MockProvider()
        provider.get_response = AsyncMock(side_effect=Exception("API Error"))

        agent = Agent(hass=hass, provider=provider)
        result = await agent.process_query("Fail please")

        assert result["success"] is False
        history = agent.get_conversation_history()
        # History should remain empty after failed query
        assert len(history) == 0

    def test_clear_conversation(self) -> None:
        """Test that clear_conversation clears the history."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        # Manually add some messages to conversation
        agent._conversation.add_user_message("Test message")
        agent._conversation.add_assistant_message("Test response")

        assert len(agent.get_conversation_history()) == 2

        agent.clear_conversation()

        assert len(agent.get_conversation_history()) == 0

    def test_get_conversation_history_returns_copy(self) -> None:
        """Test that get_conversation_history returns messages."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)
        agent._conversation.add_user_message("Hello")

        history = agent.get_conversation_history()
        assert len(history) == 1
        assert history[0]["content"] == "Hello"


class TestRegistryOperations:
    """Tests for registry operations delegating to RegistryManager."""

    def test_get_entities_by_area_delegates(self) -> None:
        """Test that get_entities_by_area delegates to RegistryManager."""
        hass = MockHass()
        provider = MockProvider()
        registry_manager = MagicMock()
        registry_manager.get_entities_by_area.return_value = [
            {"entity_id": "light.living_room", "area_id": "living_room"}
        ]

        agent = Agent(hass=hass, provider=provider, registry_manager=registry_manager)
        result = agent.get_entities_by_area("living_room")

        registry_manager.get_entities_by_area.assert_called_once_with("living_room")
        assert len(result) == 1

    def test_get_all_areas_delegates(self) -> None:
        """Test that get_all_areas delegates to RegistryManager."""
        hass = MockHass()
        provider = MockProvider()
        registry_manager = MagicMock()
        registry_manager.get_all_areas.return_value = [
            {"id": "living_room", "name": "Living Room"},
            {"id": "bedroom", "name": "Bedroom"},
        ]

        agent = Agent(hass=hass, provider=provider, registry_manager=registry_manager)
        result = agent.get_all_areas()

        registry_manager.get_all_areas.assert_called_once()
        assert len(result) == 2

    def test_get_entities_by_area_lazy_init(self) -> None:
        """Test that RegistryManager is lazily initialized if not provided."""
        hass = MockHass()
        provider = MockProvider()

        with patch(
            "custom_components.homeclaw.managers.registry_manager.RegistryManager"
        ) as MockRegistryManager:
            mock_rm = MagicMock()
            mock_rm.get_entities_by_area.return_value = []
            MockRegistryManager.return_value = mock_rm

            agent = Agent(hass=hass, provider=provider)
            agent.get_entities_by_area("kitchen")

            MockRegistryManager.assert_called_once_with(hass)
