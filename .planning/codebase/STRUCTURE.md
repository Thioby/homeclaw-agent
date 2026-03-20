# Codebase Structure

**Analysis Date:** 2026-03-20

## Directory Layout

```
ai_agent_ha/
├── custom_components/homeclaw/     # Main integration (HA custom component)
│   ├── __init__.py                 # Integration setup, config entry creation
│   ├── agent_compat.py             # HomeclawAgent wrapper (backward compat)
│   ├── conversation.py             # HA Conversation entity integration
│   ├── services.py                 # Service handlers (homeclaw.ask, etc.)
│   ├── websocket_api.py            # Facade re-exporting ws_handlers
│   ├── storage.py                  # Message, Session, SessionStorage classes
│   ├── file_processor.py           # File/attachment processing
│   ├── lifecycle.py                # Subsystem initialization/teardown
│   ├── models.py                   # Models config CRUD + cache
│   ├── prompts.py                  # System prompts, prompt templates
│   ├── function_calling.py         # FunctionCall, ToolSchemaConverter
│   ├── config_flow.py              # Config UI flow (UI setup wizard)
│   ├── const.py                    # Domain constants, provider lists
│   │
│   ├── core/                       # AI agent query processing
│   │   ├── agent.py                # Slim orchestrator (QueryProcessor delegation)
│   │   ├── query_processor.py      # Main query entry point
│   │   ├── context_builder.py      # Message building, compaction
│   │   ├── conversation.py         # Conversation history manager
│   │   ├── tool_loop.py            # Non-streaming tool call loop
│   │   ├── stream_loop.py          # Streaming tool call loop
│   │   ├── tool_executor.py        # Tool execution, result collection
│   │   ├── tool_call_codec.py      # Tool message encoding/decoding
│   │   ├── function_call_parser.py # Parse LLM function calls
│   │   ├── response_parser.py      # Parse LLM responses
│   │   ├── compaction.py           # Message compaction + summarization
│   │   ├── token_estimator.py      # Token budget computation
│   │   ├── subagent.py             # Multi-turn subagent spawning
│   │   ├── events.py               # AgentEvent types (StatusEvent, etc.)
│   │   └── __init__.py
│   │
│   ├── providers/                  # AI provider implementations
│   │   ├── registry.py             # AIProvider ABC, ProviderRegistry
│   │   ├── openai.py               # OpenAI provider
│   │   ├── gemini.py               # Gemini provider
│   │   ├── anthropic.py            # Anthropic provider
│   │   ├── openrouter.py           # OpenRouter provider
│   │   ├── gemini_oauth.py         # Gemini OAuth flow
│   │   ├── _gemini_convert.py      # Gemini-specific conversions
│   │   ├── _gemini_retry.py        # Gemini retry logic
│   │   ├── _gemini_constants.py    # Gemini constants
│   │   ├── zai.py                  # (Experimental) AI provider
│   │   └── __init__.py
│   │
│   ├── tools/                      # Tool implementations
│   │   ├── base.py                 # Tool ABC, ToolRegistry, ToolTier
│   │   ├── ha_native.py            # HA-native tools (get_entities, call_service)
│   │   ├── load_tool.py            # load_tool meta-tool
│   │   ├── memory.py               # Memory tools (store, recall)
│   │   ├── webfetch.py             # fetch_url tool
│   │   ├── websearch.py            # web_search tool
│   │   ├── shell_execute.py        # Shell execution tool
│   │   ├── shell_security.py       # Shell security validators
│   │   ├── scheduler.py            # Scheduling tools
│   │   ├── subagent.py             # Subagent spawning tool
│   │   ├── identity.py             # User identity tools
│   │   ├── integration_manager.py  # Integration tools
│   │   ├── channel_status.py       # Channel status tools
│   │   ├── context7.py             # Context helper tool
│   │   └── __init__.py
│   │
│   ├── managers/                   # HA integration managers
│   │   ├── entity_manager.py       # Entity queries, domain caching
│   │   ├── registry_manager.py     # Device/area/entity registry
│   │   ├── control_manager.py      # Service call execution
│   │   ├── automation_manager.py   # Automation operations
│   │   ├── dashboard_manager.py    # Custom panel lifecycle
│   │   └── __init__.py
│   │
│   ├── memory/                     # Long-term memory system
│   │   ├── manager.py              # MemoryManager facade
│   │   ├── memory_store.py         # SQLite memory persistence
│   │   ├── auto_capture.py         # Regex-triggered memory extraction
│   │   ├── identity_store.py       # User identity storage
│   │   ├── identity_manager.py     # Identity CRUD operations
│   │   └── __init__.py
│   │
│   ├── rag/                        # Retrieval-Augmented Generation
│   │   ├── query_engine.py         # Hybrid search engine
│   │   ├── context_retriever.py    # Entity context retrieval
│   │   ├── semantic_learner.py     # Embedding + indexing
│   │   ├── session_indexer.py      # Session knowledge base indexing
│   │   ├── lifecycle_manager.py    # RAG initialization
│   │   ├── embeddings.py           # Embedding provider interface
│   │   ├── sqlite_store.py         # SQLite persistence
│   │   ├── _session_context.py     # Session context helpers
│   │   ├── _store_fts.py           # Full-text search wrappers
│   │   ├── _store_utils.py         # Storage utilities
│   │   ├── _temporal.py            # Temporal search helpers
│   │   ├── event_handlers.py       # HA event monitoring
│   │   └── __init__.py
│   │
│   ├── channels/                   # Multi-platform message intake
│   │   ├── base.py                 # Channel ABC, ChannelTarget, MessageEnvelope
│   │   ├── manager.py              # ChannelManager lifecycle
│   │   ├── intake.py               # MessageIntake unified processor
│   │   ├── config.py               # Channel configuration helpers
│   │   ├── discord/                # Discord channel implementation
│   │   │   ├── __init__.py         # DiscordChannel class
│   │   │   ├── gateway.py          # Websocket gateway connection
│   │   │   ├── rest.py             # REST API client
│   │   │   ├── pairing.py          # Device pairing flow
│   │   │   └── helpers.py          # Helper utilities
│   │   └── __init__.py
│   │
│   ├── ws_handlers/                # WebSocket API handlers
│   │   ├── _common.py              # Shared validation, storage, errors
│   │   ├── chat.py                 # send_message, send_message_stream
│   │   ├── sessions.py             # Session CRUD operations
│   │   ├── rag.py                  # RAG endpoints (search, memories)
│   │   ├── models.py               # Model config endpoints
│   │   ├── proactive.py            # Proactive alert endpoints
│   │   ├── __init__.py             # Handler registration
│   │   └── helpers.py              # Shared helpers
│   │
│   ├── proactive/                  # Scheduled alerts & tasks
│   │   ├── scheduler.py            # Cron-like task scheduler
│   │   ├── heartbeat.py            # Health check intervals
│   │   └── __init__.py
│   │
│   ├── utils/                      # Utility modules
│   │   ├── yaml_io.py              # YAML serialization
│   │   ├── yaml_sections.py        # YAML section helpers
│   │   ├── yaml_tags.py            # YAML tag definitions
│   │   ├── yaml_writer.py          # YAML writer
│   │   └── __init__.py
│   │
│   ├── frontend/                   # Custom panel (TypeScript/Vue)
│   │   ├── src/                    # Source files
│   │   ├── dist/                   # Compiled assets
│   │   ├── public/                 # Static assets
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── translations/               # i18n translations
│   └── manifest.json               # Integration manifest
│
├── tests/                          # Test suite
│   ├── fixtures/                   # Test fixtures and factories
│   ├── test_core/                  # Query processor tests
│   ├── test_providers/             # Provider tests
│   ├── test_tools/                 # Tool tests
│   ├── test_managers/              # Manager tests
│   ├── test_memory/                # Memory system tests
│   ├── test_channels/              # Channel tests
│   ├── test_rag/                   # RAG system tests
│   ├── test_homeclaw/              # Integration tests
│   ├── test_proactive/             # Proactive system tests
│   └── conftest.py                 # Pytest configuration
│
├── docs/                           # Project documentation
│   ├── AGENTS.md                   # Full system overview
│   ├── ANALYSIS-AGENT-LOOP.md      # Agent loop detailed analysis
│   ├── CHANGELOG.md                # Change history
│   └── PLAN-*.md                   # Technical plans
│
├── icons/                          # Icon assets
├── deploy.sh                       # Deployment script
├── pytest.ini                      # Pytest configuration
├── AGENTS.md                       # System documentation root
├── CHANGELOG.md                    # Release notes
└── manifest.json                   # (in custom_components/homeclaw/)
```

