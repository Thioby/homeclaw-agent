# Unified Provider Adapter — Design Spec

**Date:** 2026-03-28
**Goal:** Eliminate per-provider tool use hacks by normalizing all providers to OpenAI format via a shared adapter layer, inspired by liteLLM's transformation architecture.

---

## Problem

~48% of provider code (~780 LOC) is format conversion that's highly redundant:
- Tool schema conversion: 3 separate implementations (OpenAI, Anthropic, Gemini)
- Message format conversion: 3 separate implementations (218 LOC)
- Tool call extraction: 4 separate strategies tried in priority order
- Streaming chunk parsing: 3 separate SSE parsers with duplicated tool accumulation
- `anthropic_oauth.py` duplicates ~115 LOC from `anthropic.py`

Adding a new provider (e.g. Mistral, DeepSeek) requires writing all these conversions from scratch.

## Solution

A shared adapter layer where each provider implements two transforms:
1. **Request transform:** canonical (OpenAI) format -> provider API format
2. **Response transform:** provider API response -> canonical (OpenAI) format

The core (`QueryProcessor`, `FunctionCallParser`, `tool_call_codec`, `stream_loop`) only ever sees OpenAI format.

---

## Canonical Format (OpenAI-compatible)

### Messages (input)

```python
# System
{"role": "system", "content": "You are a helpful assistant."}

# User (text)
{"role": "user", "content": "Turn on the lights"}

# User (multimodal)
{"role": "user", "content": [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
]}

# Assistant (text)
{"role": "assistant", "content": "Done!"}

# Assistant (tool call)
{"role": "assistant", "content": None, "tool_calls": [
    {"id": "call_123", "type": "function", "function": {"name": "ha_control", "arguments": "{\"entity_id\": \"light.bedroom\"}"}}
]}

# Tool result
{"role": "tool", "tool_call_id": "call_123", "content": "Light turned on"}
```

### Tool Schemas (input)

```python
{"type": "function", "function": {"name": "ha_control", "description": "...", "parameters": {"type": "object", "properties": {...}, "required": [...]}}}
```

### Streaming Chunks (output from provider)

```python
# Text delta
{"type": "text", "content": "partial text"}

# Tool call (complete, after accumulation)
{"type": "tool_call", "id": "call_123", "name": "ha_control", "args": {"entity_id": "light.bedroom"}}

# Error
{"type": "error", "content": "error message"}

# Finish
{"type": "finish", "reason": "stop" | "tool_calls" | "length"}
```

### Non-streaming Response (output from provider)

```python
# Text only
{"type": "text", "content": "Here's the answer...", "finish_reason": "stop"}

# Tool calls
{"type": "tool_calls", "tool_calls": [{"id": "call_123", "name": "ha_control", "args": {...}}], "finish_reason": "tool_calls"}
```

---

## Architecture

```
                     CANONICAL (OpenAI) FORMAT
                              |
             +----------------+----------------+
             |                                 |
     [QueryProcessor]                  [stream_loop.py]
     [tool_loop.py]                    Consumes normalized
     Builds canonical msgs             streaming chunks
             |                                 ^
             v                                 |
    +------------------+              +------------------+
    | ProviderAdapter  |              | ProviderAdapter  |
    | .transform_req() |              | .transform_resp()|
    +------------------+              +------------------+
             |                                 ^
             v                                 |
    +------------------+              +------------------+
    | Provider HTTP    |  -- HTTP --> | Raw API Response |
    +------------------+              +------------------+
```

### New Files

```
providers/
├── adapters/
│   ├── __init__.py
│   ├── base.py              # ProviderAdapter ABC (~60 LOC)
│   ├── openai_compat.py     # OpenAI/Groq/OpenRouter/z.ai adapter (~40 LOC)
│   ├── anthropic_adapter.py # Anthropic adapter (~120 LOC)
│   ├── gemini_adapter.py    # Gemini adapter (~120 LOC)
│   ├── tool_schema.py       # Tool schema conversion (~50 LOC)
│   ├── message_format.py    # Message format conversion (~100 LOC)
│   └── stream_utils.py      # SSE parsing + tool accumulation (~100 LOC)
```

