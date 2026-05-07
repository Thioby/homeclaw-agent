# OpenRouter Free Models with Tool Calling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace OpenRouter's stale paid-model list with the 16 curated "Free Models" from OpenRouter that all support tool calling, switch the default to `tencent/hy3-preview:free`, and route background tasks through the smaller `openai/gpt-oss-20b:free`.

**Architecture:** Pure data update plus a minimal `lightweight_model` override. `OpenRouterProvider` keeps inheriting from `OpenAIProvider` and using raw `aiohttp` via `BaseHTTPClient` — same pattern as every other provider in the project.

**Tech Stack:** Python 3.13+, Home Assistant custom component, `aiohttp`, pytest with `asyncio_mode = auto`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-06-openrouter-free-tooling-design.md`

---

## File Structure

Three files to modify, no new files:

- `custom_components/homeclaw/models_config.json` — replace `openrouter.models[]` (16 entries) and update `default`/`description`. Add `"lightweight": true` to `openai/gpt-oss-20b:free`.
- `custom_components/homeclaw/providers/openrouter.py` — change `DEFAULT_MODEL` and add `lightweight_model` property mirroring `gemini_oauth.py:125-129`.
- `custom_components/homeclaw/agent_compat.py:159` — update the legacy provider→model fallback map.

Tests to update / add:

- `tests/test_providers/test_openrouter.py` — update `test_build_payload_default_model` (expects `openai/gpt-4o` today), add `TestOpenRouterProviderLightweightModel`.

No frontend or i18n changes. The provider list is served by `homeclaw/providers/config` WS handler in `ws_handlers/models.py:73`, which reads from `models_config.json` directly. `ProviderSelector.svelte` and `ModelSelector.svelte` already render whatever the backend returns.

---

## Task 1: Update existing payload test to reflect new default model

**Files:**
- Modify: `tests/test_providers/test_openrouter.py:83-92`

- [ ] **Step 1: Edit the failing-default test**

Replace the `test_build_payload_default_model` body so it expects the new default. The model id is set in `Task 3` via `models_config.json` and `Task 4` via `DEFAULT_MODEL`; the test pins both ends of the contract.

```python
def test_build_payload_default_model(self, hass: HomeAssistant) -> None:
    """Test that default model is used when not specified."""
    config = {"token": "sk-or-test-key"}

    provider = OpenRouterProvider(hass, config)
    messages = [{"role": "user", "content": "Hello"}]
    payload = provider._build_payload(messages)

    assert payload["model"] == "tencent/hy3-preview:free"
    assert payload["messages"] == messages
```

- [ ] **Step 2: Run the test and confirm it fails**

```
pytest tests/test_providers/test_openrouter.py::TestOpenRouterProviderBuildPayload::test_build_payload_default_model -v
```

Expected: `FAIL` with `assert 'openai/gpt-4o' == 'tencent/hy3-preview:free'`. This proves the test is correctly wired before we change production code.

- [ ] **Step 3: Commit**

```bash
git add tests/test_providers/test_openrouter.py
git commit -m "update openrouter default model test"
```

---

## Task 2: Add test for OpenRouter `lightweight_model` property

**Files:**
- Modify: `tests/test_providers/test_openrouter.py` (append a new test class)

- [ ] **Step 1: Append new test class**

Add this class at the end of the file (after `TestOpenRouterProviderExtractResponse`). It pins the contract: `lightweight_model` returns the model tagged `"lightweight": true` in `models_config.json`.

```python
class TestOpenRouterProviderLightweightModel:
    """Tests for OpenRouter provider lightweight_model property."""

    def test_lightweight_model_returns_gpt_oss_20b(self, hass: HomeAssistant) -> None:
        """Lightweight model is the JSON-tagged free 20B model."""
        config = {"token": "sk-or-test-key"}

        provider = OpenRouterProvider(hass, config)

        assert provider.lightweight_model == "openai/gpt-oss-20b:free"