## Directory Purposes

**`custom_components/homeclaw/`:**
- Purpose: Home Assistant custom component (integration)
- Contains: All Python source code for the integration
- Key files: `__init__.py` (entry point), `config_flow.py` (UI)

**`custom_components/homeclaw/core/`:**
- Purpose: AI agent query processing and orchestration
- Contains: Message building, tool calling loops, streaming coordination
- Key files: `agent.py` (slim orchestrator), `query_processor.py` (main entry)

**`custom_components/homeclaw/providers/`:**
- Purpose: AI provider implementations and registry
- Contains: Provider classes (OpenAI, Gemini, Anthropic), conversion utilities, OAuth
- Key files: `registry.py` (provider registry pattern), provider implementations

**`custom_components/homeclaw/tools/`:**
- Purpose: Tool/function implementations for agent use
- Contains: Tool classes, tool registry, tool tier definitions
- Key files: `base.py` (Tool ABC and registry), individual tool files

**`custom_components/homeclaw/managers/`:**
- Purpose: Encapsulated Home Assistant operations
- Contains: Entity caching, service calls, automation management
- Key files: `entity_manager.py` (with per-domain cache), other managers

**`custom_components/homeclaw/memory/`:**
- Purpose: Long-term memory persistence and retrieval
- Contains: Memory store, auto-capture rules, identity tracking
- Key files: `manager.py` (facade), `memory_store.py` (SQLite)

