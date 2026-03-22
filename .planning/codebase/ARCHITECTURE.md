# Architecture

**Analysis Date:** 2026-03-20

## Pattern Overview

**Overall:** Layered plugin architecture with modular AI agent orchestration

**Key Characteristics:**
- Provider-agnostic AI integration with pluggable LLM backends
- Separation of concerns via specialized component delegation
- Multi-channel support (WebSocket, conversation entity, Discord, etc.)
- Progressive tool activation (CORE vs ON_DEMAND tiers)
- Hybrid RAG system with semantic + keyword search
- Long-term memory with auto-capture and auto-recall

## Layers

**Provider Layer (AI Backends):**
- Purpose: Abstract AI provider implementations (OpenAI, Gemini, Anthropic, etc.)
- Location: `custom_components/homeclaw/providers/`
- Contains: `AIProvider` base class, provider registrations, OAuth handlers
- Depends on: External AI SDKs (openai, google-generativeai, anthropic)
- Used by: HomeclawAgent, QueryProcessor
- Key files: `registry.py` (ProviderRegistry), `gemini_oauth.py`, `_gemini_convert.py`

**Core AI Agent Layer (Query Processing):**
- Purpose: Orchestrate AI interactions, message building, tool calling loops
- Location: `custom_components/homeclaw/core/`
- Contains:
  - `agent.py`: Thin orchestrator delegating to QueryProcessor, ResponseParser, ConversationManager
  - `query_processor.py`: Main entry point for AI queries, sanitization, delegation
  - `context_builder.py`: System prompt assembly, conversation history, message compaction
  - `tool_loop.py`/`stream_loop.py`: Non-streaming and streaming tool call loops
  - `tool_executor.py`: Executes tool schemas against ToolRegistry
  - `function_call_parser.py`: Parses LLM-native function calls
  - `tool_call_codec.py`: Encodes/decodes tool messages, normalizes across providers
  - `compaction.py`: Token-aware message compaction with semantic summarization
  - `token_estimator.py`: Token budget computation
  - `conversation.py`: Conversation history management
  - `response_parser.py`: Parses LLM responses, detects function calls
  - `subagent.py`: Multi-turn agent spawning for subtasks
- Depends on: Providers, ToolRegistry, RagManager, MemoryManager
- Used by: Agent, HomeclawAgent, Conversation entities

**Tool Layer (Function Calling):**
- Purpose: Provide extensible tools for agent use
- Location: `custom_components/homeclaw/tools/`
- Contains:
  - `base.py`: `Tool` ABC, `ToolRegistry` (decorator-based registration), `ToolTier` enum (CORE/ON_DEMAND)
  - Implementations: Home Assistant integration tools, web tools, memory tools, scheduler tools
- Depends on: Home Assistant core, external APIs (websearch, webfetch)
- Used by: ToolExecutor, load_tool meta-tool

**Home Assistant Integration Layer (Managers):**
- Purpose: Encapsulate HA-specific operations
- Location: `custom_components/homeclaw/managers/`
- Contains:
  - `entity_manager.py`: Entity query with per-domain caching and state_changed listeners
  - `registry_manager.py`: Device/area/entity registry queries
  - `control_manager.py`: Service call execution
  - `automation_manager.py`: Automation operations
  - `dashboard_manager.py`: Custom panel lifecycle
- Depends on: Home Assistant core
- Used by: Tools, Agent

**Memory Layer (Long-Term Memory):**
- Purpose: Capture and retrieve user memories across sessions
- Location: `custom_components/homeclaw/memory/`
- Contains:
  - `manager.py`: Facade orchestrating memory operations
  - `memory_store.py`: SQLite persistence for memories
  - `auto_capture.py`: Regex-triggered memory extraction from conversations
  - `identity_store.py`/`identity_manager.py`: User identity (name, preferences)
- Depends on: RagManager (for embeddings), SQLite
- Used by: ContextBuilder (auto-recall), RAG post-conversation handlers

**RAG Layer (Retrieval-Augmented Generation):**
- Purpose: Semantic search over entities, conversations, and memories
- Location: `custom_components/homeclaw/rag/`
- Contains:
  - `query_engine.py`: Hybrid semantic + keyword search, context compression
  - `context_retriever.py`: Retrieves relevant entity context
  - `semantic_learner.py`: Async embedding generation with retry
  - `session_indexer.py`: Indexes completed sessions for knowledge base
  - `lifecycle_manager.py`: RAG system initialization
  - `embeddings.py`: Embedding provider abstraction
  - SQLite store with FTS5 (full-text search) support
- Depends on: Embeddings provider (cached), SQLite
- Used by: ContextBuilder (inject relevant context), Memory system, Conversation handlers

**Session & Storage Layer:**
- Purpose: Persist conversations and user data
- Location: `custom_components/homeclaw/storage.py`
- Contains: `Message`, `Session`, `SessionStorage` classes using HA Store helpers
- Depends on: Home Assistant storage APIs
- Used by: WebSocket handlers, Conversation entity