```

- [ ] **Step 2: Run the test and confirm it fails**

```
pytest tests/test_providers/test_openrouter.py::TestOpenRouterProviderLightweightModel -v
```

Expected: `FAIL`. Today `lightweight_model` is the base-class `None`, so the assertion `None == "openai/gpt-oss-20b:free"` fails. (If the JSON change in Task 3 lands first, the test still fails because the provider hasn't overridden the property yet.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_providers/test_openrouter.py
git commit -m "add openrouter lightweight model test"
```

---

## Task 3: Replace `openrouter` section in `models_config.json`

**Files:**
- Modify: `custom_components/homeclaw/models_config.json:193-248`

- [ ] **Step 1: Replace the `openrouter` block**

Open `custom_components/homeclaw/models_config.json`. Find the `"openrouter": { ... }` object (currently lines 193–248, ending before the comma that precedes `"groq":`). Replace the whole `"openrouter"` value with this exact block (keep the trailing comma — `"groq"` follows):

```json
  "openrouter": {
    "display_name": "OpenRouter",
    "description": "OpenRouter — free models with tool calling",
    "allow_custom_model": true,
    "models": [
      {
        "id": "tencent/hy3-preview:free",
        "name": "Tencent Hy3 Preview",
        "description": "Configurable reasoning, code generation, agentic workflows",
        "context_window": 262144,
        "default": true
      },
      {
        "id": "nvidia/nemotron-3-super-120b-a12b:free",
        "name": "NVIDIA Nemotron 3 Super",
        "description": "Multi-token prediction, tool calling",
        "context_window": 262144
      },
      {
        "id": "inclusionai/ling-2.6-1t:free",
        "name": "inclusionAI Ling 2.6 1T",
        "description": "Advanced coding, complex reasoning, agent workflows",
        "context_window": 262144
      },
      {
        "id": "openrouter/owl-alpha",
        "name": "OpenRouter Owl Alpha",
        "description": "Tool use, long-context tasks, code generation",
        "context_window": 1048576
      },
      {
        "id": "poolside/laguna-m.1:free",
        "name": "Poolside Laguna M.1",
        "description": "Tool calling, reasoning, software engineering focus",
        "context_window": 131072
      },
      {
        "id": "openai/gpt-oss-120b:free",
        "name": "OpenAI gpt-oss-120b",
        "description": "Configurable reasoning, tool use, function calling",
        "context_window": 131072
      },
      {
        "id": "z-ai/glm-4.5-air:free",
        "name": "Z.ai GLM 4.5 Air",
        "description": "Thinking/reasoning mode, tool use, hybrid inference",
        "context_window": 131072
      },
      {
        "id": "minimax/minimax-m2.5:free",
        "name": "MiniMax M2.5",
        "description": "Office productivity, code generation, multi-tool support",
        "context_window": 196608
      },
      {
        "id": "nvidia/nemotron-3-nano-30b-a3b:free",
        "name": "NVIDIA Nemotron 3 Nano 30B",
        "description": "Agentic AI systems, compact MoE design",
        "context_window": 256000
      },
      {
        "id": "poolside/laguna-xs.2:free",
        "name": "Poolside Laguna XS.2",
        "description": "Tool calling, reasoning, coding workflows",
        "context_window": 131072
      },
      {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "name": "NVIDIA Nemotron 3 Nano Omni",
        "description": "Multimodal (text, image, video, audio), reasoning",
        "context_window": 256000
      },
      {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B",
        "description": "Multimodal, thinking mode, function calling",
        "context_window": 262144
      },
      {
        "id": "nvidia/nemotron-nano-9b-v2:free",
        "name": "NVIDIA Nemotron Nano 9B V2",
        "description": "Reasoning traces, configurable reasoning",
        "context_window": 128000
      },
      {
        "id": "nvidia/nemotron-nano-12b-v2-vl:free",
        "name": "NVIDIA Nemotron Nano 12B V2 VL",
        "description": "Multimodal, OCR, chart reasoning",
        "context_window": 128000
      },
      {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Google Gemma 4 26B A4B",
        "description": "Multimodal, thinking mode, function calling",
        "context_window": 262144
      },
      {
        "id": "openai/gpt-oss-20b:free",
        "name": "OpenAI gpt-oss-20b",
        "description": "Function calling, tool use, structured outputs (small)",
        "context_window": 131072,
        "lightweight": true
      }
    ]
  },
```