**`custom_components/homeclaw/rag/`:**
- Purpose: Retrieval-augmented generation (semantic + keyword search)
- Contains: Query engine, embeddings, session indexing
- Key files: `query_engine.py` (hybrid search), `lifecycle_manager.py` (init)

**`custom_components/homeclaw/channels/`:**
- Purpose: External platform integrations (Discord, Telegram, etc.)
- Contains: Channel base classes, platform implementations, message intake
- Key files: `base.py` (Channel ABC), `intake.py` (unified processor)

**`custom_components/homeclaw/ws_handlers/`:**
- Purpose: WebSocket API endpoints for custom panel
- Contains: Chat handlers (streaming), session management, RAG API, config endpoints
- Key files: `chat.py` (send_message, send_message_stream), `_common.py` (shared validators)

**`custom_components/homeclaw/proactive/`:**
- Purpose: Scheduled alerts and background tasks
- Contains: Task scheduler, heartbeat monitoring
- Key files: `scheduler.py` (cron tasks), `heartbeat.py` (health checks)

**`custom_components/homeclaw/utils/`:**
- Purpose: Shared utility functions
- Contains: YAML I/O, text processing helpers
- Key files: `yaml_io.py` (YAML serialization)

**`custom_components/homeclaw/frontend/`:**
- Purpose: Custom panel UI (TypeScript/Vue)
- Contains: Vue components, TypeScript source, compiled assets
- Key files: `src/` (source), `package.json` (dependencies)

**`tests/`:**
- Purpose: Test suite (pytest)
- Contains: Unit tests, integration tests, fixtures
- Key files: `conftest.py` (shared fixtures), test_core/ (agent tests)

**`docs/`:**
- Purpose: Project documentation
- Contains: Architecture guides, technical plans, changelog
- Key files: `AGENTS.md` (system overview), implementation plans

## Key File Locations

**Entry Points:**
- `custom_components/homeclaw/__init__.py`: HA integration setup (async_setup_entry)
- `custom_components/homeclaw/config_flow.py`: Configuration UI flow
- `custom_components/homeclaw/conversation.py`: HA Conversation entity
- `custom_components/homeclaw/ws_handlers/__init__.py`: WebSocket handler registration

**Configuration:**
- `custom_components/homeclaw/const.py`: Domain, provider lists, constants
- `custom_components/homeclaw/models.py`: Model configuration CRUD
- `custom_components/homeclaw/models_config.json`: Model list (JSON file)

**Core Logic:**
- `custom_components/homeclaw/core/agent.py`: Agent orchestrator
- `custom_components/homeclaw/core/query_processor.py`: Query handling
- `custom_components/homeclaw/core/context_builder.py`: Message assembly + compaction
- `custom_components/homeclaw/core/stream_loop.py`: Streaming tool loop
- `custom_components/homeclaw/providers/registry.py`: Provider abstraction

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures
- `tests/fixtures/`: Factory classes for test data
- `tests/test_core/`: Query processor, context builder tests
- `tests/test_providers/`: Provider implementation tests

## Naming Conventions

**Files:**
- `.py` files: `snake_case`
  - Examples: `entity_manager.py`, `query_processor.py`, `websocket_api.py`
- Underscore prefix `_` for private/internal modules (not part of public API)
  - Examples: `_gemini_convert.py`, `_session_context.py`, `_store_fts.py`
- Test files: `test_<module>.py` or `test_<feature>.py`
  - Examples: `test_function_call_parser.py`, `test_gemini_oauth.py`

**Classes:**
- PascalCase for all classes
  - Examples: `Agent`, `QueryProcessor`, `EntityManager`, `HomeclawAgent`
- Abstract base classes (ABC): prefix with capital letter, inherit ABC
  - Examples: `Tool`, `Channel`, `AIProvider`
