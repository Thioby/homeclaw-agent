# Codebase Concerns

**Analysis Date:** 2026-03-20

## Tech Debt

**Gemini OAuth 429 Rate Limiting — Non-stop rate limit errors:**
- Issue: HomeClaw receives continuous 429 responses from `cloudcode-pa.googleapis.com` while gemini-cli does not. Root causes: missing SSE streaming format, new aiohttp session per request (no connection pooling), fake User-Agent headers, missing per-request IDs, weak retry logic, and unstructured error parsing.
- Files: `custom_components/homeclaw/providers/gemini_oauth.py` (1081 lines), `custom_components/homeclaw/providers/_gemini_retry.py`, `custom_components/homeclaw/providers/_gemini_constants.py`
- Impact: Every Gemini query faces exponential backoff and repeated retries, adding 20-40 seconds latency per query. Production deployments with heavy usage become unusable.
- Fix approach: **6-fix implementation plan in `/docs/PLAN-gemini-oauth-429-fix.md`** prioritizes: (1) Add `alt=sse` to streaming URL, (2) Reuse aiohttp.ClientSession with TCPConnector, (3) Fix User-Agent and remove fake headers, (4) Add user_prompt_id per request, (5) Implement dual-level retry (transport + app-level), (6) Parse structured Google API errors (RetryInfo.retryDelay, ErrorInfo.reason).

**Gemini thought_signature 400 errors on thinking models:**
- Issue: Gemini 2.5/3 thinking models require `thoughtSignature` at the Part level (sibling of `functionCall`), but HomeClaw extracts/places it at wrong levels (inside functionCall or missing entirely). Causes "missing thoughtSignature" 400 errors after tool calls in multi-turn flows.
- Files: `custom_components/homeclaw/providers/_gemini_convert.py` (637 lines, fixes 1/3/4/5), `custom_components/homeclaw/core/tool_call_codec.py` (fix 2)
- Impact: Multi-turn conversations with tool calls fail on 2nd+ tool invocation. Thinking models (highest quality) are effectively broken for agent use.
- Fix approach: **5-fix plan in `/docs/fix-thought-signature-plan.md`**: (1) Extract thoughtSignature from Part level in `process_gemini_chunk`, (2) Extract from parsed_content level in `tool_call_codec.py`, (3) Place at Part level (sibling) in `convert_messages`, (4) Add synthetic `ensure_thought_signatures()` for fallback, (5) Filter `thought` parts in chunk processing.

**Gemini session reuse already fixed — but not yet deployed:**
- Issue: Session pooling was missing (each request created new aiohttp.ClientSession). Now implemented at lines 90, 96-115 in `gemini_oauth.py`.
- Files: `custom_components/homeclaw/providers/gemini_oauth.py` (lines 90, 96-115, 178, 224, 743, 922)
- Impact: **MITIGATED** — session pooling code exists but must be tested in actual HA runtime.
- Verification needed: Deploy and monitor that 429 frequency drops after TCP connection reuse kicks in.

## Known Bugs

**Discord pairing prompt spam after successful pairing:**
- Symptoms: Bot still sends "Discord pairing required... confirm code" even after user has been successfully paired.
- Files: `custom_components/homeclaw/channels/discord/__init__.py` (594 lines)
- Trigger: User pairs once → reconnects → sees pairing prompt again despite valid mapping.
- Workaround: None. Must re-pair or bypass via config edit.
- Root cause: Likely stale runtime config or pairing gate logic not checking persisted user_mapping correctly. Listed in `/docs/BUGS-discord-followup.md` as priority fix #3.

**Discord messages processed twice in some cases:**
- Symptoms: Same `MESSAGE_CREATE id=...` appears multiple times in logs, triggers duplicate actions (duplicate pairing prompts, duplicate side effects).
- Files: `custom_components/homeclaw/channels/discord/__init__.py`
- Trigger: Unclear — intermittent on reconnect or gateway restart scenarios.
- Workaround: None. Requires HA runtime verification with detailed logging.
- Notes: Message-id masking was removed and gateway sequence dedup added, but root cause needs verification in actual HA runtime (not reproducible in unit tests).

