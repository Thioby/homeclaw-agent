# Requirements: Xiaomi MiMo Provider + TTS for HomeClaw

**Defined:** 2026-03-20
**Core Value:** Users can use Xiaomi MiMo models for AI conversation and speech synthesis within Home Assistant

## v1 Requirements

### Chat Provider

- [x] **CHAT-01**: Xiaomi provider registered via `@ProviderRegistry.register("xiaomi")`
- [x] **CHAT-02**: Provider extends `OpenAIProvider` with overridden `api_url`, `DEFAULT_MODEL`, `_build_headers`
- [x] **CHAT-03**: API endpoint set to `https://api.xiaomimimo.com/v1/chat/completions`
- [x] **CHAT-04**: Auth uses `api-key` header format from config token
- [x] **CHAT-05**: Default model is `mimo-v2-flash`
- [x] **CHAT-06**: Model config in `models_config.json` with mimo-v2-flash (262K ctx), mimo-v2-pro (1M ctx), mimo-v2-omni (262K ctx)
- [x] **CHAT-07**: agent_compat.py maps `xiaomi_token` config key and model lookup
- [x] **CHAT-08**: Provider imported in `providers/__init__.py` for auto-registration
- [x] **CHAT-09**: Multimodal image support for mimo-v2-omni (inherited from OpenAIProvider)
- [x] **CHAT-10**: Tool/function calling support (inherited from OpenAIProvider)

### TTS Platform

- [ ] **TTS-01**: HA TTS platform entity implementing `tts.Provider` interface
- [ ] **TTS-02**: TTS calls MiMo-V2-TTS via chat completions endpoint with `audio` parameter
- [ ] **TTS-03**: Text to synthesize placed in assistant role message
- [ ] **TTS-04**: Returns WAV audio data decoded from base64 response
- [ ] **TTS-05**: Configurable via HA config (API key, voice selection)

## v2 Requirements

### TTS Enhancements

- **TTS-V2-01**: Style control via `<style>` tags in text
- **TTS-V2-02**: Fine-grained audio tag control (emotions, breaths, pauses)
- **TTS-V2-03**: Voice selection between mimo_default, default_zh, default_en
- **TTS-V2-04**: Streaming TTS with pcm16 format at 24kHz

### Chat Enhancements

- **CHAT-V2-01**: Lightweight model designation (mimo-v2-flash for background tasks)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Voice cloning | Not supported by Xiaomi API |
| OAuth authentication | Xiaomi uses simple API key auth only |
| Singing synthesis | Edge case, not needed for HA TTS |
| Streaming TTS to HA media player | Standard HA TTS returns audio files |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CHAT-01 | Phase 1 | Complete |
| CHAT-02 | Phase 1 | Complete |
| CHAT-03 | Phase 1 | Complete |
| CHAT-04 | Phase 1 | Complete |
| CHAT-05 | Phase 1 | Complete |
| CHAT-06 | Phase 1 | Complete |
| CHAT-07 | Phase 1 | Complete |
| CHAT-08 | Phase 1 | Complete |
| CHAT-09 | Phase 1 | Complete |
| CHAT-10 | Phase 1 | Complete |
| TTS-01 | Phase 2 | Pending |
| TTS-02 | Phase 2 | Pending |
| TTS-03 | Phase 2 | Pending |
| TTS-04 | Phase 2 | Pending |
| TTS-05 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after initial definition*
