# Tool-Calling Runtime Unification Plan (OpenCode-style)

## Goal

Make tool calling stable across providers by replacing provider-specific orchestration in `QueryProcessor` with one shared runtime and thin provider adapters.

## Why this is needed

- Anthropic OAuth currently produces many invalid tool calls (`args: {}`), causing loops and API 400 errors.
- We currently rely on provider-specific payload parsing and ad-hoc message reconstruction in multiple places.
- OpenCode is stable because it uses one tool-calling runtime and keeps provider logic mostly in transform/adapter layers.

## Target architecture

1. **Unified runtime in core**
   - One loop for text streaming, tool-call capture, tool execution, and continuation.
   - Provider-independent event protocol (`text`, `tool_call`, `status`, `error`, `complete`).

2. **Canonical tool-call state**
   - Normalize call objects to `{id, name, args, raw}`.
   - Preserve call IDs end-to-end and use them for all tool results.

3. **Thin provider adapters**
   - Providers only translate message format and stream event format.
   - No provider-specific orchestration in `QueryProcessor`.

4. **Pre-execution argument guardrails**
   - Validate tool arguments before execution.
   - If invalid, return structured `tool_error` payload with missing fields.
   - Allow bounded self-correction loop instead of repeatedly executing with `{}`.

5. **Strict pairing for Anthropic**
   - Ensure every `tool_result.tool_use_id` matches a prior assistant `tool_use.id`.
   - Support multiple tool calls in a single assistant turn.

6. **Telemetry and observability**
   - Track per-provider counters:
     - `tool_calls_total`
     - `tool_calls_invalid_args`
     - `tool_calls_repaired`
     - `tool_api_400_total`
     - `tool_loop_max_iterations`

## Implementation phases

### Phase 1: Runtime foundation

- Add shared helper utilities in core for:
  - Tool call normalization
  - Tool argument validation feedback
  - Assistant tool-call message persistence (multi-call aware)
- Refactor `QueryProcessor` to use these helpers in both streaming and non-streaming paths.

### Phase 2: Provider normalization

- Anthropic and Anthropic OAuth:
  - Normalize assistant tool message parsing from canonical format.
  - Preserve all parallel tool calls.
  - Reject or skip malformed tool results lacking valid call IDs.
- Gemini OAuth:
  - Keep current stream parser fixes and align emitted tool-call events with canonical schema.

### Phase 3: Expand to remaining providers

- Implement streaming-compatible normalized event output for OpenAI/OpenRouter (or fallback wrapper with canonical event shape).
- Remove remaining provider-specific orchestration paths from `QueryProcessor`.

### Phase 4: Tests and metrics

- Add regression tests for:
  - Parallel tool calls (ID pairing)
  - Invalid args correction loop
  - Anthropic strict tool_use/tool_result pairing
  - Max-iteration behavior with forced text fallback
- Add log counters to compare Anthropic vs Gemini failure rates over time.

## Definition of done

- Anthropic OAuth no longer produces frequent `unexpected tool_use_id` 400 errors.
- Missing-required-parameter loops are dramatically reduced by pre-execution validation feedback.
- Streaming UX remains incremental on UI while tool loop is stable.
- Same orchestration path is used across providers with only adapter differences.