- Dataclasses: PascalCase with `@dataclass` decorator
  - Examples: `Message`, `Session`, `ToolParameter`, `FunctionCall`

**Functions/Methods:**
- `snake_case` for module-level functions and methods
  - Examples: `build_messages()`, `execute_tool_calls()`, `async_setup()`
- Private functions: `_snake_case` prefix
  - Examples: `_sanitize_query()`, `_rag_post_conversation()`, `_ensure_initialized()`
- Async functions: `async_<action>()` naming pattern
  - Examples: `async_initialize()`, `async_setup()`, `async_process_message()`

**Variables:**
- `snake_case` for all variables
  - Examples: `max_iterations`, `entity_manager`, `current_iteration`
- Constants: `UPPER_SNAKE_CASE`
  - Examples: `MAX_TOOL_RESULT_CHARS`, `DEFAULT_CONTEXT_WINDOW`, `STORAGE_VERSION`
- Private attributes: `_snake_case` prefix (convention, not enforced)
  - Examples: `self._domain_cache`, `self._query_processor`, `self._initialized`

**Type Names:**
- PascalCase for types (TypeVars, Aliases)
  - Examples: `ToolT`, `ProviderT`
- Enum members: `UPPER_SNAKE_CASE`
  - Examples: `ToolTier.CORE`, `ToolTier.ON_DEMAND`

## Where to Add New Code

**New Feature (Agent Capability):**
- Primary code: Create tool in `custom_components/homeclaw/tools/my_feature.py`
  - Inherit from `Tool` base class
  - Register with `@ToolRegistry.register` decorator
  - Implement `async execute(**params) -> ToolResult`
- System prompt: Add to `custom_components/homeclaw/prompts.py`
- Tests: `tests/test_tools/test_my_feature.py`

**New Component/Module (Business Logic):**
- Implementation: Create in appropriate subdirectory
  - Tools: `custom_components/homeclaw/tools/`
  - Managers: `custom_components/homeclaw/managers/`
  - RAG: `custom_components/homeclaw/rag/`
  - Memory: `custom_components/homeclaw/memory/`
- Public API: Document in module docstring
- Private helpers: Use `_function_name()` prefix
- Tests: Mirror structure in `tests/`

**Utilities/Helpers:**
- Shared helpers: `custom_components/homeclaw/utils/`
- Tool-specific utilities: Co-locate with tool (same file or tool_utils.py)
- Provider-specific utilities: `custom_components/homeclaw/providers/_module_name.py` (private convention)

**WebSocket Handler (New API Endpoint):**
- Location: `custom_components/homeclaw/ws_handlers/`
- Naming: `ws_<action>()` (e.g., `ws_get_status()`, `ws_update_config()`)
- Pattern: Use `_get_storage()`, `_get_user_id()`, validation helpers from `_common.py`
- Registration: Add to `async_register_websocket_commands()` in `__init__.py`

**Provider Implementation (New LLM):**
- Location: `custom_components/homeclaw/providers/`
- Naming: `my_provider.py`
- Pattern: Inherit from `AIProvider`, implement required abstract methods
- Registration: `@ProviderRegistry.register("provider_key")` decorator
- Models: List in `custom_components/homeclaw/models_config.json`

## Special Directories

**`custom_components/homeclaw/frontend/`:**
- Purpose: Custom panel UI
- Generated: `dist/` is compiled from `src/` (run `npm run build`)
- Committed: Only `src/` and `dist/` are committed; `node_modules/` is ignored

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Generated: These are generated by GSD mapping agents
- Committed: Yes, for reference during planning phases

**`htmlcov/`:**
- Purpose: Test coverage reports
- Generated: Created by pytest-cov
- Committed: No (in .gitignore)

**`.pytest_cache/` and `.ruff_cache/`:**
- Purpose: Tool caches (pytest, linting)
- Generated: Created by pytest and ruff
- Committed: No (in .gitignore)

## Import Patterns

**Internal imports (from within integration):**
```python
# Absolute imports using package structure
from custom_components.homeclaw.core.agent import Agent
from custom_components.homeclaw.providers.registry import ProviderRegistry
from custom_components.homeclaw.tools.base import ToolRegistry

# Relative imports within same package (cleaner for most code)
from .core.agent import Agent
from .tools.base import ToolRegistry

# TYPE_CHECKING for circular dependency breaking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
```

**External imports:**
```python
# Home Assistant core
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import websocket_api

# Third-party AI SDKs
from openai import AsyncOpenAI
import anthropic

# Standard library
import json
import logging
from dataclasses import dataclass
```

---

*Structure analysis: 2026-03-20*