Notes for the editor:
- Order matches the OpenRouter "Free Models" collection (https://openrouter.ai/collections/free-models), with one exception: `openai/gpt-oss-20b:free` is moved to the **end** so `get_lightweight_model("openrouter")` would still pick it via the "last entry" fallback even if the `"lightweight": true` tag is ever lost. Position-in-list does not affect UI ordering for the user — `ModelSelector` shows them as a list with `default: true` selected.
- Exactly one entry has `"default": true` (the first one).
- Exactly one entry has `"lightweight": true` (the last one).
- `allow_custom_model: true` stays so the user can paste any OpenRouter model id.

- [ ] **Step 2: Validate JSON parses**

```
python -c "import json; json.load(open('custom_components/homeclaw/models_config.json'))"
```

Expected: no output, exit code 0. If a `JSONDecodeError` prints, fix the trailing comma or quote and re-run.

- [ ] **Step 3: Sanity-check the data via the public helpers**

```
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'custom_components')
from homeclaw.models import get_models_for_provider, get_default_model, get_lightweight_model, get_allow_custom_model
ids = [m['id'] for m in get_models_for_provider('openrouter')]
assert len(ids) == 16, ids
assert get_default_model('openrouter') == 'tencent/hy3-preview:free'
assert get_lightweight_model('openrouter') == 'openai/gpt-oss-20b:free'
assert get_allow_custom_model('openrouter') is True
print('OK', len(ids), 'models')
"
```

Expected: `OK 16 models`. If an assertion fails, the JSON is correct but tagged wrong — fix `default` / `lightweight` flags and re-run.

- [ ] **Step 4: Commit**

```bash
git add custom_components/homeclaw/models_config.json
git commit -m "update openrouter models to free tier with tool calling"
```

---

## Task 4: Update `OpenRouterProvider` — default model and lightweight property

**Files:**
- Modify: `custom_components/homeclaw/providers/openrouter.py:23-24` and class body

- [ ] **Step 1: Replace the file contents**

Open `custom_components/homeclaw/providers/openrouter.py` and replace the **entire file** with:

```python
"""OpenRouter provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .openai import OpenAIProvider
from .registry import ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant  # noqa: F401


@ProviderRegistry.register("openrouter")
class OpenRouterProvider(OpenAIProvider):
    """OpenRouter API provider.

    OpenRouter provides access to multiple AI models through a unified,
    OpenAI-compatible API. Extends OpenAIProvider with custom headers
    and endpoint. Defaults target free models that support tool calling
    so that out-of-the-box use does not incur cost.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "tencent/hy3-preview:free"

    @property
    def api_url(self) -> str:
        """Return the OpenRouter API endpoint URL."""
        return self.API_URL

    @property
    def lightweight_model(self) -> str | None:
        """Return the cheapest/fastest model for background tasks.

        Reads from models_config.json (entry tagged lightweight: true).
        Falls back to the user-selected model if the JSON has no tag.
        """
        from ..models import get_lightweight_model

        return get_lightweight_model("openrouter") or self._model

    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for OpenRouter API requests."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://home-assistant.io",
            "X-Title": "Homeclaw",
        }
```

Differences from the old file:
- `DEFAULT_MODEL` is now `tencent/hy3-preview:free` (was `openai/gpt-4o`).
- New `lightweight_model` property mirrors `gemini_oauth.py:125-129`.
- Removed the unused `Any` import; `TYPE_CHECKING`-only `HomeAssistant` import is kept with `noqa: F401` because the old file had it.

- [ ] **Step 2: Run the OpenRouter unit tests**

```
pytest tests/test_providers/test_openrouter.py -v
```

Expected: all tests pass, including the two we updated/added in Tasks 1–2 (`test_build_payload_default_model` and `TestOpenRouterProviderLightweightModel::test_lightweight_model_returns_gpt_oss_20b`).

- [ ] **Step 3: Commit**

```bash
git add custom_components/homeclaw/providers/openrouter.py
git commit -m "switch openrouter default to free tencent hy3 and add lightweight model"
```

---

## Task 5: Update legacy fallback map in `agent_compat.py`

**Files:**
- Modify: `custom_components/homeclaw/agent_compat.py:159`

- [ ] **Step 1: Edit the mapping line**

Open `custom_components/homeclaw/agent_compat.py`, find line 159 inside the legacy provider→default-model dict. Change:

```python
"openrouter": "openai/gpt-4",
```

to:

```python
"openrouter": "tencent/hy3-preview:free",
```

Leave surrounding entries untouched.

- [ ] **Step 2: Run agent_compat tests**

```
pytest tests/test_agent_compat.py -v
```

Expected: all tests pass. (No existing assertion checks the openrouter mapping value, but this confirms nothing else broke.)

- [ ] **Step 3: Commit**

```bash
git add custom_components/homeclaw/agent_compat.py
git commit -m "update openrouter legacy default to free tencent hy3"
```

---

## Task 6: Final verification — full test suite and manual sanity check

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite**

```
pytest tests/ -q
```

Expected: all tests pass. Coverage is enforced ≥ 70 % by `pytest.ini`. If a previously-passing test now fails because it referenced `openai/gpt-4o` for the openrouter provider somewhere, fix the test (the contract has shifted). The grep for stale references has already been done; this step catches surprises.

- [ ] **Step 2: Grep for any remaining stale references**

```
grep -rn 'openai/gpt-4o' custom_components/homeclaw/ tests/ | grep -i openrouter
grep -rn 'openai/gpt-4"' custom_components/homeclaw/ tests/
```

Expected: empty output for both. If the second grep matches in `agent_compat.py`, the change in Task 5 was incomplete — re-apply it.

- [ ] **Step 3: Confirm the WS providers/config response carries the new list**

```
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'custom_components')
from homeclaw.models import get_models_for_provider, get_default_model
ms = get_models_for_provider('openrouter')
print(get_default_model('openrouter'))
for m in ms[:3]: print('-', m['id'], m['name'])
print('...', len(ms), 'total')
"
```

Expected output:
```
tencent/hy3-preview:free
- tencent/hy3-preview:free Tencent Hy3 Preview
- nvidia/nemotron-3-super-120b-a12b:free NVIDIA Nemotron 3 Super
- inclusionai/ling-2.6-1t:free inclusionAI Ling 2.6 1T
... 16 total
```

- [ ] **Step 4: Manual end-to-end check (recorded in PR description, not automated)**

Document the result of each in the eventual PR description. These cannot be unit-tested because they need a live HA instance and an OpenRouter API key.

1. Reload the integration in Home Assistant (via the deploy script or the HA UI).
2. Open config flow → choose **OpenRouter** → paste a real OpenRouter API key.
3. Confirm the model picker lists the 16 free models plus a `Custom...` row, with **Tencent Hy3 Preview** preselected.
4. Open the chat UI → start a new session → send "Hello".
5. Send "Turn on the light in <some configured room>" (or whatever HA tool-call prompt fits the user's setup) → confirm the LLM emits a tool call, the device state changes, and the assistant acknowledges.
6. Switch model in a new session to **OpenAI gpt-oss-120b** → repeat step 5.
7. Trigger a session-title generation (`ws_handlers/sessions.py:464` reads `provider.lightweight_model`) by sending the first message in a new session → check the HA log for a request to `openai/gpt-oss-20b:free`.

If any of those fail, file a follow-up issue rather than reverting; the data change can be tweaked in a small PR.

- [ ] **Step 5: No extra commit needed**

Verification only. Step 4 produces text for the PR description, not code.

---

## Done criteria

- All tasks above checked.
- `pytest tests/` passes with coverage ≥ 70 %.
- Both grep checks in Task 6 Step 2 return empty.
- The `homeclaw/providers/config` WS response (verifiable via Task 6 Step 3) lists 16 OpenRouter models with `tencent/hy3-preview:free` flagged default.
- Manual checklist in Task 6 Step 4 noted in the PR description.
