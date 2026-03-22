---
phase: 01-xiaomi-chat-provider
plan: 01
subsystem: providers
tags: [xiaomi, mimo, openai-compat, provider-registry, api-key-auth]

# Dependency graph
requires: []
provides:
  - XiaomiProvider registered as 'xiaomi' in ProviderRegistry
  - 3 Xiaomi MiMo models in models_config.json (flash/pro/omni)
  - Config flow integration (PROVIDERS, TOKEN_FIELD_NAMES, TOKEN_LABELS)
  - Agent compat token and default model mappings
  - 21-test comprehensive suite covering CHAT-01 to CHAT-10
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OpenAI-compatible provider with api-key header override (not Bearer)"
    - "Provider module mirroring groq.py structure"

key-files:
  created:
    - custom_components/homeclaw/providers/xiaomi.py
    - tests/test_providers/test_xiaomi.py
  modified:
    - custom_components/homeclaw/providers/__init__.py
    - custom_components/homeclaw/models_config.json
    - custom_components/homeclaw/config_flow.py
    - custom_components/homeclaw/agent_compat.py

key-decisions:
  - "Use api-key header format per Xiaomi docs (not Authorization: Bearer)"
  - "Fix _build_provider_config token_keys lookup to check provider name first, then base_provider"

patterns-established:
  - "OpenAI-compatible provider pattern: extend OpenAIProvider, override API_URL, DEFAULT_MODEL, api_url property, _build_headers"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, CHAT-10]

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 1 Plan 1: Xiaomi Chat Provider Summary

**Xiaomi MiMo provider with api-key auth, 3 models (flash/pro/omni), full config flow and agent compat wiring, 21-test suite covering CHAT-01 to CHAT-10**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-20T12:30:37Z
- **Completed:** 2026-03-20T12:38:33Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- XiaomiProvider registered and functional with api-key auth header format (not Bearer)
- All 10 CHAT requirements (CHAT-01 through CHAT-10) have passing test coverage (21 tests)
- Full test suite green with no regressions (2133 passed, 1 skipped)
- Provider selectable in config flow, agent_compat correctly maps token and default model
- models_config.json has 3 Xiaomi models with accurate context windows (flash=262144, pro=1048576, omni=262144)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Xiaomi provider and wire all integration points**
   - `9b0161e` (test: TDD RED - failing tests for provider)
   - `14c0ffa` (feat: provider implementation and wiring - TDD GREEN)
2. **Task 2: Create comprehensive test suite for Xiaomi provider**
   - `739b94d` (test: 21 tests covering CHAT-01 to CHAT-10)

## Files Created/Modified
- `custom_components/homeclaw/providers/xiaomi.py` - XiaomiProvider class with api-key auth
- `custom_components/homeclaw/providers/__init__.py` - Import trigger for xiaomi module
- `custom_components/homeclaw/models_config.json` - 3 Xiaomi MiMo model definitions
- `custom_components/homeclaw/config_flow.py` - PROVIDERS, TOKEN_FIELD_NAMES, TOKEN_LABELS dicts
- `custom_components/homeclaw/agent_compat.py` - token_keys and defaults mappings + token lookup fix
- `tests/test_providers/test_xiaomi.py` - 21 comprehensive tests

## Decisions Made
- Used api-key header format per Xiaomi curl documentation (not Authorization: Bearer)
- Fixed _build_provider_config token_keys lookup to prioritize provider name over base_provider name

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed token_keys lookup in _build_provider_config**
- **Found during:** Task 2 (TestXiaomiAgentCompat.test_token_key_mapping)
- **Issue:** `_build_provider_config` looked up token key using `base_provider` (via `_get_base_provider_name()`), which returned "openai" for non-OAuth providers like "xiaomi". This caused the config to look for "openai_token" instead of "xiaomi_token".
- **Fix:** Changed lookup to check `provider` first, then `base_provider`: `token_keys.get(provider, token_keys.get(base_provider, f"{base_provider}_token"))`
- **Files modified:** custom_components/homeclaw/agent_compat.py
- **Verification:** test_token_key_mapping passes, full suite passes
- **Committed in:** 739b94d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was necessary for correct token resolution for all non-OpenAI, non-OAuth providers. Pre-existing issue exposed by new provider.

## Issues Encountered
None beyond the auto-fixed bug above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Xiaomi chat provider is fully integrated and ready for use
- Users can select "Xiaomi MiMo" in the config flow, enter their API key, and chat
- Phase 2 (Xiaomi TTS) can proceed independently

## Self-Check: PASSED

All files verified present, all commit hashes confirmed in git log.

---
*Phase: 01-xiaomi-chat-provider*
*Completed: 2026-03-20*
