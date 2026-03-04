# Dynamic Tool Loading - Research & Architecture

## Problem

Homeclaw currently eagerly loads all 11 tools into every LLM context, regardless of query relevance. Each tool schema consumes ~400-500 tokens (OpenAI format), meaning ~5K tokens are wasted per call. As the tool count grows (planned integrations, MCP servers, user-added tools), this will:

1. **Pollute context** - irrelevant tool definitions crowd out useful information
2. **Degrade selection accuracy** - LLMs struggle with >20-30 tools (accuracy drops from ~97% to ~69% per MCP-Zero research)
3. **Waste tokens/money** - paying for schema tokens that add no value
4. **Break KV-cache** - dynamic tool sets invalidate prompt caching (Manus finding)

### Current Architecture

- **ToolRegistry** (`tools/base.py`) - decorator-based registration, all tools loaded at import time
- **ToolSchemaConverter** (`function_calling.py`) - converts all tools to OpenAI/Anthropic/Gemini formats
- **QueryProcessor** (`core/query_processor.py`) - receives full `tools` list, passes to provider
- **RAG subsystem** (`rag/`) - already has embeddings (Gemini/OpenAI), SQLite vector store, hybrid search, caching

**11 tools registered** in `tools/__init__.py`:
1. `ha_native` - HA entity/automation/service/dashboard operations (largest, 43KB)
2. `websearch` - Web search via Exa AI
3. `webfetch` - Fetch and parse URLs
4. `scheduler` - Cron-based task scheduling
5. `memory` - Long-term memory storage/recall
6. `identity` - User identity management
7. `integration_manager` - HA integration setup
8. `subagent` - Background agent spawning
9. `context7` - Library documentation lookup
10. `channel_status` - Discord/channel status
11. `memory` - Memory management tools

---

## Research: Existing Solutions

### 1. Tiered Loading (Manus AI)

**Source:** [manus.im/blog/Context-Engineering](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)

**Mechanism:** Tools organized into 3 tiers:
- **Tier 1 (Atomic):** ~20 core tools always in context. Stable, cache-friendly definitions.
- **Tier 2 (Sandbox Utilities):** Rather than discrete tools, instruct models to use general-purpose executors (e.g., bash). Keeps tool definitions out of context.
- **Tier 3 (Code/Packages):** For multi-step workflows, provide libraries rather than separate LLM invocations.

**Critical finding:** Manus does NOT use dynamic tool RAG. Their finding:
> "Fetching tool definitions dynamically per step based on semantic similarity often fails because (a) it breaks KV-cache invalidation (tool definitions are near the front of context, so any change re-computes all downstream KV pairs), and (b) when previous actions reference tools no longer in context, the model gets confused, leading to schema violations or hallucinated actions."

**Alternative:** Instead of removing/adding tools, Manus uses **logit masking during decoding** — keeping all ~20 core tool definitions in context (stable, cache-friendly) while using a state machine to mask which tools can be emitted as output tokens.

**Pros:**
- Maximum KV-cache efficiency
- No per-step retrieval latency
- Eliminates tool-disappearance confusion

**Cons:**
- Logit masking requires model server access (not applicable to API-only usage)
- Tier structure requires upfront design discipline

**Applicability to Homeclaw:** Medium-High. Logit masking is not available via OpenAI/Anthropic APIs, but the tiering principle is directly applicable.

---

### 2. Anthropic `defer_loading` + Tool Search Tool (Beta)

**Source:** [platform.claude.com/docs - Tool Search Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)

**Mechanism:**
1. Include a tool search tool (`tool_search_tool_regex` or `tool_search_tool_bm25`) in the `tools` array
2. All other tool definitions passed with `defer_loading: true` - NOT injected into context at request time
3. Claude initially sees ONLY the search tool + non-deferred tools
4. When Claude needs a capability, it calls the search tool with regex or BM25 query
5. API returns 3-5 most relevant `tool_reference` blocks
6. These are automatically expanded into full tool definitions

**Two search variants:**
- **Regex** (`tool_search_tool_regex`): Claude generates Python `re.search()` patterns against tool names/descriptions. Fast, deterministic.
- **BM25** (`tool_search_tool_bm25`): Claude writes natural language queries; server uses BM25 sparse retrieval.