**Discord provider selection ignores user preferences:**
- Symptoms: Discord chat uses first available provider instead of `default_provider` from user preferences.
- Files: `custom_components/homeclaw/channels/discord/__init__.py` (method `_default_provider()` around line 466)
- Impact: Wrong model/provider used, inconsistent with web panel behavior.
- Root cause: `DiscordChannel._default_provider()` fallback logic doesn't consult user preferences before selecting.
- Fix: Fetch user preferences and validate default_provider exists; fall back to first provider only if missing.

**Discord mixed behavior — pairing text + normal LLM answer in same flow:**
- Symptoms: Bot sends both pairing prompt and regular answer for same user message in quick succession.
- Files: `custom_components/homeclaw/channels/discord/__init__.py`
- Impact: Confusing UX, suggests split decision path or concurrent consumers.
- Root cause: Likely race condition between pairing check and normal query processing, or async task ordering issue.
- Notes: Listed in `/docs/BUGS-discord-followup.md` as priority fix #4.

## Security Considerations

**Shell command execution requires rate limiting and validation:**
- Risk: `shell_execute` tool can be abused for DOS (fork bombs, infinite loops) or unintended system manipulation.
- Files: `custom_components/homeclaw/tools/shell_execute.py` (MAX_RATE_PER_MINUTE=10, MAX_OUTPUT_BYTES=65536, MAX_TIMEOUT=120)
- Current mitigation: Rate limiting (10 cmds/min), output size cap (64 KB), timeout (5-120s range), command filtering in `shell_security.py`.
- Recommendations: (1) Add per-user rate limits (aggregate across sessions), (2) Log all executions with user context, (3) Consider allowlist-based restrictions for production deployments, (4) Add audit trail to storage.

**OAuth tokens stored in config entries (encrypted by HA):**
- Risk: If config entry encryption key is compromised, tokens leak. If Home Assistant instance is physically accessed, tokens could be extracted.
- Files: `custom_components/homeclaw/__init__.py`, `custom_components/homeclaw/config_flow.py` (OAuth token storage at lines 872+)
- Current mitigation: HA encrypts config entry data at rest.
- Recommendations: (1) Implement token rotation strategy (refresh tokens should be short-lived), (2) Add audit logging for token usage, (3) Document that config entry encryption depends on HA instance security, (4) Consider implementing token revocation endpoint for cleanup on unload.

**RAG content could expose sensitive state data in embeddings:**
- Risk: Entity states (temperatures, door locks, cameras) are indexed in embeddings and persisted to SQLite. If database is stolen, sensitive information is recoverable.
- Files: `custom_components/homeclaw/rag/sqlite_store.py` (704 lines), `custom_components/homeclaw/rag/optimizer.py` (925 lines)
- Current mitigation: `optimizer.py` has "CRITICAL RULE #1" to remove entity state data before indexing (lines 1-50).
- Recommendations: (1) Audit optimizer rules to ensure state removal is exhaustive, (2) Consider encrypting SQLite database at rest, (3) Add data purge on component unload, (4) Log all RAG index operations.

## Performance Bottlenecks

**Compaction triggers on every message due to historic bugs (now fixed):**
- Problem: Prior to fixes in `BUGS-compaction-persistence.md`, compaction ran on EVERY message due to (1) WebSocket handlers not persisting compaction, (2) `keep_last=24` misaligned with `MIN_RECENT_MESSAGES=16`, (3) orphaned tool calls causing re-compaction.
- Files: `custom_components/homeclaw/ws_handlers/chat.py` (776 lines), `custom_components/homeclaw/core/compaction.py` (MAX_HISTORY_TURNS=12, MIN_RECENT_MESSAGES=16)
- Impact: Each message = ~28 seconds of LLM overhead (summarization).
- Status: **FIXED** in recent commits. Bugs 1-3 from `/docs/BUGS-compaction-persistence.md` are resolved.
- Verification: Monitor logs for "Compaction triggered" frequency. Should occur ~once per session (when >12 turns), not every turn.

