# Known Bugs — To Fix

## Bug 2: Tool calling breaks in longer conversations    | FIXED

**Status:** Fixed (across commits b472a86, 98a2d9a, 8df1506, 6ecc1a2)

**Root causes found and fixed:**
1. **Compaction destroyed tool call/result pairs** — AI-summarization during the tool
   loop removed structured `assistant(tool_call)` → `function(result)` pairs, causing
   the model to re-issue the same tool calls ("Gemini loop bug").
   **Fix:** `_recompact_if_needed()` replaced with progressive tool result truncation
   (2000→1000→500→200 chars) that never removes messages — only shortens content.
   (commit `6ecc1a2`)
2. **Token budget exhaustion / race condition** — `max_iterations` was too low (10) and
   was shared mutable state on `QueryProcessor`, causing concurrent calls to interfere.
   **Fix:** raised to 20 (agent) / 25 (scheduler), now passed per-call via kwargs.
   (commit `6ecc1a2`)
3. **Unified tool-call encoding** — provider-specific tool-call formats caused ID
   mismatches and empty-args loops across Anthropic/Gemini/OpenAI.
   **Fix:** `tool_call_codec.py` provides canonical encoding/decoding; pre-execution
   argument validation added to `tool_executor.py`. (commit `98a2d9a`)
4. **Streaming tool-call edge cases** — Anthropic/Gemini streaming could lose tool calls
   due to incomplete chunk assembly.
   **Fix:** stabilized streaming chunk handling and tool-call ID propagation.
   (commits `b472a86`, `8df1506`)

---

## Bug 3: YAML Config Merger not working correctly    | FIXED

**Status:** Fixed (2026-02-17)

**Root causes found and fixed:**
1. **`_remove_yaml_section` corrupted YAML with anchors/aliases** — removing a section
   that defined `&anchor` orphaned `*alias` references elsewhere, making the file
   unparseable. **Fix:** anchor-safety check raises `ValueError` before removal.
2. **`dashboard_manager._update_configuration_yaml` was a "wild" writer** — no lock,
   no backup, no atomic write, f-string YAML injection, naive string matching.
   **Fix:** complete rewrite using shared `yaml_writer` utilities (lock, backup,
   `yaml.safe_dump`, `atomic_write_file`, comment-aware key detection).
3. **`!include_dir_*` tag type was lost** — all variants mapped to `!include`.
   **Fix:** `IncludeTag` now stores `.tag` field preserving the exact variant.
4. **Duplicated YAML utilities** — safety code was trapped in `integration_manager.py`.
   **Fix:** extracted to shared `utils/yaml_writer.py` module.

**Files changed:**
- `custom_components/homeclaw/utils/yaml_writer.py` — new shared module (268 -> 393 lines)
- `custom_components/homeclaw/tools/integration_manager.py` — refactored to use yaml_writer (885 -> 643 lines)
- `custom_components/homeclaw/managers/dashboard_manager.py` — fixed _update_configuration_yaml (463 -> 533 lines)
- `tests/test_integration_manager.py` — +10 tests (anchor safety, tag preservation)
- `tests/test_managers/test_dashboard_manager.py` — +5 tests (_update_configuration_yaml)

**Test results:** 117/117 passed (79 existing + 23 existing dashboard + 15 new)
