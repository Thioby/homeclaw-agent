# Discord Bugs - Follow-up List

Date: 2026-02-16

This file tracks bugs found during Discord channel rollout, so we can continue later.

## Open bugs

1. Pairing prompt spam after user is already paired
- Symptom: bot still sends "Discord pairing is required... confirm code ..." even after successful pairing.
- Impact: noisy UX, confusing state.
- Notes: likely stale runtime config and/or pairing gate logic not short-circuiting correctly.

2. Same inbound message processed twice in some cases
- Symptom: same `MESSAGE_CREATE id=...` appears multiple times in logs and can trigger duplicate actions.
- Impact: duplicate pairing prompts and duplicate side effects.
- Notes: we removed message-id masking and added gateway sequence dedupe, but real root cause still needs final verification in HA runtime.

3. Discord path not using user default provider/model from preferences
- Symptom: Discord chat can use first available provider instead of `default_provider` from user preferences.
- Impact: wrong model/provider, inconsistent behavior vs panel.
- Repro clue: provider chosen by `DiscordChannel._default_provider()` and stream path without explicit provider/model.

4. Mixed behavior on one inbound message (pairing text + normal LLM answer)
- Symptom: bot can send pairing prompt and regular answer for same user flow close in time.
- Impact: inconsistent routing and trust issues.
- Notes: suggests concurrent consumers or split decision path with different effective config/mapping.

## Fixed during this session (needs real HA re-check)

1. Blocking I/O warnings in event loop
- Fixed `open()` for Discord defaults by moving file read to executor.
- Fixed attachment file open in websocket chat history by moving binary read to executor.

2. Setup timeout warning from tracked startup task
- Discord gateway startup switched to background task pattern to avoid bootstrap timeout coupling.

3. Mapping for paired Discord user to HA user context
- Added/merged `user_mapping` support for channel config and fallback from legacy `external_user_mapping`.
- Pairing persist now writes mapping into channel-level config so user context can align with RAG/persona.

## Suggested next work order

1. Fix provider/model selection from user preferences in Discord flow.
2. Finalize true duplicate root cause (single active consumer + runtime logs with instance/session markers).
3. Harden pairing state logic to prevent prompts after confirmed mapping.
4. Add regression tests for "paired user never sees pairing prompt" and "single reply per inbound message".