**Large files with high cyclomatic complexity:**
- Problem: Multiple modules exceed 700 lines. Largest: `ha_native.py` (1357 lines), `gemini_oauth.py` (1081 lines), `optimizer.py` (925 lines).
- Files: `custom_components/homeclaw/tools/ha_native.py` (1357), `custom_components/homeclaw/providers/gemini_oauth.py` (1081), `custom_components/homeclaw/rag/optimizer.py` (925), `custom_components/homeclaw/config_flow.py` (872)
- Impact: Harder to test, higher bug density, slower to navigate.
- Improvement path: (1) Break `ha_native.py` into tool classes per domain (lights, switches, etc.), (2) Extract Gemini retry logic into separate module (already partially done), (3) Consider tool factory pattern for dynamic tool registration.

**RAG query optimization missing indices:**
- Problem: `sqlite_store.py` performs full-table scans on semantic searches. No indices on `content_type`, `session_id`, or embedding distance.
- Files: `custom_components/homeclaw/rag/sqlite_store.py` (704 lines)
- Impact: RAG queries slow on large sessions (1000+ messages).
- Improvement path: (1) Add index on `(session_id, content_type)`, (2) Cache recent embeddings in memory, (3) Implement approximate nearest neighbor search (FAISS or similar) instead of exact euclidean distance.

**Proactive scheduler runs synchronously for all automations:**
- Problem: `proactive/scheduler.py` iterates over all scheduled tasks sequentially. No parallelization.
- Files: `custom_components/homeclaw/proactive/scheduler.py` (690 lines)
- Impact: If N automations are scheduled, latency = sum(execution_times). Bottleneck for 50+ automations.
- Improvement path: (1) Use `asyncio.gather()` for task execution, (2) Implement task queue with worker pool, (3) Add per-task timeout to prevent one slow task blocking others.

## Fragile Areas

**FunctionCallParser — multi-provider format detection is brittle:**
- Files: `custom_components/homeclaw/core/function_call_parser.py`
- Why fragile: Tries strategies in order (OpenAI → Gemini → Anthropic). Storage layer produces hybrid JSON with BOTH `"tool_calls"` (canonical) AND `"tool_use"` (Anthropic-specific), confusing detection.
- Safe modification: (1) Add provider context to parser (know which provider called which format), (2) Validate format before returning (check that returned format is internally consistent), (3) Add comprehensive unit tests for cross-provider round-trips.
- Test coverage: 5 new tests added in `test_function_call_parser.py` for Bug 3 fix, but missing cross-provider scenarios.

**WebSocket chat handlers — concurrent message processing:**
- Files: `custom_components/homeclaw/ws_handlers/chat.py` (776 lines)
- Why fragile: Multiple coroutines can process same session concurrently. No locking around message append/compaction. Discord bug #2 (duplicate processing) may be related.
- Safe modification: (1) Add session-level lock for message operations, (2) Use asyncio.Lock around compaction, (3) Add dedup by message UUID before processing.
- Test coverage: Limited concurrency tests. Add stress tests with rapid-fire messages.

**Memory manager with eventual consistency:**
- Files: `custom_components/homeclaw/memory/manager.py` (604 lines)
- Why fragile: Semantic memory (embeddings) are computed asynchronously. If query happens before embeddings are ready, memories won't be found.
- Safe modification: (1) Add `pending_memories` queue, (2) Check queue during search, (3) Implement linearization point (wait for embeddings before returning search results).
- Test coverage: No tests for race conditions between insert and search.

