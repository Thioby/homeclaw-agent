"""Agent orchestrator for Homeclaw.

This is a slim orchestrator that delegates to specialized components:
- QueryProcessor for AI query handling
- ResponseParser for parsing AI responses
- ConversationManager for conversation history
- Various managers for Home Assistant operations

This replaces the 5000+ LOC God Class with a focused coordinator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator

from .query_processor import QueryProcessor
from .response_parser import ResponseParser
from .conversation import ConversationManager

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from ..providers.registry import AIProvider
    from ..managers.entity_manager import EntityManager
    from ..managers.registry_manager import RegistryManager
    from ..managers.automation_manager import AutomationManager
    from ..managers.dashboard_manager import DashboardManager
    from ..managers.control_manager import ControlManager


class Agent:
    """Slim orchestrator that delegates to specialized components.

    This class acts as the main entry point for AI agent functionality,
    coordinating between the AI provider, conversation management, and
    Home Assistant managers.

    Attributes:
        hass: Home Assistant instance.
        provider: AI provider for generating responses.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        provider: AIProvider,
        entity_manager: EntityManager | None = None,
        registry_manager: RegistryManager | None = None,
        automation_manager: AutomationManager | None = None,
        dashboard_manager: DashboardManager | None = None,
        control_manager: ControlManager | None = None,
        system_prompt: str | None = None,
        max_iterations: int = 10,
    ) -> None:
        """Initialize the Agent orchestrator.

        Args:
            hass: Home Assistant instance.
            provider: AI provider to use for generating responses.
            entity_manager: Optional EntityManager instance for entity operations.
            registry_manager: Optional RegistryManager instance for registry lookups.
            automation_manager: Optional AutomationManager for automation operations.
            dashboard_manager: Optional DashboardManager for dashboard operations.
            control_manager: Optional ControlManager for service calls.
            system_prompt: Optional system prompt for AI context.
            max_iterations: Maximum tool call iterations (default 10).
        """
        self.hass = hass
        self.provider = provider

        # Core components - always initialized
        self._query_processor = QueryProcessor(provider, max_iterations=max_iterations)
        self._response_parser = ResponseParser()
        self._conversation = ConversationManager()

        # Managers - lazy init if not provided
        self._entity_manager = entity_manager
        self._registry_manager = registry_manager
        self._automation_manager = automation_manager
        self._dashboard_manager = dashboard_manager
        self._control_manager = control_manager

        self._system_prompt = system_prompt

    # === Query Processing ===

    async def process_query(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Process a user query through the AI provider.

        Delegates to QueryProcessor and updates conversation history on success.

        Args:
            query: The user's query text.
            **kwargs: Additional arguments passed to the processor (e.g., tools).

        Returns:
            Dict with:
                - success: True if successful, False otherwise.
                - response: The AI response text (on success).
                - error: Error message (on failure).
        """
        # Allow callers to override the system prompt (e.g. subagent/heartbeat)
        effective_system_prompt = (
            kwargs.pop("system_prompt_override", None) or self._system_prompt
        )

        result = await self._query_processor.process(
            query=query,
            messages=self._conversation.get_messages(),
            system_prompt=effective_system_prompt,
            **kwargs,
        )

        if result.get("success"):
            self._conversation.add_user_message(query)
            self._conversation.add_assistant_message(result["response"])

        return result

    async def process_query_stream(
        self, query: str, **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a user query response through the AI provider.

        Delegates to QueryProcessor and updates conversation history on completion.

        Args:
            query: The user's query text.
            **kwargs: Additional arguments passed to the processor (e.g., tools).

        Yields:
            Dict chunks with:
                - type: "text" | "tool_call" | "tool_result" | "error" | "complete"
                - content: The text content (for type="text")
                - name: Tool name (for type="tool_call" | "tool_result")
                - args: Tool arguments (for type="tool_call")
                - result: Tool result (for type="tool_result")
                - message: Error message (for type="error")
                - messages: Updated message list (for type="complete")
        """
        accumulated_text = ""
        success = False

        # Use session history from storage if provided, otherwise fall back
        # to the agent's in-memory conversation (which is per-provider, not per-session).
        # Use `is not None` to allow empty lists (first turn of a new conversation)
        # without falling back to global in-memory history.
        conversation_history = kwargs.pop("conversation_history", None)
        messages = (
            conversation_history
            if conversation_history is not None
            else self._conversation.get_messages()
        )

        # Allow system_prompt override from kwargs (for identity/onboarding)
        system_prompt = kwargs.pop("system_prompt_override", None) or kwargs.pop(
            "system_prompt", self._system_prompt
        )

        async for chunk in self._query_processor.process_stream(
            query=query,
            messages=messages,
            system_prompt=system_prompt,
            **kwargs,
        ):
            # Track accumulated text for conversation history
            if chunk.get("type") == "text":
                accumulated_text += chunk.get("content", "")
            elif chunk.get("type") == "complete":
                success = True

            # Yield all chunks to caller
            yield chunk

        # Update in-memory conversation history if successful
        if success and accumulated_text:
            self._conversation.add_user_message(query)
            self._conversation.add_assistant_message(accumulated_text)

    # === Entity Operations (delegate to EntityManager) ===

    def get_entity_state(self, entity_id: str) -> dict[str, Any] | None:
        """Get the state of a specific entity.

        Args:
            entity_id: The entity ID to look up.

        Returns:
            Dictionary with entity state information, or None if not found.
        """
        return self._get_entity_manager().get_entity_state(entity_id)

    def get_entities_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """Get all entities for a specific domain.

        Args:
            domain: The domain to filter by (e.g., 'light', 'sensor').

        Returns:
            List of entity state dictionaries.
        """
        return self._get_entity_manager().get_entities_by_domain(domain)

    # === Control Operations (delegate to ControlManager) ===

    async def call_service(
        self,
        domain: str,
        service: str,
        target: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Call a Home Assistant service.

        Args:
            domain: The service domain (e.g., 'light', 'switch').
            service: The service name (e.g., 'turn_on', 'turn_off').
            target: Optional target specification (entity_id, area_id, etc.).
            data: Optional additional service data.
            **kwargs: Additional keyword arguments passed to ControlManager.

        Returns:
            Dictionary with success status and optional error message.
        """
        return await self._get_control_manager().call_service(
            domain, service, target=target, data=data, **kwargs
        )

    async def turn_on(self, entity_id: str, **kwargs: Any) -> dict[str, Any]:
        """Turn on an entity.

        Args:
            entity_id: The entity ID to turn on.
            **kwargs: Additional service data (e.g., brightness for lights).

        Returns:
            Dictionary with success status and optional error message.
        """
        return await self._get_control_manager().turn_on(entity_id, **kwargs)

    async def turn_off(self, entity_id: str, **kwargs: Any) -> dict[str, Any]:
        """Turn off an entity.

        Args:
            entity_id: The entity ID to turn off.
            **kwargs: Additional service data.

        Returns:
            Dictionary with success status and optional error message.
        """
        return await self._get_control_manager().turn_off(entity_id, **kwargs)

    # === Automation Operations ===

    async def create_automation(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a new automation.

        Args:
            config: Automation configuration dictionary.

        Returns:
            Dict with 'success' boolean and 'id' of the created automation.
        """
        return await self._get_automation_manager().create_automation(config)

    def get_automations(self) -> list[dict[str, Any]]:
        """Get all automation entities.

        Returns:
            List of automation entity state dictionaries.
        """
        return self._get_automation_manager().get_automations()

    # === Dashboard Operations ===

    async def get_dashboards(self) -> list[dict[str, Any]]:
        """Get list of all dashboards.

        Returns:
            List of dashboard info dictionaries.
        """
        return await self._get_dashboard_manager().get_dashboards()

    async def create_dashboard(
        self, config: dict[str, Any], dashboard_id: str | None = None
    ) -> dict[str, Any]:
        """Create a new dashboard.

        Args:
            config: Dashboard configuration with title, url_path, views, etc.
            dashboard_id: Optional explicit dashboard ID.

        Returns:
            Result dictionary with success status or error.
        """
        return await self._get_dashboard_manager().create_dashboard(
            config, dashboard_id
        )

    # === Registry Operations ===

    def get_entities_by_area(self, area_id: str) -> list[dict[str, Any]]:
        """Get all entities in a specific area.

        Args:
            area_id: The area ID to filter by.

        Returns:
            List of entity info dictionaries.
        """
        return self._get_registry_manager().get_entities_by_area(area_id)

    def get_all_areas(self) -> list[dict[str, Any]]:
        """Get all areas from the area registry.

        Returns:
            List of area info dictionaries.
        """
        return self._get_registry_manager().get_all_areas()

    # === Conversation ===

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation.clear()

    def get_conversation_history(self) -> list[dict[str, str]]:
        """Get the current conversation history.

        Returns:
            List of message dictionaries with role and content.
        """
        return self._conversation.get_messages()

    # === Lazy initialization helpers ===

    def _get_entity_manager(self) -> EntityManager:
        """Get or create the EntityManager instance.

        Returns:
            EntityManager instance.
        """
        if self._entity_manager is None:
            from ..managers.entity_manager import EntityManager

            self._entity_manager = EntityManager(self.hass)
            self._entity_manager.async_setup()
        return self._entity_manager

    def _get_control_manager(self) -> ControlManager:
        """Get or create the ControlManager instance.

        Returns:
            ControlManager instance.
        """
        if self._control_manager is None:
            from ..managers.control_manager import ControlManager

            self._control_manager = ControlManager(self.hass)
        return self._control_manager

    def _get_automation_manager(self) -> AutomationManager:
        """Get or create the AutomationManager instance.

        Returns:
            AutomationManager instance.
        """
        if self._automation_manager is None:
            from ..managers.automation_manager import AutomationManager

            self._automation_manager = AutomationManager(self.hass)
        return self._automation_manager

    def _get_dashboard_manager(self) -> DashboardManager:
        """Get or create the DashboardManager instance.

        Returns:
            DashboardManager instance.
        """
        if self._dashboard_manager is None:
            from ..managers.dashboard_manager import DashboardManager

            self._dashboard_manager = DashboardManager(self.hass)
        return self._dashboard_manager

    def _get_registry_manager(self) -> RegistryManager:
        """Get or create the RegistryManager instance.

        Returns:
            RegistryManager instance.
        """
        if self._registry_manager is None:
            from ..managers.registry_manager import RegistryManager

            self._registry_manager = RegistryManager(self.hass)
        return self._registry_manager