### ProviderAdapter Interface

```python
class ProviderAdapter(ABC):
    """Transforms between canonical (OpenAI) format and provider-specific format."""

    @abstractmethod
    def transform_tools(self, tools: list[dict]) -> Any:
        """Convert OpenAI tool schemas to provider format."""

    @abstractmethod
    def transform_messages(self, messages: list[dict]) -> tuple[Any, Any]:
        """Convert OpenAI messages to provider format.

        Returns:
            (transformed_messages, system_content) — system extracted separately
            for providers that need it (Anthropic, Gemini).
        """

    @abstractmethod
    def transform_request(self, messages: Any, tools: Any, system: Any, **kwargs) -> dict:
        """Build the full API request payload."""

    @abstractmethod
    def extract_response(self, raw_response: dict) -> dict:
        """Extract canonical response from raw API response.

        Returns:
            {"type": "text", "content": str, "finish_reason": str}
            or {"type": "tool_calls", "tool_calls": [...], "finish_reason": "tool_calls"}
        """

    @abstractmethod
    def iter_stream_events(self, raw_chunk: str | bytes) -> list[dict]:
        """Parse a raw streaming chunk into canonical events.

        Returns list of:
            {"type": "text", "content": str}
            {"type": "tool_call", "id": str, "name": str, "args": dict}
            {"type": "finish", "reason": str}
        """
```

### Adapter Implementations

**OpenAICompatAdapter** — passthrough (tools/messages already in OpenAI format):
- `transform_tools()`: return as-is
- `transform_messages()`: convert `_images` to multimodal content blocks, format tool history
- `extract_response()`: extract from `choices[0].message`
- `iter_stream_events()`: parse SSE, accumulate tool fragments, emit complete tool calls
- Used by: OpenAI, Groq, OpenRouter, z.ai, Xiaomi

**AnthropicAdapter**:
- `transform_tools()`: `function.parameters` -> `input_schema`
- `transform_messages()`: extract system, convert tool results to `tool_result` blocks, convert tool calls to `tool_use` blocks
- `extract_response()`: separate `text` and `tool_use` content blocks, normalize to canonical
- `iter_stream_events()`: parse Anthropic event stream, accumulate tool inputs

**GeminiAdapter**:
- `transform_tools()`: wrap in `functionDeclarations`
- `transform_messages()`: convert roles, tool calls to `functionCall` parts, tool results to `functionResponse`
- `extract_response()`: extract from `candidates[0].content.parts`
- `iter_stream_events()`: parse Gemini streaming, handle `thoughtSignature`
- Reuses existing `_gemini_convert.py` pure functions where possible

---

## What Changes in Existing Code

### Simplified (major changes)

1. **`FunctionCallParser`** — currently tries 5 strategies. After: only 1 (canonical format), because providers return normalized responses. The parser becomes trivial or eliminated entirely.

2. **`tool_call_codec.py`** — currently stores backward-compat formats for every provider. After: stores only canonical `tool_calls` format. `build_assistant_tool_message()` and `extract_tool_calls_from_assistant_content()` become simpler.

3. **`ToolSchemaConverter`** (`function_calling.py`) — currently has `to_openai_format()`, `to_anthropic_format()`, `to_gemini_format()`. After: only `to_openai_format()` survives. Adapters handle the rest.

4. **`context_builder.py:repair_tool_history()`** — currently must detect multiple formats. After: only canonical format.

5. **`anthropic_oauth.py`** — ~115 LOC of duplicated format conversion eliminated. Becomes thin OAuth wrapper + shared AnthropicAdapter.

6. **`gemini_oauth.py`** — format conversion delegated to GeminiAdapter. File keeps only: OAuth, project ID management, model fallback chains, retry logic.