**Storage compaction with concurrent writes:**
- Files: `custom_components/homeclaw/storage.py` (712 lines)
- Why fragile: `compact_session_messages()` reads full session, rebuilds, and writes. If two requests compact simultaneously, second write overwrites first's changes.
- Safe modification: (1) Add write lock for compaction, (2) Implement ACID transaction if using SQL backend, (3) Add CRC/version check before compaction commit.
- Test coverage: Tests use isolated sessions, but production could have race condition.

## Scaling Limits

**SQLite backend not suitable for 1000+ concurrent sessions:**
- Current capacity: ~100 active sessions (estimated from PRAGMA page_size=4096).
- Limit: SQLite locks entire database during writes. 10+ concurrent writes → heavy contention.
- Scaling path: (1) Implement connection pooling with WAL mode, (2) Consider PostgreSQL backend for production (with async driver), (3) Add sharding by session_id to distribute load.
- Impact: If user base grows beyond ~100 concurrent users, persistence layer becomes bottleneck.

**Memory store (in-process dict) unbounded growth:**
- Current capacity: All memories (semantic + factual) live in `self._memories` dict. No eviction policy.
- Limit: ~100 active sessions × 500 memories/session = 50K memories. At 1KB each = 50 MB RAM. Scales linearly.
- Scaling path: (1) Implement LRU eviction by recency, (2) Move to Redis for multi-process sharing, (3) Add memory TTL (delete old memories after 30 days).
- Impact: Long-running HA instances (6+ months) will accumulate unbounded memories.

**Compaction summary generation synchronous:**
- Current capacity: 1 compaction takes ~15-20 seconds (LLM call). Max ~3 concurrent compactions per instance.
- Limit: If 10+ sessions need compaction simultaneously, LLM queue grows → linear slowdown.
- Scaling path: (1) Queue compactions with priority (keep recent active sessions fresh), (2) Cache similar summaries (reuse across sessions), (3) Offload to background worker pool.
- Impact: Burst load (50+ new users starting conversations) could starve normal queries.

**RAG embeddings computed synchronously in query path:**
- Current capacity: Embedding computation (sentence-transformers) takes ~200-500ms per query.
- Limit: If user types fast, next query starts before embeddings finish → all queries stall.
- Scaling path: (1) Pre-compute embeddings asynchronously on message arrival, (2) Cache embeddings with TTL, (3) Use approximate nearest neighbor search (FAISS) for O(log N) instead of O(N).
- Impact: High-frequency users (> 1 query/sec) will experience degraded RAG quality or timeouts.

## Dependencies at Risk

**aiohttp ClientSession pooling newly added — not yet battle-tested:**
- Risk: Session pooling in `gemini_oauth.py:90-115` is new code. Connector settings (limit=10, keepalive_timeout=30) may not be optimal for production load.
- Impact: If settings are wrong, connections leak or socket exhaustion occurs.
- Migration plan: (1) Add monitoring for active connections and pool size, (2) Load test with 100+ concurrent requests, (3) Consider exposing settings as config parameters.

**sentence-transformers embeddings model — large download on first use:**
- Risk: Model auto-downloads (~1.6 GB) on first call. If internet drops, embeddings fail silently.
- Impact: RAG subsystem silently fails on first query if model cache is cold and internet is unreliable.
- Migration plan: (1) Add pre-download step in setup (with progress), (2) Cache model locally in config directory, (3) Graceful fallback to text-only search if embeddings unavailable.

**Google Cloud Code Assist API — undocumented streaming format:**
- Risk: `alt=sse` streaming format is not officially documented. Implementation depends on reverse-engineering from gemini-cli.
- Impact: If Google changes response format, streaming breaks.
- Migration plan: (1) Monitor gemini-cli for format changes, (2) Implement version detection in response header, (3) Add format negotiation fallback to JSON array parsing.

## Missing Critical Features