**Communication Layer (Channels):**
- Purpose: Multi-platform message intake and routing
- Location: `custom_components/homeclaw/channels/`
- Contains:
  - `base.py`: `Channel` ABC, `MessageEnvelope`, `ChannelTarget`
  - `manager.py`: `ChannelManager` (lifecycle)
  - `intake.py`: `MessageIntake` (unified message processing)
  - Implementations: Discord (websocket gateway + REST), extensible for Telegram, etc.
- Depends on: External platform APIs (Discord)
- Used by: WebSocket handlers for non-HA message routing

**WebSocket API Layer:**
- Purpose: Real-time streaming and UI communication
- Location: `custom_components/homeclaw/ws_handlers/`
- Contains:
  - `chat.py`: `ws_send_message` (non-streaming), `ws_send_message_stream` (streaming with events)
  - `sessions.py`: Session management endpoints
  - `rag.py`: RAG (search, memories, identity, stats) endpoints
  - `models.py`: Model configuration endpoints
  - `proactive.py`: Proactive alert endpoints
  - `_common.py`: Shared validation, storage retrieval, errors
- Depends on: HA websocket API, Agent
- Used by: Custom panel frontend, tests

**Compatibility Layer:**
- Purpose: Bridge old monolithic interface to new modular architecture
- Location: `custom_components/homeclaw/agent_compat.py`
- Contains: `HomeclawAgent` wrapper maintaining backward compatibility
- Depends on: All core layers
- Used by: `__init__.py`, conversation.py, lifecycle.py