### Unchanged

- `AIProvider` base class and `ProviderRegistry` — unchanged
- `BaseHTTPClient` template — unchanged (adapters plug into it)
- `QueryProcessor` orchestration — unchanged (already works with canonical format conceptually)
- `stream_loop.py` / `tool_loop.py` — minimal changes (already expect normalized chunks)
- Tool definitions (`tools/base.py`, `ToolRegistry`) — unchanged
- Progressive tool loading — unchanged
- OAuth token management — unchanged (stays in provider files)
- Gemini model fallback chains — unchanged

---

## Shared Utilities

### `stream_utils.py`

```python
class SSEParser:
    """Parse Server-Sent Events from raw bytes/text."""
    def feed(self, chunk: str) -> list[str]:
        """Feed raw data, return complete events."""

class ToolAccumulator:
    """Accumulate partial tool call fragments across streaming chunks."""
    def add_fragment(self, index: int, id: str | None, name: str | None, args_delta: str) -> None:
    def flush_complete(self) -> list[dict]:
        """Return and clear any completed tool calls."""
    def flush_all(self) -> list[dict]:
        """Force-flush all pending (end of stream)."""
```

### `tool_schema.py`

```python
def to_anthropic_tools(openai_tools: list[dict]) -> list[dict]:
    """Convert OpenAI tool schemas to Anthropic format."""

def to_gemini_tools(openai_tools: list[dict]) -> list[dict]:
    """Convert OpenAI tool schemas to Gemini functionDeclarations format."""
```

### `message_format.py`

```python
def extract_system_message(messages: list[dict]) -> tuple[list[dict], str | None]:
    """Remove and return system message from message list."""

def images_to_multimodal(messages: list[dict], format: str) -> list[dict]:
    """Convert _images attachments to provider-specific multimodal blocks."""

FINISH_REASON_MAP: dict[str, str]  # All provider finish reasons -> canonical
```

---

## Migration Strategy

**Phase 1:** Create adapter layer alongside existing code (no breaking changes)
- Write `adapters/` module with all adapters
- Write tests for adapters independently

**Phase 2:** Wire adapters into providers
- Each provider delegates format conversion to its adapter
- Remove duplicated conversion code from providers
- `anthropic_oauth.py` uses same adapter as `anthropic.py`

**Phase 3:** Simplify core
- `FunctionCallParser` simplified to canonical-only
- `tool_call_codec.py` simplified
- `ToolSchemaConverter` reduced to OpenAI-only
- `context_builder.py` simplified

**Phase 4:** Cleanup
- Remove dead code from `function_calling.py` (Anthropic/Gemini converters)
- Update AGENTS.md

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Format conversion LOC | ~780 | ~430 (adapters) |
| Adding new OpenAI-compat provider | ~50 LOC | ~10 LOC (just URL + model) |
| Adding new non-OpenAI provider | ~200-500 LOC | ~120 LOC (adapter only) |
| `FunctionCallParser` strategies | 5 | 1 |
| `ToolSchemaConverter` methods | 3 | 1 |
| `tool_call_codec` compat formats | 3 | 1 |
| `anthropic_oauth.py` duplication | 115 LOC | 0 |

---

## Risks

1. **Regression in tool call parsing** — existing tests cover this well, but edge cases (Gemini thoughtSignature, Anthropic parallel tool use) need careful testing
2. **Streaming behavior changes** — providers stream differently; adapter must preserve existing behavior exactly
3. **OAuth providers have complex flows** — adapter only handles format; OAuth logic stays in provider
4. **`repair_tool_history()` depends on current format** — must update simultaneously

## Testing Strategy

- Unit tests for each adapter (transform_tools, transform_messages, extract_response, iter_stream_events)
- Integration tests verifying tool call round-trip: schema -> API request -> API response -> canonical
- Existing provider tests updated to use adapters
- No new external dependencies
