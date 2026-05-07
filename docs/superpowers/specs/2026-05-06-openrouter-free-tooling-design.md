# OpenRouter — free models with tool calling

**Date:** 2026-05-06
**Status:** Approved (design)

## Goal

Make OpenRouter a first-class option for users who want zero-cost LLMs that can drive Home Assistant tools. Today the integration registers OpenRouter as a provider but ships an outdated, paid-model default list (`openai/gpt-4o`, `anthropic/claude-3.5-sonnet`, …). The result is that picking OpenRouter immediately costs money and offers no advantage over going to those providers directly.

After this change, choosing OpenRouter in the config flow gives the user a curated list of 16 free models that all support function calling, with a sensible default that works for HA tool calls out of the box.

## Non-goals

- No dynamic fetch of `/api/v1/models` — the static list will be updated by hand when it goes stale (one JSON edit per refresh).
- No model fallback chain (`models[]`), no provider preferences (`provider`), no cost tracking (`usage.cost`), no `reasoning` parameter — separate features, separate specs.
- No migration to OpenAI SDK or `@openrouter/sdk` — out of scope, see "Decision: stay on raw HTTP" below.
- No frontend changes — `ProviderSelector` / `ModelSelector` already pull provider and model lists dynamically from the `homeclaw/providers/config` WS handler.
- No new translation strings — model descriptions live in `models_config.json` as plain data, not i18n keys.

## Decision: stay on raw HTTP (no SDK)

The user asked whether to switch to OpenRouter's official SDK. The answer is no, for these reasons:

- **Python SDK doesn't exist.** OpenRouter ships `@openrouter/agent` and `@openrouter/sdk` for TypeScript only. Their official Python guidance is "use the OpenAI SDK with `base_url=https://openrouter.ai/api/v1`".
- **Architectural consistency.** Every other provider (`OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `XiaomiProvider`, `ZaiProvider`, `GroqProvider`) inherits from `BaseHTTPClient` and uses raw `aiohttp` via `aiohttp_client.async_get_clientsession(hass)` — a Home Assistant requirement. Mixing in the OpenAI SDK only for OpenRouter would break the pattern.
- **No realised value.** OpenRouter's chat completions API is the OpenAI wire format with extra optional keys (`provider`, `models`, `usage.cost`, `reasoning`). They are dict keys in a JSON payload — `_build_payload` adds them in two lines when needed. The SDK gives no extra ergonomics here, because we already normalise responses to canonical chunks via `OpenAICompatAdapter`.
- **HA dependency rules.** Adding `openai` to `manifest.json` pulls `httpx`, `pydantic`, `tiktoken` for no benefit. We already have the streaming SSE parser and `ToolAccumulator` in place.
- **Agent SDK is a non-starter** — it competes with this project's own tool-execution loop in `function_calling.py` and `core/`.

## Architecture

Unchanged. `OpenRouterProvider(OpenAIProvider)` continues to inherit OpenAI-compatible streaming, tool calling, and multimodal handling from `OpenAIProvider`. The difference vs. today is **data** (curated free-model list, new default) plus a small `lightweight_model` override.

## Changes

### 1. `custom_components/homeclaw/models_config.json` — section `openrouter`

Replace the eight current models with the 16 entries from OpenRouter's "Free Models" collection (https://openrouter.ai/collections/free-models), in the order the page lists them. Each entry keeps the existing schema (`id`, `name`, `description`, `context_window`).

- `description` (provider-level) → `"OpenRouter — free models with tool calling"`
- `allow_custom_model: true` stays (users can still type any OpenRouter model id).
- `default: true` on `tencent/hy3-preview:free` (top of the curated list).

The 16 models, in order:

| # | id | name | ctx |
|---|---|---|---|
| 1 | `tencent/hy3-preview:free` | Tencent Hy3 Preview | 262144 |
| 2 | `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA Nemotron 3 Super | 262144 |
| 3 | `inclusionai/ling-2.6-1t:free` | inclusionAI Ling 2.6 1T | 262144 |
| 4 | `openrouter/owl-alpha` | OpenRouter Owl Alpha | 1048576 |
| 5 | `poolside/laguna-m.1:free` | Poolside Laguna M.1 | 131072 |
| 6 | `openai/gpt-oss-120b:free` | OpenAI gpt-oss-120b | 131072 |
| 7 | `z-ai/glm-4.5-air:free` | Z.ai GLM 4.5 Air | 131072 |
| 8 | `minimax/minimax-m2.5:free` | MiniMax M2.5 | 196608 |
| 9 | `nvidia/nemotron-3-nano-30b-a3b:free` | NVIDIA Nemotron 3 Nano 30B | 256000 |
| 10 | `openai/gpt-oss-20b:free` | OpenAI gpt-oss-20b | 131072 |
| 11 | `poolside/laguna-xs.2:free` | Poolside Laguna XS.2 | 131072 |
| 12 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | NVIDIA Nemotron 3 Nano Omni | 256000 |
| 13 | `google/gemma-4-31b-it:free` | Google Gemma 4 31B | 262144 |
| 14 | `nvidia/nemotron-nano-9b-v2:free` | NVIDIA Nemotron Nano 9B V2 | 128000 |
| 15 | `nvidia/nemotron-nano-12b-v2-vl:free` | NVIDIA Nemotron Nano 12B V2 VL | 128000 |
| 16 | `google/gemma-4-26b-a4b-it:free` | Google Gemma 4 26B A4B | 262144 |

Short one-line `description` per entry, mirroring the highlights from the collection page (e.g. `tencent/hy3-preview:free` → "Configurable reasoning, code generation, agentic workflows").

### 2. `custom_components/homeclaw/providers/openrouter.py`

Two changes:

- `DEFAULT_MODEL` constant: `"openai/gpt-4o"` → `"tencent/hy3-preview:free"`.
- New property `lightweight_model` returning `"openai/gpt-oss-20b:free"`. Background tasks (session-title generation, emoji synthesis, summarisation) call this instead of the user-selected model, which spares the rate-limit budget on the heavier default. Pattern matches `gemini_oauth.py:125-129`.

Headers (`Authorization`, `Content-Type`, `HTTP-Referer`, `X-Title`) stay as they are. `X-Title` is the historical name and OpenRouter still accepts it; no need to rename.

### 3. `custom_components/homeclaw/agent_compat.py:159`

Update the legacy fallback map so the agent_compat shim picks a sensible model when nothing else is configured:

```python
"openrouter": "openai/gpt-4"  →  "openrouter": "tencent/hy3-preview:free"
```

## Files unchanged but verified relevant

- `custom_components/homeclaw/const.py` — `CONF_OPENROUTER_TOKEN`, `AI_PROVIDERS` already include `openrouter`.
- `custom_components/homeclaw/config_flow.py` — `PROVIDERS`, `TOKEN_FIELD_NAMES`, `TOKEN_LABELS` already include `openrouter`. `get_model_options_for_flow()` already appends `Custom...` because `allow_custom_model: true`.
- `custom_components/homeclaw/strings.json`, `translations/{en,de,es,ca}.json` — `openrouter_token` strings already exist.
- `custom_components/homeclaw/services.yaml` — `openrouter` already in the provider enum.
- `custom_components/homeclaw/__init__.py:39` — `openrouter_token` already in the secrets-strip list.
- Frontend (`ProviderSelector.svelte`, `ModelSelector.svelte`) — populated dynamically from `homeclaw/providers/config` WS response, no edits needed.

## Test plan

1. Reload the Home Assistant integration after the changes.
2. Open config flow → choose **OpenRouter** → paste an OpenRouter API key → confirm the model picker lists the 16 entries plus `Custom…`, with `tencent/hy3-preview:free` selected by default.
3. Open the chat UI → start a new session → confirm the provider/model selectors show OpenRouter / Tencent Hy3 Preview.
4. Send a plain text message → response streams correctly.
5. Send a tool-calling prompt ("turn on the living room light" or similar) → confirm:
   - LLM emits a tool call,
   - Home Assistant executes it (the device actually changes state),
   - the assistant's follow-up message acknowledges the action.
6. Switch model to `openai/gpt-oss-120b:free` in a new session → repeat step 5 to confirm a second model in the list works end-to-end.
7. Trigger a background task that uses `lightweight_model` (e.g. session-title generation after first message) → check logs to confirm `openai/gpt-oss-20b:free` was the model called.

## Risks and mitigations

- **Rate limits.** OpenRouter's free tier is ~20 req/min and 50/day without credits (1000/day with ≥$10 credits). Heavy voice users will see 429s. Mitigation: errors already flow through `_logger_for(self).error(...)` and surface to the UI as error chunks via the existing streaming path. No new code needed; user-visible behaviour is "this model is rate-limited, try another".
- **Preview / alpha models can be retired.** `tencent/hy3-preview:free` and `openrouter/owl-alpha` are explicitly preview/alpha. If they disappear, rollback is a single PR: change `DEFAULT_MODEL` and the `default: true` flag to `nvidia/nemotron-3-super-120b-a12b:free` (262k ctx, stable, second on the curated list).
- **List goes stale.** Models on the free tier rotate every ~1–2 months. Acceptable: a follow-up PR refreshes the JSON. If this becomes painful, the future work is dynamic fetching from `/api/v1/models` (out of scope here).
- **Privacy.** Some free providers train on prompts. Documented as a known property of the OpenRouter free tier — surface in the description field if needed in a future iteration.

## Sources

- OpenRouter Free Models collection: https://openrouter.ai/collections/free-models
- OpenRouter Models API (filtered for `pricing.prompt==0 && pricing.completion==0 && "tools" in supported_parameters`): https://openrouter.ai/api/v1/models
- OpenRouter SDK landing page: https://openrouter.ai/sdk
- OpenRouter Quickstart (Python recommended via OpenAI SDK with base_url override): https://openrouter.ai/docs/quickstart
