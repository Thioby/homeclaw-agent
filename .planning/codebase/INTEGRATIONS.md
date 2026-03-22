# External Integrations

**Analysis Date:** 2026-03-20

## APIs & External Services

**LLM Providers (Pluggable):**
- Google Gemini API (REST API Key)
  - SDK/Client: aiohttp with custom conversion layer
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  - Auth: `GEMINI_API_KEY` (API key authentication)
  - Implementation: `custom_components/homeclaw/providers/gemini.py`

- Google Gemini Cloud Code Assist (OAuth)
  - SDK/Client: aiohttp with managed OAuth
  - Endpoint: `https://cloudcode-pa.googleapis.com/v1internal` (Cloud Code Assist API)
  - Auth: OAuth Bearer token (requires onboarding to managed project)
  - Implementation: `custom_components/homeclaw/providers/gemini_oauth.py`
  - Features: Automatic retry on rate limits, project onboarding flow, model fallback chains

- Anthropic Claude API (REST API Key)
  - SDK/Client: aiohttp
  - Endpoint: `https://api.anthropic.com/v1/messages`
  - Auth: `anthropic_token` (API key)
  - Implementation: `custom_components/homeclaw/providers/anthropic.py`

- Anthropic Claude OAuth (Claude Pro/Max)
  - SDK/Client: aiohttp with managed OAuth
  - Endpoint: `https://api.anthropic.com/v1/messages?beta=true` (requires beta header)
  - Auth: OAuth Bearer token (CLI-compatible with claude-cli)
  - Implementation: `custom_components/homeclaw/providers/anthropic_oauth.py`
  - Features: System prompt prefix requirement, interleaved thinking support

- OpenAI GPT API
  - SDK/Client: aiohttp
  - Endpoint: `https://api.openai.com/v1/chat/completions`
  - Auth: `openai_token` (API key)
  - Implementation: `custom_components/homeclaw/providers/openai.py`

- OpenRouter (Multi-provider gateway)
  - SDK/Client: aiohttp (OpenAI-compatible)
  - Endpoint: `https://openrouter.ai/api/v1/chat/completions`
  - Auth: `openrouter_token` (API key)
  - Implementation: `custom_components/homeclaw/providers/openrouter.py`
  - Models: Access to 100+ models from multiple providers

- Groq (Fast LPU inference)
  - SDK/Client: aiohttp (OpenAI-compatible)
  - Endpoint: `https://api.groq.com/openai/v1/chat/completions`
  - Auth: API key
  - Implementation: `custom_components/homeclaw/providers/groq.py`

- z.ai (Zhipu AI)
  - SDK/Client: aiohttp
  - Auth: `zai_token` (API key) + endpoint type configuration
  - Implementation: `custom_components/homeclaw/providers/zai.py`
  - Configurable endpoints (general, vision, search, etc.)

- Alter AI
  - SDK/Client: aiohttp
  - Auth: `alter_token` (API key)
  - Allow custom model specification

- Llama (Meta API)
  - SDK/Client: aiohttp
  - Available via config but not primary focus
  - Configurable model

- Local Models (Ollama, LM Studio, vLLM)
  - SDK/Client: aiohttp
  - Endpoint: Configurable via `api_url` (default: `http://localhost:11434`)
  - Auth: None required
  - Implementation: `custom_components/homeclaw/providers/local.py`

**Chat Channels:**
- Discord Bot (Gateway + REST)
  - Gateway: Discord WebSocket gateway protocol
  - REST: Discord HTTP API for message sending
  - SDK/Client: Custom implementation (aiohttp for HTTP)
  - Auth: `bot_token` or `discord_bot_token`
  - Implementation: `custom_components/homeclaw/channels/discord/`
    - Gateway: `gateway.py` (WebSocket event stream)
    - REST Client: `rest.py` (Message CRUD, typing indicator)
  - Features: DM/group pairing policy, user mapping, rate limiting

**Authentication & Identity**

**OAuth Providers:**
- Google OAuth 2.0 (for Gemini Cloud Code Assist)
  - PKCE flow implementation
  - Token refresh mechanism
  - Implementation: `gemini_oauth.py`, `oauth.py`
  - Redirect: Home Assistant config flow callback

- Anthropic OAuth (for Claude Pro/Max)
  - PKCE flow implementation
  - Claude CLI compatible
  - Token refresh mechanism
  - Implementation: `anthropic_oauth.py`, `oauth.py`

