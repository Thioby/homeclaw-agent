"""Compatibility layer for migration from old HomeclawAgent to new Agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator

from .core.agent import Agent
from .core.conversation import ConversationManager
from .providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class HomeclawAgent:
    """Compatibility wrapper that delegates to new modular Agent.

    This class maintains the same interface as the old monolithic agent
    while internally using the new architecture.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize with same signature as old agent."""
        self.hass = hass
        self.config = config
        self.config_entry = config_entry

        # Determine provider and create new architecture components
        self._provider_name = config.get("ai_provider", "openai")
        self._setup_provider()
        self._setup_agent()

        # RAG manager (set externally)
        self._rag_manager = None

        _LOGGER.info(
            "HomeclawAgent initialized with new architecture (provider: %s)",
            self._provider_name,
        )

    def _setup_provider(self) -> None:
        """Create AI provider from config."""
        # Map old config keys to new provider config
        provider_config = self._build_provider_config()

        try:
            _LOGGER.info(
                "🔧 Creating provider '%s' via ProviderRegistry", self._provider_name
            )
            self._provider = ProviderRegistry.create(
                self._provider_name, self.hass, provider_config
            )
            _LOGGER.info(
                "✅ Provider created: %s (has get_response_stream: %s)",
                self._provider.__class__.__name__,
                hasattr(self._provider, "get_response_stream"),
            )
        except ValueError as e:
            # Fallback for OAuth providers or unknown providers
            # They map to base providers
            _LOGGER.warning(
                "❌ ProviderRegistry.create('%s') failed: %s - using fallback",
                self._provider_name,
                e,
            )
            base_provider = self._get_base_provider_name()
            _LOGGER.info("🔄 Falling back to base provider: %s", base_provider)
            self._provider = ProviderRegistry.create(
                base_provider, self.hass, provider_config
            )
            _LOGGER.info(
                "✅ Fallback provider created: %s", self._provider.__class__.__name__
            )

    def _get_base_provider_name(self) -> str:
        """Map OAuth provider names to base provider names.

        Note: gemini_oauth is now a registered provider, so it doesn't fall back,
        but we still need the mapping for model/token lookups.
        """
        mapping = {
            "anthropic_oauth": "anthropic",
            "gemini_oauth": "gemini",
            "openai_oauth": "openai",
        }
        return mapping.get(self._provider_name, "openai")

    def _build_provider_config(self) -> dict[str, Any]:
        """Build provider config from old config format."""
        provider = self._provider_name
        base_provider = self._get_base_provider_name()

        # OAuth providers use config_entry for tokens
        is_oauth_provider = provider.endswith("_oauth")

        # Get token for this provider (API key providers)
        token_keys = {
            "openai": "openai_token",
            "gemini": "gemini_token",
            "anthropic": "anthropic_token",
            "groq": "groq_token",
            "openrouter": "openrouter_token",
            "local": None,  # No token needed
        }

        token_key = token_keys.get(base_provider, f"{base_provider}_token")
        token = self.config.get(token_key, "") if token_key else ""

        # Get model for this provider
        models = self.config.get("models", {})

        # For OAuth providers, try provider name first (e.g., gemini_oauth),
        # then fall back to base provider (e.g., gemini)
        if is_oauth_provider:
            model = models.get(
                provider, models.get(base_provider, self._get_default_model(provider))
            )
        else:
            model = models.get(provider, self._get_default_model(provider))

        config: dict[str, Any] = {
            "token": token,
            "model": model,
            "api_url": self.config.get(f"{base_provider}_api_url"),
        }

        # OAuth providers need config_entry for token management
        if is_oauth_provider and self.config_entry:
            config["config_entry"] = self.config_entry

        return config

    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider."""
        defaults = {
            "openai": "gpt-4",
            "gemini": "gemini-2.5-flash",
            "gemini_oauth": "gemini-3-pro-preview",
            "anthropic": "claude-sonnet-4-5-20250929",
            "anthropic_oauth": "claude-sonnet-4-5-20250929",
            "groq": "llama-3.3-70b-versatile",
            "openrouter": "openai/gpt-4",
            "local": "llama2",
        }
        return defaults.get(provider, "gpt-4")

    def _setup_agent(self) -> None:
        """Create new Agent orchestrator."""
        from .managers.automation_manager import AutomationManager
        from .managers.control_manager import ControlManager
        from .managers.dashboard_manager import DashboardManager
        from .managers.entity_manager import EntityManager
        from .managers.registry_manager import RegistryManager

        self._agent = Agent(
            hass=self.hass,
            provider=self._provider,
            entity_manager=self._create_entity_manager(),
            registry_manager=RegistryManager(self.hass),
            automation_manager=AutomationManager(self.hass),
            dashboard_manager=DashboardManager(self.hass),
            control_manager=ControlManager(self.hass),
        )

    def _create_entity_manager(self):
        """Create an EntityManager with cache listener enabled."""
        from .managers.entity_manager import EntityManager

        em = EntityManager(self.hass)
        em.async_setup()
        return em

    # === PUBLIC API (same signatures as old agent) ===

    def _get_tools_for_provider(self) -> list[dict[str, Any]] | None:
        """Get CORE-tier tools in OpenAI format for the current provider.

        Only CORE tools are included in function-calling schemas by default.
        ON_DEMAND tools are listed as short descriptions in the system prompt
        and activated via the ``load_tool`` meta-tool at runtime.

        Returns:
            List of tools in OpenAI format, or None if provider doesn't support tools.
        """
        if not self._provider.supports_tools:
            return None

        try:
            from .function_calling import ToolSchemaConverter
            from .tools import ToolRegistry

            tools = ToolRegistry.get_core_tools(
                hass=self.hass,
                config=self.config,
            )

            if not tools:
                _LOGGER.debug("No CORE tools available for native function calling")
                return None

            openai_tools = ToolSchemaConverter.to_openai_format(tools)
            _LOGGER.debug(
                "Retrieved %d CORE tools for native function calling "
                "(ON_DEMAND tools available via load_tool)",
                len(tools),
            )
            return openai_tools

        except Exception as e:
            _LOGGER.warning("Failed to get tools for native function calling: %s", e)
            return None

    async def process_query(
        self,
        user_query: str,
        provider: str | None = None,
        model: str | None = None,
        debug: bool = False,
        conversation_history: list[dict] | None = None,
        user_id: str | None = None,
        session_id: str = "",
        denied_tools: frozenset[str] | None = None,
        system_prompt: str | None = None,
        max_iterations: int | None = None,
    ) -> dict[str, Any]:
        """Process a user query through the AI provider.

        Same signature as old HomeclawAgent.process_query().

        Args:
            user_query: The user's query text.
            provider: Provider name (used for context window lookup).
            model: Model ID override.
            debug: Enable debug mode.
            conversation_history: External conversation history.
            user_id: User ID for memory flush scoping.
            session_id: Session ID for memory flush context.
            denied_tools: Optional frozenset of tool names to block from execution.
            system_prompt: Optional system prompt override (e.g. for subagent/heartbeat).
            max_iterations: Override max tool-call iterations (default: agent's own limit).
        """
        # If external conversation history provided, use it
        if conversation_history:
            # Inject history into conversation manager
            self._agent._conversation.clear()
            for msg in conversation_history:
                self._agent._conversation.add_message(
                    msg.get("role", "user"), msg.get("content", "")
                )

        # Build kwargs
        kwargs: dict[str, Any] = {"hass": self.hass}  # Pass hass for tool execution
        if debug:
            kwargs["debug"] = debug
        if model:
            kwargs["model"] = model
        if user_id:
            kwargs["user_id"] = user_id
        if session_id:
            kwargs["session_id"] = session_id

        # Add tools for native function calling
        tools = self._get_tools_for_provider()
        if tools:
            # Auto-load ON_DEMAND tools when query obviously needs them
            auto_loaded = self._auto_load_tools(user_query, tools)
            if auto_loaded:
                _LOGGER.debug(
                    "Auto-loaded %d ON_DEMAND tool(s) in non-stream path",
                    len(auto_loaded),
                )
            # Filter out denied tools from the LLM tool list (first layer of defense)
            if denied_tools:
                tools = [
                    t
                    for t in tools
                    if t.get("function", {}).get("name") not in denied_tools
                ]
            kwargs["tools"] = tools

        # Pass denied_tools for ToolExecutor enforcement (second layer of defense)
        if denied_tools:
            kwargs["denied_tools"] = denied_tools

        # Context window for compaction
        from .models import get_context_window

        effective_provider = provider or self._provider_name
        kwargs["context_window"] = get_context_window(effective_provider, model)

        # Memory flush function for pre-compaction capture
        if self._rag_manager and self._rag_manager.is_initialized:
            mem_mgr = getattr(self._rag_manager, "_memory_manager", None)
            if mem_mgr:
                kwargs["memory_flush_fn"] = mem_mgr.flush_from_messages

        # Add RAG context if available
        if self._rag_manager:
            _LOGGER.debug("Starting RAG context retrieval...")
            rag_context = await self._get_rag_context(user_query, user_id=user_id)
            if rag_context:
                _LOGGER.debug("RAG context retrieved successfully, adding to kwargs")
                kwargs["rag_context"] = rag_context
            else:
                _LOGGER.debug("RAG returned empty context, not adding to kwargs")
        else:
            _LOGGER.debug("RAG manager not configured, skipping context retrieval")

        # System prompt: use override if provided, otherwise build default
        # (includes ON_DEMAND tool catalog for the LLM)
        # NOTE: Agent.process_query() only honors system_prompt_override, not system_prompt
        if system_prompt:
            kwargs["system_prompt_override"] = system_prompt
        else:
            default_prompt = await self._get_system_prompt(user_id or "")
            if default_prompt:
                kwargs["system_prompt_override"] = default_prompt

        # Pass max_iterations through kwargs (consumed by QueryProcessor.process)
        # — no shared state mutation, safe for concurrent async calls
        if max_iterations is not None:
            kwargs["max_iterations"] = max_iterations

        try:
            result = await self._agent.process_query(user_query, **kwargs)

            # Transform to old response format
            response = {
                "success": result.get("success", True),
                "answer": result.get("response", ""),
                "automation": result.get("automation"),
                "dashboard": result.get("dashboard"),
                "debug": result.get("debug") if debug else None,
            }
            # Propagate error from QueryProcessor (e.g. max iterations reached)
            if result.get("error"):
                response["error"] = result["error"]
            return response
        except Exception as e:
            _LOGGER.error("Error processing query: %s", e)
            return {
                "success": False,
                "error": str(e),
            }

    # === PUBLIC API — channels and MessageIntake use ONLY these ===

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
    ) -> AsyncGenerator[Any, None]:
        """Public streaming entry point.

        Builds all kwargs internally — callers never need to access
        ``_get_tools_for_provider``, ``_get_rag_context``, ``_get_system_prompt``,
        or ``get_context_window`` directly.

        Args:
            text: User message text.
            user_id: HA user ID (or shadow user ID for external channels).
            session_id: Session ID for context.
            model: Optional model override.
            conversation_history: Optional conversation history from storage.
            attachments: Optional list of ProcessedAttachment objects.
            channel_source: Origin channel (``"panel"``, ``"telegram"``, etc.).

        Yields:
            AgentEvent objects (TextEvent, ToolCallEvent, StatusEvent, etc.).
        """
        kwargs = self.build_query_kwargs(
            text,
            user_id=user_id,
            session_id=session_id,
            model=model,
            conversation_history=conversation_history,
            attachments=attachments,
            channel_source=channel_source,
        )

        # Add async parts: RAG context + system prompt
        if self._rag_manager:
            rag_context = await self._get_rag_context(text, user_id=user_id)
            if rag_context:
                kwargs["rag_context"] = rag_context

        system_prompt = await self._get_system_prompt(user_id)
        if system_prompt:
            kwargs["system_prompt"] = system_prompt

        async for event in self._agent.process_query_stream(text, **kwargs):
            yield event

    def build_query_kwargs(
        self,
        text: str,
        *,
        user_id: str,
        session_id: str = "",
        model: str | None = None,
        conversation_history: list[dict] | None = None,
        attachments: list | None = None,
        channel_source: str = "panel",
    ) -> dict[str, Any]:
        """Build kwargs dict for process_query / process_query_stream.

        Encapsulates all the boilerplate: tools, RAG context lookup, system
        prompt, context window, memory flush. No ``_agent`` access needed.

        Args:
            text: User message text.
            user_id: HA user ID.
            session_id: Session ID.
            model: Optional model override.
            conversation_history: Optional history from storage.
            attachments: Optional attachments.
            channel_source: Origin channel identifier.

        Returns:
            Dict of kwargs ready for ``process_query()`` or ``stream_query()``.
        """
        from .models import get_context_window

        kwargs: dict[str, Any] = {
            "hass": self.hass,
            "user_id": user_id,
            "session_id": session_id,
            "config": self.config,  # For tool instantiation (API keys, etc.)
        }

        if model:
            kwargs["model"] = model
        if conversation_history is not None:
            kwargs["conversation_history"] = conversation_history
        if attachments:
            kwargs["attachments"] = attachments

        # Tools — CORE tools always loaded; ON_DEMAND auto-loaded by heuristic
        tools = self._get_tools_for_provider()
        if tools:
            auto_loaded = self._auto_load_tools(text, tools)
            if auto_loaded:
                _LOGGER.debug(
                    "Auto-loaded %d ON_DEMAND tool(s) based on query hints",
                    len(auto_loaded),
                )
            kwargs["tools"] = tools

        # Context window for compaction
        kwargs["context_window"] = get_context_window(self._provider_name, model)

        # Memory flush for pre-compaction capture
        if self._rag_manager and self._rag_manager.is_initialized:
            mem_mgr = getattr(self._rag_manager, "_memory_manager", None)
            if mem_mgr:
                kwargs["memory_flush_fn"] = mem_mgr.flush_from_messages

        return kwargs

    @property
    def provider_name(self) -> str:
        """Public read-only access to the provider name."""
        return self._provider_name

    @property
    def rag_manager(self) -> Any:
        """Public read-only access to the RAG manager (may be None)."""
        return self._rag_manager

    async def get_system_prompt_for_user(self, user_id: str) -> str:
        """Public method to get the full system prompt for a user.

        Includes identity context, onboarding state, and current time.

        Args:
            user_id: HA user ID.

        Returns:
            Full system prompt string.
        """
        return await self._get_system_prompt(user_id)

    async def get_rag_context(
        self, query: str, user_id: str | None = None
    ) -> str | None:
        """Public method to retrieve RAG context for a query.

        Args:
            query: User query text.
            user_id: Optional user ID for memory recall.

        Returns:
            RAG context string, or None if unavailable.
        """
        return await self._get_rag_context(query, user_id=user_id)

    async def create_automation(self, automation_config: dict) -> dict[str, Any]:
        """Create a new automation."""
        return await self._agent.create_automation(automation_config)

    async def create_dashboard(self, dashboard_config: dict) -> dict[str, Any]:
        """Create a new dashboard."""
        return await self._agent.create_dashboard(dashboard_config)

    async def update_dashboard(
        self,
        dashboard_url: str,
        dashboard_config: dict,
    ) -> dict[str, Any]:
        """Update an existing dashboard."""
        return await self._agent._get_dashboard_manager().update_dashboard(
            dashboard_url, dashboard_config
        )

    async def save_user_prompt_history(
        self,
        user_id: str,
        history: list[str],
    ) -> dict[str, Any]:
        """Save user prompt history."""
        # This is a storage operation - delegate to storage module
        try:
            from .storage import save_prompt_history

            await save_prompt_history(self.hass, user_id, history)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def load_user_prompt_history(self, user_id: str) -> dict[str, Any]:
        """Load user prompt history."""
        try:
            from .storage import load_prompt_history

            history = await load_prompt_history(self.hass, user_id)
            return {"success": True, "history": history}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_rag_manager(self, rag_manager) -> None:
        """Set the RAG manager for semantic search."""
        self._rag_manager = rag_manager

    async def _get_rag_context(
        self, query: str, user_id: str | None = None
    ) -> str | None:
        """Get relevant context from RAG system.

        Args:
            query: User query text.
            user_id: Optional user ID for long-term memory recall.
        """
        if not self._rag_manager:
            _LOGGER.debug("RAG manager not configured, skipping context retrieval")
            return None
        try:
            _LOGGER.debug("Querying RAG for context: %s", query[:100])
            # RAGManager.get_relevant_context returns compressed context string
            context = await self._rag_manager.get_relevant_context(
                query, user_id=user_id
            )
            if context:
                _LOGGER.info("RAG found relevant context (%d chars)", len(context))
                _LOGGER.debug(
                    "RAG context preview: %s",
                    context[:300] if len(context) > 300 else context,
                )
                return context
            else:
                _LOGGER.debug("RAG returned no results for query")
        except Exception as e:
            _LOGGER.warning("RAG query failed: %s", e, exc_info=True)
        return None

    # Keyword hints for auto-loading ON_DEMAND tools without an extra LLM round-trip.
    # Keys are tool IDs, values are lowercase keyword lists.
    _AUTO_LOAD_HINTS: dict[str, list[str]] = {
        "web_search": [
            "search",
            "look up",
            "find online",
            "google",
            "latest news",
            "wyszukaj",
            "szukaj",
            "znajdź w internecie",
            "sprawdź online",
        ],
        "web_search_simple": [],  # covered by web_search hints
        "web_fetch": [
            "http://",
            "https://",
            "fetch",
            "read this url",
            "open link",
            "pobierz stronę",
            "otwórz link",
        ],
        "context7_resolve": [
            "documentation",
            "library docs",
            "api reference",
            "dokumentacja",
            "docs for",
        ],
        "context7_docs": [],  # covered by context7_resolve hints
        "identity_set": [
            "my name is",
            "call me",
            "change your name",
            "mam na imię",
            "nazywaj mnie",
        ],
    }

    def _auto_load_tools(
        self,
        query: str,
        tools: list[dict[str, Any]],
    ) -> list[str]:
        """Pre-load ON_DEMAND tools when the query obviously needs them.

        Scans the query for keyword hints and adds matching tool schemas
        to the ``tools`` list in-place. This eliminates the +1 round-trip
        latency of ``load_tool`` for the ~80% of obvious cases.

        Args:
            query: User query text.
            tools: Mutable list of tool schemas (OpenAI format) to extend.

        Returns:
            List of tool IDs that were auto-loaded.
        """
        from .function_calling import ToolSchemaConverter
        from .tools.base import ToolRegistry

        query_lower = query.lower()
        loaded: list[str] = []

        for tool_id, keywords in self._AUTO_LOAD_HINTS.items():
            if not keywords:
                continue
            if not any(kw in query_lower for kw in keywords):
                continue
            # Check if already in tools list
            if any(t.get("function", {}).get("name") == tool_id for t in tools):
                continue
            tool_instance = ToolRegistry.get_tool(
                tool_id, hass=self.hass, config=self.config
            )
            if tool_instance is None:
                continue
            new_schemas = ToolSchemaConverter.to_openai_format([tool_instance])
            tools.extend(new_schemas)
            loaded.append(tool_id)

        return loaded

    async def _get_system_prompt(self, user_id: str) -> str:
        """Build system prompt with identity context and on-demand tool catalog.

        Args:
            user_id: User ID for identity lookup.

        Returns:
            Full system prompt string with identity context if available,
            or onboarding prompt for new users, or base prompt as fallback.
            Includes short descriptions of ON_DEMAND tools when the provider
            supports function calling.
        """
        from .prompts import BASE_SYSTEM_PROMPT

        # Check if identity manager is available
        if not self._rag_manager or not self._rag_manager.identity_manager:
            _LOGGER.debug("Identity manager not available, using BASE_SYSTEM_PROMPT")
            system_prompt = BASE_SYSTEM_PROMPT
        else:
            try:
                identity_manager = self._rag_manager.identity_manager
                identity = await identity_manager.get_identity(user_id)
                system_prompt = identity_manager.build_system_prompt(identity)

                if identity and identity.onboarding_completed:
                    _LOGGER.debug(
                        "Using system prompt with identity context (agent: %s)",
                        identity.agent_name,
                    )
                else:
                    _LOGGER.debug("User not onboarded, using onboarding prompt")

            except Exception as e:
                _LOGGER.warning("Failed to build system prompt with identity: %s", e)
                system_prompt = BASE_SYSTEM_PROMPT

        # Append ON_DEMAND tool catalog when provider supports tools
        if self._provider.supports_tools:
            from .tools import ToolRegistry

            on_demand_desc = ToolRegistry.get_on_demand_descriptions()
            if on_demand_desc:
                system_prompt = system_prompt + "\n\n" + on_demand_desc

        return self._inject_current_time(system_prompt)

    @staticmethod
    def _inject_current_time(prompt: str) -> str:
        """Append current date/time to the system prompt.

        This is critical for scheduling — the agent needs the real current
        time to compute correct cron expressions for 'in 5 minutes' etc.
        """
        from homeassistant.util import dt as dt_util

        now = dt_util.now()
        time_block = (
            f"\n\n[CURRENT TIME]\n"
            f"Now: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} "
            f"(weekday: {now.strftime('%A')}, month: {now.month}, day: {now.day})"
        )
        return prompt + time_block

    # === ENTITY OPERATIONS (delegate to EntityManager) ===

    def get_entity_state(self, entity_id: str) -> dict | None:
        """Get entity state."""
        return self._agent.get_entity_state(entity_id)

    def get_entities_by_domain(self, domain: str) -> list[dict]:
        """Get entities by domain."""
        return self._agent.get_entities_by_domain(domain)

    # === CONTROL OPERATIONS (delegate to ControlManager) ===

    async def call_service(
        self,
        domain: str,
        service: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Call a Home Assistant service."""
        return await self._agent.call_service(domain, service, **kwargs)

    # === CONVERSATION ===

    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self._agent.clear_conversation()