**Conversation Entity Layer:**
- Purpose: HA Conversation component integration (Assist pipelines, voice)
- Location: `custom_components/homeclaw/conversation.py`
- Contains: `HomeclawConversationEntity` (adapter to HA's conversation protocol)
- Depends on: HomeclawAgent, streaming infrastructure
- Used by: Home Assistant's conversation component

**Proactive System:**
- Purpose: Scheduled alerts and background tasks
- Location: `custom_components/homeclaw/proactive/`
- Contains:
  - `scheduler.py`: Cron-like task scheduling
  - `heartbeat.py`: Regular system health checks
- Depends on: Agent, tools
- Used by: Lifecycle management

**Configuration & Lifecycle:**
- Location: `custom_components/homeclaw/config_flow.py`, `lifecycle.py`
- Contains: Configuration UI flow, integration setup/teardown, all subsystem initialization

## Data Flow

**User Query (WebSocket):**

1. User sends message via custom panel → `ws_send_message_stream` (WebSocket handler)
2. Handler retrieves/creates `SessionStorage` for user
3. Stores message as `Message` object with status="pending"
4. Calls `HomeclawAgent.process_query_stream()` via compatibility layer
5. Agent delegates to `QueryProcessor.process_query_stream()`
6. QueryProcessor:
   - Sanitizes query (removes invisible chars, caps length)
   - Calls `build_messages()` → ContextBuilder assembles messages with:
     - System prompt (with memory auto-recall injection)
     - RAG-retrieved entity context if needed
     - Conversation history (compacted if over token budget)
   - Enters tool calling loop with streaming
7. StreamLoop yields events as events occur:
   - StatusEvent: Starting iteration
   - TextEvent: Streaming text chunks from provider
   - ToolCallEvent: Tool invocation detected
   - ToolResultEvent: Tool execution results
   - CompletionEvent: Conversation finished
8. ToolExecutor executes tools against ToolRegistry:
   - Validates tool exists, not denied
   - Calls tool.execute() with normalized parameters
   - Captures result, truncates if oversized
   - Appends tool_result message to history
9. If load_tool was called, expand_loaded_tools() dynamically adds requested tool schemas
10. Loop continues until max_iterations or no more tool calls
11. Final text accumulated and stored as Message with role="assistant"
12. RAG post-conversation triggers:
    - Semantic learner embeds and indexes session
    - Session indexer updates knowledge base
    - Memory auto-capture extracts "remember this" commands

**Conversation Entity (Assist/Voice):**

1. HA sends message to Conversation component
2. `HomeclawConversationEntity.async_process()` called
3. Retrieves agent from domain data
4. Calls `agent.process_query_stream()` (same flow as above)
5. Adapts provider stream chunks to HA ChatLog delta format via `_transform_provider_stream()`
6. Streams deltas to HA in real time
7. Tool calling handled internally (not exposed to HA)

**Channel Message (Discord/External):**

1. Channel (Discord) receives platform event
2. Converts to `MessageEnvelope` with normalized fields
3. Passes to `MessageIntake.process_message()` or enqueues for rate limiting
4. Intake retrieves/creates session, stores message
5. Calls agent's process_query_stream() with ChannelTarget for routing
6. Agent streams response back to channel
7. Channel sends response via platform API (Discord REST or websocket)

**State Management:**

- **Conversation History:** In-memory during query, persisted to `SessionStorage` after completion
- **Entity Cache:** Per-domain cache in `EntityManager`, invalidated on EVENT_STATE_CHANGED
- **Tool Schemas:** Built at QueryProcessor init, expanded dynamically via load_tool
- **RAG Context:** Computed per-query during ContextBuilder phase
- **Memory Embeddings:** Cached via `CachedEmbeddingProvider` (shared with entity RAG)

## Key Abstractions

**AIProvider:**
- Purpose: Abstract interface to LLM backends
- Examples: `providers/openai.py`, `providers/gemini.py`, `providers/anthropic.py`
- Pattern: Inheritance from `AIProvider` ABC; `supports_tools`, `get_response()`, `get_response_stream()` methods

**Tool:**
- Purpose: Unit of agent capability (function call)
- Examples: `tools/ha_native.py` (get_entities_by_domain), `tools/webfetch.py`, `tools/memory.py`
- Pattern: Inherit from `Tool` ABC; register with `@ToolRegistry.register`; implement `async execute()`
- Tiers: CORE tools always in schema; ON_DEMAND tools loaded via `load_tool`

**Channel:**
- Purpose: External platform integration
- Examples: `channels/discord/__init__.py`
- Pattern: Inherit from `Channel` ABC; implement `async_setup()`, `send_response()`

**FunctionCall:**
- Purpose: Parsed function call from LLM response
- Pattern: Dataclass with `id`, `name`, `arguments` fields

**ToolSchemaConverter:**
- Purpose: Convert Tool metadata to provider-native formats (OpenAI, Anthropic, Gemini)
- Pattern: Static methods for each provider; type mapping dictionaries

**Message/Session:**
- Purpose: Persistent conversation data
- Pattern: Dataclasses stored via HA's Store helper; indexed by user_id and session_id

**AgentEvent:**
- Purpose: Streaming events from QueryProcessor
- Subtypes: StatusEvent, TextEvent, ToolCallEvent, ToolResultEvent, CompletionEvent, ErrorEvent

## Entry Points

**Integration Setup:**
- Location: `custom_components/homeclaw/__init__.py`
- Triggers: HA startup, config entry creation
- Responsibilities:
  - Parse config (provider, model, API keys)
  - Create provider via ProviderRegistry
  - Instantiate HomeclawAgent
  - Initialize MemoryManager, RagManager, ChannelManager
  - Register WebSocket handlers
  - Set up conversation entity
  - Register services (homeclaw.ask, etc.)

**WebSocket Entry Point (Chat):**
- Location: `ws_handlers/chat.py` → `ws_send_message_stream`
- Entry: `{"type": "homeclaw/send_message_stream", "session_id": "...", "message": "..."}`
- Flow: Message → SessionStorage → Agent.process_query_stream() → event stream

**Conversation Entity Entry Point:**
- Location: `conversation.py` → `HomeclawConversationEntity.async_process()`
- Entry: HA's `conversation.process` service
- Flow: User query → Agent.process_query_stream() → ChatLog deltas

**Service Entry Point:**
- Location: `services.py`
- Services: `homeclaw.ask` (query), `homeclaw.get_config` (read settings)
- Flow: Call agent.process_query(), return final text

## Error Handling

**Strategy:** Multi-level fallback with graceful degradation

**Patterns:**

1. **Provider Errors:**
   - Retry with exponential backoff via provider's `get_response()` method
   - Fallback: Non-streaming mode if streaming fails
   - Fallback: Revert tool calling loop to non-streaming if stream errors

2. **Tool Execution Errors:**
   - Catch exceptions during `tool.execute()`
   - Return error message to LLM as tool_result with error flag
   - Track repeated calls via `call_history_hashes` to break infinite loops
   - Deny tool if denied_tools frozenset includes it

3. **Context Overflow:**
   - Estimate tokens via `estimate_messages_tokens()`
   - If over budget, trigger `compact_messages()` (semantic summarization)
   - Fallback: `truncation_fallback()` if compaction fails
   - Recompact after tool results if needed

4. **Storage Errors:**
   - SessionStorage handles HA Store errors
   - Return error responses via WebSocket (ERR_STORAGE_ERROR)
   - Log and skip non-critical operations (RAG indexing, memory capture)

5. **Streaming Errors:**
   - Catch exceptions in stream loop
   - Yield ErrorEvent with error details
   - Client disconnection handled gracefully

## Cross-Cutting Concerns

**Logging:**
- Per-module loggers via `logging.getLogger(__name__)`
- Structured logs in agents, tools, managers
- Debug levels for token counting, tool execution

**Validation:**
- Query length capping in QueryProcessor
- Session ID and message format validation in ws_handlers
- Tool parameter validation via ToolParameter schemas
- Role validation in Message.__post_init__()

**Authentication:**
- OAuth flows in `providers/gemini_oauth.py` for third-party providers
- HA user_id resolution in WebSocket handlers
- User isolation in SessionStorage (per-user access)

**Rate Limiting:**
- Per-user rate limiting in Channel base class
- Provider-level quotas (Gemini 429 backoff)
- WebSocket message queue depth monitoring

**Security:**
- Tool denial via `denied_tools` frozenset
- load_tool validation: only ON_DEMAND, enabled, not denied
- Shell command execution guards in `tools/shell_security.py`
- Sensitive key masking in logs (_SENSITIVE_KEYS set)

---

*Architecture analysis: 2026-03-20*