**Custom client-side search:** You can implement your own search tool (e.g., using dense embeddings) and return `tool_reference` blocks from a standard `tool_result`.

**Auto-trigger in Claude Code CLI:** Automatically enables when MCP tool descriptions consume >10% of context window (or 10K tokens).

**Stats:**
- 50 tools typically consume 10,000-20,000 tokens when eagerly loaded
- **85% token reduction** with Tool Search
- Accuracy up from 49% to 74% (Opus 4)
- Supports up to 10,000 tools in catalog
- Returns 3-5 per search

**Pros:**
- Solves both context efficiency and tool selection accuracy
- Regex is fast and deterministic; BM25 requires no embedding infrastructure
- Custom search hooks allow dense embedding approaches
- Prompt caching works correctly — discovered tools persist across turns

**Cons:**
- Public beta (early 2026); not compatible with tool-use examples
- Only works with Anthropic API (vendor lock-in)
- BM25 is lexical, not semantic — weak on synonym matching
- Haiku models excluded

**Applicability to Homeclaw:** High for Anthropic provider. Not portable to Gemini/OpenAI.

---

### 3. Embedding-Based Tool Selection (MCP-Zero, Semantic Router)

#### MCP-Zero

**Source:** [arxiv.org/abs/2506.01056](https://arxiv.org/abs/2506.01056), [github.com/xfey/MCP-Zero](https://github.com/xfey/MCP-Zero)

**Mechanism:** The LLM itself generates a structured tool request:
```json
{
  "server": "github",
  "tool": "search repository files by pattern"
}
```

The framework's **hierarchical semantic routing** runs two stages:
1. Match `server` field against server descriptions using vector embeddings
2. Score tools within matched servers: `score = (s_server * s_tool) * max(s_server, s_tool)`

**Results on 2,797 tools across 308 MCP servers:**
- **98% reduction in token consumption** (6,308 tokens → 111 tokens on APIBank)
- Standard approaches: accuracy fell from 97.6% to 69.2% as catalog grew from 40 to 1,760+ tools
- MCP-Zero maintained **95.19% accuracy** throughout

#### Semantic Router

**Source:** [github.com/aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router)

**Mechanism:**
- Define `Route` objects with example utterances per route
- Query embedding compared against route utterance embeddings
- Pure vector math, millisecond latency
- Supports Cohere, OpenAI, HuggingFace, FastEmbed encoders

#### LlamaIndex ToolRetriever

**Source:** [developers.llamaindex.ai - agent retrieval](https://developers.llamaindex.ai/python/examples/agent/openai_agent_retrieval/)

**Mechanism:**
- `ObjectIndex.from_objects()` creates vector index over `FunctionTool` objects
- Agent initialized with `tool_retriever=obj_index.as_retriever(similarity_top_k=2)`
- Only top-2 semantically matched tools passed to LLM per query

#### Cline Discussion: MCP + Embeddings

**Source:** [github.com/cline/cline/discussions/3081](https://github.com/cline/cline/discussions/3081)

- Embed user prompts and tool descriptions using same encoder
- Similarity search narrows from 100+ tools to ~20 before LLM invocation
- BAML (Boundary Markup Language) enforces schema validation on retrieved tools

**Pros (all embedding approaches):**
- Handles catalogs orders of magnitude larger than eager loading
- Token consumption near-zero for unused tools
- Works across tool ecosystems (not vendor-specific)
- Encoder-based routing is much faster than an LLM generation step

**Cons:**
- Requires embedding infrastructure (encoder model, vector store)
- Embedding quality determines retrieval quality
- Cold start: embeddings must be pre-computed
- Dense retrieval can miss exact-match patterns where BM25 would succeed
- Threshold tuning required

**Applicability to Homeclaw:** Very High. Existing `rag/embeddings.py` + `rag/sqlite_store.py` already provides this infrastructure. Extending from entity embeddings to tool embeddings is minimal work.

---

### 4. MCP Protocol - Tool Discovery & Dynamic Loading

**Source:** [modelcontextprotocol.io/specification/2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)

**Core protocol:**
- `tools/list` — client requests available tools from a server
- `tools/call` — client invokes a specific tool
- `notifications/tools/list_changed` — server notifies when tools change

**Problem:** Default = host fetches ALL tools from ALL MCP servers and injects full schemas. At 400-500 tokens/tool, 50 tools = 20K-25K tokens.

#### lazy-mcp

**Source:** [github.com/voicetreelab/lazy-mcp](https://github.com/voicetreelab/lazy-mcp)

**Mechanism:** Proxy server exposing only two meta-tools:
- `get_tools_in_category(path)` - browse tool hierarchy
- `execute_tool(tool_path, arguments)` - lazy-load target MCP server on demand

**Savings:** 34,000 tokens (17% of Claude Code context window) in real use.

#### Hierarchical Tool Management Proposal

**Source:** [github.com/orgs/modelcontextprotocol/discussions/532](https://github.com/orgs/modelcontextprotocol/discussions/532)

Proposes native MCP extensions:
- `tools/categories` and `tools/discover` endpoints for browsing without loading schemas
- `tools/load` and `tools/unload` for managing active tool subsets
- Enhanced metadata: category, namespace, latency estimates, usage examples

**Applicability to Homeclaw:** Medium. Relevant when/if Homeclaw starts consuming MCP servers as a client.

---

### 5. SKILLS.md Pattern (Claude Code Agent Skills)

**Source:** [agentskills.io](https://agentskills.io), [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)

**Mechanism:** Capabilities packaged as directories with `SKILL.md` entrypoint:
```
my-skill/
├── SKILL.md          # YAML frontmatter + markdown
├── reference.md      # heavy docs (loaded on demand)
└── scripts/helper.py
```

**Progressive loading in 3 stages:**
1. **Metadata stage**: Only `name` + `description` from frontmatter (2% of context budget)
2. **Skill body stage**: Full `SKILL.md` injected when Claude decides skill is relevant
3. **Supporting files stage**: Claude reads referenced files only if needed

**Key insight (Armin Ronacher):** Skills do NOT register new API-level tools. They inject instructions into conversation as user messages. Claude uses its existing tools more intelligently, guided by skill instructions. Avoids tool schema overhead entirely.

**Pros:**
- Zero schema overhead
- Progressive loading
- Flexible invocation control
- Monorepo-aware discovery

**Cons:**
- Not suited for function-calling flow
- No semantic/embedding-based matching

**Applicability to Homeclaw:** Low for function-calling tools. Could be useful for adding "knowledge skills" (e.g., HA best practices, troubleshooting guides) that don't need tool schemas.

---

### 6. OpenClaw / PicoClaw

**Source:** [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw), [github.com/sipeed/picoclaw](https://github.com/sipeed/picoclaw)

**OpenClaw** (68K+ GitHub stars): Personal AI agent with 50+ integrations (WhatsApp, Telegram, Slack, Discord, iMessage, Teams).

**Tool management:**
- Multi-tier: bundled skills (core), managed skills (curated), workspace skills (`~/.openclaw/workspace/skills/`)
- `SKILL.md` files describe capabilities
- **ClawHub registry** for automatic tool discovery
- **Channel-specific routing**: tools target Discord/Slack natively; device-level commands dispatched via `node.invoke`

**PicoClaw** (ultra-lightweight Go reimplementation, <10MB RAM):
- `TOOLS.md` in workspace describes capabilities
- `HEARTBEAT.md` - unique pattern: file checked every 30 minutes containing periodic task prompts. Scheduled context injection rather than request-driven.
- Sandboxed workspace by default

**Applicability to Homeclaw:** Medium. The `HEARTBEAT.md` pattern is interesting for HA's event-driven model. The workspace file hierarchy is a low-friction way to organize tools.

---

### 7. Cursor / Windsurf / Cline Tool Management

#### Cursor

**Source:** [webrix.ai/blog/cursor-mcp-features](https://webrix.ai/blog/cursor-mcp-features-blog-post)

**Mechanism:**
- **Always-available ceiling:** ~30 core tools always in context
- **Category-based demand loading:** `add_tools(categories=[...])` triggers loading additional category
- **Usage-based eviction:** Tools track `last_usage_timestamp`. When ceiling hit, oldest/least-used evicted
- **MCP notification:** Server sends `tools/list_changed`, Cursor updates dynamically
- Exposes 100+ internal tools through single MCP connection

**Key insight:** Ceiling + category loading + usage-based eviction is practical and deployable without embedding infrastructure.

#### Cline

- MCP Marketplace for one-click installs
- All connected MCP server tools available simultaneously (no per-query filtering)
- Deep context management: reads entire codebases

#### Windsurf

- Admin controls for enterprise tool governance
- Tools written to disk before approval (human-in-the-loop gating)

---

### 8. OpenAI Function Calling Best Practices

**Source:** [platform.openai.com/docs/guides/function-calling](https://platform.openai.com/docs/guides/function-calling)

- **Soft limit: <20 functions** at any time
- **Hard tested limit: ~100 tools, ~20 arguments per tool** are "in-distribution"
- **For 50+ tools:** "embedding similarity decides the tool" - build retrieval layer yourself
- **Reasoner models:** Use o3/o4-mini to pre-determine which tools to call and in which order
- **Strict mode:** Always use `strict: true` to eliminate schema violations
- **Tool quality:** Brief description is the single most impactful factor in selection accuracy

---

### 9. Anthropic Tool Use Best Practices

**Source:** [anthropic.com/engineering/advanced-tool-use](https://www.anthropic.com/engineering/advanced-tool-use), [anthropic.com/engineering/writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

- **Defer loading** (`defer_loading: true`): Mark infrequently needed tools
- **Programmatic tool calling:** Claude generates Python code to orchestrate tools in sandbox. **37% token reduction** on complex research tasks (43K → 27K tokens)
- **Tool design principles:**
  - Implement `search_contacts` not `list_contacts` — agents should not page through large lists
  - Consolidate related operations: single `schedule_event` vs `list_users` + `list_events` + `create_event`
  - Namespace tools: `asana_search`, `jira_search` (prevents confusion)
  - Return only high-signal data; support `response_format` enum for verbosity control
  - Add pagination, filtering, truncation with sensible defaults

---

### 10. "Tool Use is Agentic Search" Pattern

**Source:** [deeplearning.ai - Agentic Design Patterns](https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-3-tool-use/), [lilianweng.github.io - LLM Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)

When hundreds of tools available, the agent first uses a search/index tool to find the right tool, then uses that tool. The search step itself is a tool call:

```
Phase 1: search_tools(query="control lights") → ["ha_light_control", "ha_scene"]
Phase 2: ha_light_control(entity_id="...", state="on") → success
```

This is exactly what Anthropic's Tool Search Tool, LlamaIndex's `ToolRetriever`, and LangGraph's `select_tools` node formalize.

---

### 11. LangGraph / LlamaIndex Tool Routing

#### LangGraph "many-tools" pattern

**Source:** [langchain-ai.github.io/langgraph/how-tos/many-tools/](https://langchain-ai.github.io/langgraph/how-tos/many-tools/)

```
State: { messages: [...], selected_tools: [...] }
Graph: [select_tools node] → [agent node] → [tools node]
                              ↑_________________________| (error recovery loop)
```

- `select_tools` embeds current query, retrieves relevant tool IDs from vector store
- `agent` binds only `state.selected_tools` to LLM
- Error recovery: if wrong tools selected, `tools` node routes back to `select_tools`

#### Dynamic Tool Calling Middleware

**Source:** [changelog.langchain.com](https://changelog.langchain.com/announcements/dynamic-tool-calling-in-langgraph-agents)

`@wrap_model_call` middleware filters tools based on conversation state, auth, permissions, or feature flags before each model invocation.

---

### 12. Tool-to-Agent Retrieval (Research Paper)

**Source:** [arxiv.org/html/2511.01854v1](https://arxiv.org/html/2511.01854v1)

Bipartite graph links tools to parent agents. Both embedded in shared vector space. On LiveMCPBench (527 tools, 70 MCP servers): **+19.4% Recall@5, +17.7% nDCG@5** over prior agent retrievers.

---

## Comparison Matrix

| Approach | Token Savings | Latency Cost | Infra Needed | Scales to 1K+ | Vendor Lock |
|---|---|---|---|---|---|
| Tiering (Manus) | High | Zero | None | No (~30 limit) | None |
| Anthropic defer_loading | 85% | Near-zero | API beta | Yes (10K) | Anthropic |
| Embeddings (MCP-Zero) | 98% | +1 embed call | Embedding provider | Yes (tested 2,797) | None |
| lazy-mcp proxy | High | +1 proxy call | MCP proxy | Yes | None |
| SKILLS.md | Good | Zero | None | Moderate | None |
| Cursor ceiling+eviction | Medium | Zero | None | Yes | None |
| LangGraph select_tools | High | +1 embed call | Vector store | Yes | None |
| Agentic search (2-phase) | Very High | +1 call | Search index | Yes | None |

---

## Recommended Approach: Progressive Tool Loading (load_tool pattern)

### Dlaczego SKILLS.md jednak zadziała

Pierwotna ocena ("SKILLS.md nie pasuje do function-calling flow") była zbyt powierzchowna. SKILLS.md **nie musi** zastępować function-calling — może je **uzupełniać** w modelu progressive loading:

1. Krótkie opisy tooli (jak SKILLS.md frontmatter) → zawsze w system prompt
2. Pełne schematy function-calling → ładowane on-demand przez meta-tool
3. Po załadowaniu → natywne function calling z pełną walidacją parametrów

To łączy zalety SKILLS.md (lekkie opisy, progressive loading) z zaletami function-calling (strict mode, walidacja typów).

### Mechanika

```
System prompt (stały, cache-friendly):
┌─────────────────────────────────────────────────────────┐
│ Available tools (use load_tool to activate):             │
│ - websearch: Search the web for current information      │
│ - webfetch: Fetch and parse content from any URL         │  ~50 tok × 8
│ - context7: Library documentation lookup                 │  = ~400 tok
│ - integration_manager: Setup HA integrations             │  (zamiast ~4000)
│ - identity: Manage user identity and preferences         │
│ - channel_status: Check Discord channel status           │
│ - subagent: Spawn background agent for complex tasks     │
└─────────────────────────────────────────────────────────┘

Native function-calling schemas (zawsze załadowane):
┌─────────────────────────────────────────────────────────┐
│ ha_native    - pełny schemat  (~500 tok)  ← CORE        │
│ memory       - pełny schemat  (~300 tok)  ← CORE        │
│ scheduler    - pełny schemat  (~300 tok)  ← CORE        │
│ load_tool    - pełny schemat  (~100 tok)  ← meta-tool   │
└─────────────────────────────────────────────────────────┘
```

### Flow przykładowy

```
User: "Wyszukaj pogodę na jutro w Krakowie"

Iteracja 1:
  LLM widzi opis "websearch: Search the web" w system prompt
  → wywołuje load_tool("websearch")
  → load_tool zwraca opis + parametry jako tool result
  → QueryProcessor DODAJE websearch do effective_tools

Iteracja 2:
  LLM ma teraz websearch w schematach function-calling
  → wywołuje web_search(query="pogoda Kraków jutro")  ← pełna walidacja!
  → wynik zwrócony użytkownikowi
```

### Porównanie z innymi podejściami

| | Embedding retrieval | load_tool (progressive) | Eager (obecny stan) |
|---|---|---|---|
| Kto decyduje? | cosine similarity | **LLM sam** (pełen kontekst) | nikt (wszystko) |
| Infrastruktura | embedding provider + index | **zero** | zero |
| Walidacja params | pełna ale może wybrać złe | **pełna, świadomy wybór** | pełna |
| Tokeny (11 tooli) | ~2-2.5K | **~1.6K** | ~5.5K |
| Dodatkowy koszt | +1 embedding/query | +1 round-trip/tool | zero |
| Cache-friendly | zależy od selekcji | **tak** (system prompt stały) | tak |
| Skalowanie | do 1000+ tooli | do ~50-100 tooli | do ~20 tooli |
| Vendor lock | żaden | **żaden** | żaden |

**Kluczowa przewaga:** LLM sam decyduje co potrzebuje, mając pełen kontekst konwersacji.
Cosine similarity na krótkich opisach tooli jest kiepski — "zaplanuj mi coś na jutro"
nie matchuje embeddinowo z "scheduler", ale LLM od razu wie że potrzebuje schedulera.

### Zmiana w kodzie — minimalna

Jedno miejsce: **tool-call loop w `QueryProcessor.process_stream()`**:

```python
# Po wykonaniu tool calla, jeśli to load_tool:
if tool_name == "load_tool":
    loaded_tool_id = tool_result  # np. "websearch"
    new_tool = ToolRegistry.get_tool(loaded_tool_id, hass=hass)
    if new_tool:
        # Dodaj schemat do effective_tools na kolejne iteracje
        new_schema = ToolSchemaConverter.to_current_format([new_tool])
        effective_tools.extend(new_schema)
```

Reszta pipeline'u (provider, function calling, tool executor) — **bez zmian**.

### Ograniczenia

- Przy 100+ toolach nawet krótkie opisy zajmą za dużo system promptu
  → wtedy warto dodać embedding retrieval jako pre-filter na opisy
- +1 round-trip gdy ON_DEMAND tool potrzebny (ale to samo co agentic search)
- Przy obecnych 11 toolach i planowanych ~30-50 — opisy to ~2-3K tokenów, akceptowalne

### Implementation steps

1. Add `ToolTier` enum + `tier` field to `Tool` base class (`tools/base.py`)
2. Annotate CORE tools: `ha_native`, `memory`, `scheduler`
3. Create `load_tool` meta-tool (`tools/load_tool.py`) — tier=CORE, always available
4. Modify `ToolRegistry.get_system_prompt()` to emit short descriptions for ON_DEMAND tools
5. Modify `QueryProcessor` tool-call loop to dynamically extend `effective_tools` after `load_tool`
6. Each tool's SKILL.md-style description stored as `Tool.short_description` class var

### Future enhancements

- Anthropic `defer_loading` when it exits beta (native support for same pattern)
- Usage-based tier promotion (auto-promote frequently used tools to CORE)
- Per-channel tool sets (Discord vs voice assistant)
- MCP server lazy loading via `lazy-mcp` pattern
- Embedding pre-filter when tool count exceeds ~50

---

## Sources

- [Manus Context Engineering Blog](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [Phil Schmid - Context Engineering Part 2](https://www.philschmid.de/context-engineering-part-2)
- [Anthropic - Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Anthropic - Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Anthropic - Tool Search Tool Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- [Anthropic - Implement Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [MCP-Zero Paper (arXiv 2506.01056)](https://arxiv.org/abs/2506.01056)
- [MCP-Zero GitHub](https://github.com/xfey/MCP-Zero)
- [MCP Specification Nov 2025](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Hierarchical Tool Management Discussion](https://github.com/orgs/modelcontextprotocol/discussions/532)
- [lazy-mcp GitHub](https://github.com/voicetreelab/lazy-mcp)
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Skills vs Dynamic MCP Loadouts (Armin Ronacher)](https://lucumr.pocoo.org/2025/12/13/skills-vs-mcp/)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [PicoClaw GitHub](https://github.com/sipeed/picoclaw)
- [Semantic Router GitHub](https://github.com/aurelio-labs/semantic-router)
- [LangGraph - Many Tools](https://langchain-ai.github.io/langgraph/how-tos/many-tools/)
- [LangChain - Dynamic Tool Calling](https://changelog.langchain.com/announcements/dynamic-tool-calling-in-langgraph-agents)
- [LlamaIndex - Retrieval-Augmented Agents](https://developers.llamaindex.ai/python/examples/agent/openai_agent_retrieval/)
- [Tool-to-Agent Retrieval Paper (arXiv 2511.01854)](https://arxiv.org/html/2511.01854v1)
- [Cursor MCP Dynamic Tools](https://webrix.ai/blog/cursor-mcp-features-blog-post)
- [Cline GitHub](https://github.com/cline/cline)
- [Cline MCP Embeddings Discussion](https://github.com/cline/cline/discussions/3081)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [DeepLearning.AI - Agentic Design Patterns: Tool Use](https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-3-tool-use/)
- [Lilian Weng - LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)
- [Claude Code Lazy Loading Issue #7336](https://github.com/anthropics/claude-code/issues/7336)
- [Claude Code Dynamic Context Issue #4689](https://github.com/anthropics/claude-code/issues/4689)