**API Key Management:**
- Sensitive keys stored in config entry data
- Masked in logs (see `_SENSITIVE_KEYS` in `__init__.py`)
- Supported tokens:
  - `llama_token`, `openai_token`, `gemini_token`
  - `openrouter_token`, `anthropic_token`, `zai_token`, `alter_token`

## Data Storage

**Databases:**
- SQLite (embedded)
  - Location: Home Assistant `config/` directory
  - Primary use: Session storage, conversation history, embeddings cache
  - Implementation: `custom_components/homeclaw/rag/sqlite_store.py`
  - Composition:
    - FTS5 indexing for keyword search (`_store_fts.py`)
    - Embedding cache with content-addressed lookup (`_store_cache.py`)
    - Session chunk storage (`_store_sessions.py`)
  - No external database server required

**File Storage:**
- Local filesystem only
  - Uploaded files: `config/homeclaw/uploads/`
  - Auto-cleanup: Files > 7 days deleted on startup
  - Processing: PDF extraction via pypdf library
  - Implementation: `file_processor.py`

**Caching:**
- In-memory: Embedding cache during RAG operations
- SQLite: Persistent embedding blob store with FTS5 text index
- Session cache: Message history loaded on demand from storage

## Monitoring & Observability

**Error Tracking:**
- Native Home Assistant logging (Python logging module)
- Logger: `logging.getLogger(__name__)` pattern
- Implementation: Standard Python logger in each module

**Logs:**
- Directed to Home Assistant logger
- Standard Python logging levels (DEBUG, INFO, WARNING, ERROR)
- Sensitive data masking in logs (credentials, tokens)
- Rate limit and retry diagnostics in Google/Anthropic providers

**Metrics:**
- Home Assistant statistics (built-in conversation stats)
- No external metrics service integration

## CI/CD & Deployment

**Hosting:**
- Home Assistant (supervised, core, or OS)
- Deployment: Custom component directory
- Version: 1.3.1+

**CI Pipeline:**
- Not detected in codebase
- Tests run locally via pytest

**Deployment Configuration:**
- Home Assistant config entry flow
- Single or multiple provider instances supported (one per config entry)
- Lifecycle management: `lifecycle.py` handles subsystem initialization

## Environment Configuration

**Required env vars (via config entry UI):**
- `ai_provider` - Selected provider (gemini, gemini_oauth, anthropic, anthropic_oauth, openai, openrouter, groq, zai, alter, llama, local)
- Provider-specific auth:
  - API key providers: `{provider}_token`
  - Local: `api_url`
  - z.ai: `zai_token` + optional `zai_endpoint`
  - OAuth providers: OAuth tokens managed in config entry

**Optional Configuration:**
- `model` - LLM model ID (provider-specific)
- `rag_enabled` - Enable RAG (default: True)
- `discord_bot_token` - Enable Discord channel
- `dm_policy` - Discord DM handling (pairing, allow, deny)
- Channel configuration: `history_limit`, `max_concurrent`, etc.

**Secrets location:**
- Home Assistant config entry data (encrypted at rest)
- Not in environment variables or .env files
- Sensitive keys logged as redacted

## Webhooks & Callbacks

**Incoming:**
- Discord Gateway: WebSocket connection for message events (no webhook)
- OAuth callbacks: Home Assistant redirect URI for auth code exchange
  - Handled by config_flow reauth steps
  - Path: `/api/homeclaw/oauth_callback` (implicit in HA)

**Outgoing:**
- LLM provider APIs: REST calls for message generation
- Discord REST API: Message send, typing indicators
- OAuth endpoints: Token refresh for Google and Anthropic
- No outbound webhooks initiated by Homeclaw

## Service Integrations

**Home Assistant Native:**
- `conversation` service - Conversation API integration
- `ai_task` service - Task creation/management
- `recorder` - Conversation history recording
- `http` - HTTP platform dependency
- `history` - Entity history access
- `lovelace` - Frontend dashboard integration

**Tool Execution:**
- Web search (via aiohttp + search tools)
- Web fetch (via aiohttp + fetch tools)
- Context7 semantic search (via aiohttp + embeddings)
- Function calling codec for AI tool invocation

## External File Processing

**PDF Processing:**
- Library: pypdf 4.0.0+
- Purpose: Extract text from uploaded PDFs for RAG
- Cleanup: Automatic removal of files > 7 days old
- No external PDF processing service

---

*Integration audit: 2026-03-20*