**Dashboard creation/update not exposed as function-calling tools:**
- Problem: Agent can READ dashboards but cannot CREATE or UPDATE them via function calls. Only works through HA services or prompt-based UI suggestions.
- Blocks: Users cannot ask "create a dashboard with my favorite lights" and have it work directly.
- Files: `custom_components/homeclaw/tools/ha_native.py` (missing register for `create_dashboard`, `update_dashboard`)
- Plan: `/docs/PLAN-dashboard-tools.md` lists exact tasks. Ready to implement: backends exist, need tool registration.

**Vision/camera snapshot tool not implemented:**
- Problem: No tool to capture or analyze camera snapshots. Vision-capable providers (Gemini, Claude) cannot see what's happening.
- Blocks: Users cannot ask "what's on the front door camera?" and get an answer.
- Potential: Qwen 3.5 (local) supports vision natively and could run on HA for privacy.
- Plan: `/docs/PLAN-qwen35-local-edge-ai.md` outlines camera vision tool (#2 priority P1).

**Offline fallback provider not implemented:**
- Problem: If cloud provider (Gemini, OpenAI) fails, agent stops working. No local fallback.
- Blocks: Outages = downtime.
- Potential: Qwen 3.5 via Ollama can run locally for tool calling + thinking.
- Plan: `/docs/PLAN-qwen35-local-edge-ai.md` outlines offline fallback (#1 priority P1).

**Test coverage gaps in critical paths:**
- Gaps: (1) Concurrent message handling in WS chat, (2) Cross-provider function call round-trips, (3) Compaction under heavy load, (4) Discord dedup/pairing state, (5) Memory eventual consistency.
- Impact: Bugs in these areas slip into production without warning.
- Pytest coverage: 70% baseline required (`pytest.ini:16`). Current status unknown but large files (1357-line `ha_native.py`) likely have low coverage.

## Test Coverage Gaps

**WebSocket message concurrency not tested:**
- What's not tested: Multiple messages arriving simultaneously for same session. Rapid fire (10+ msgs/sec).
- Files: `custom_components/homeclaw/ws_handlers/chat.py`, tests in `tests/test_websocket_api.py`
- Risk: Race conditions in message append, compaction trigger, history persistence go unnoticed.
- Priority: **HIGH** — Discord bug #2 (duplicate processing) likely hidden here.

**Function call parser cross-provider round-trips not tested:**
- What's not tested: Full cycle for each provider: (1) LLM returns tool call, (2) Storage layer persists, (3) Next request loads from storage, (4) Parser detects format correctly.
- Files: `custom_components/homeclaw/core/function_call_parser.py`, tests in `tests/test_core/test_function_call_parser.py`
- Risk: Orphaned tool calls (Bug 3 scenario) or format misdetection happens only under specific provider+model combinations.
- Priority: **HIGH** — Bug 3 was production incident.

**Compaction under load not tested:**
- What's not tested: Compaction triggered for 10+ sessions simultaneously. Concurrent compaction requests to LLM.
- Files: `custom_components/homeclaw/core/compaction.py`, `custom_components/homeclaw/memory/manager.py`
- Risk: Queue backlog or timeout during peak usage.
- Priority: **MEDIUM** — mostly perf concern, not correctness.

**Discord pairing state machine not tested:**
- What's not tested: Full lifecycle of pairing (unpaired → awaiting confirmation → paired). Edge cases: reconnect while pairing, timeout, duplicate gateway events.
- Files: `custom_components/homeclaw/channels/discord/__init__.py`
- Risk: Bugs #1, #2, #3, #4 in `BUGS-discord-followup.md` all live here.
- Priority: **CRITICAL** — affects real Discord users.

**Memory eventual consistency not tested:**
- What's not tested: Query happening before embeddings are computed. Concurrent insert/search on same memory.
- Files: `custom_components/homeclaw/memory/manager.py`
- Risk: Race conditions where memory search returns stale or incomplete results.
- Priority: **MEDIUM** — low frequency occurrence, but correctness issue.

---

*Concerns audit: 2026-03-20*
