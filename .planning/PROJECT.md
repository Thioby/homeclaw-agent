# Xiaomi MiMo Provider + TTS for HomeClaw

## What This Is

Adding Xiaomi MiMo as a new AI provider in HomeClaw (chat completions) and a separate Home Assistant TTS platform entity powered by MiMo-V2-TTS. The chat provider handles text/reasoning/multimodal models via an OpenAI-compatible API, while the TTS platform integrates into HA's native TTS engine for voice synthesis with style control, dialects, and expressive speech.

## Core Value

Users can use Xiaomi MiMo models for both AI conversation (chat) and natural speech synthesis (TTS) within Home Assistant, with the TTS engine pluggable into any HA automation or voice pipeline.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Xiaomi chat provider registered in HomeClaw provider system
- [ ] Chat provider supports mimo-v2-flash, mimo-v2-pro, mimo-v2-omni models
- [ ] Chat provider extends OpenAI-compatible pattern (like Groq)
- [ ] Auth via `api-key` header to `https://api.xiaomimimo.com/v1`
- [ ] Tool/function calling support inherited from OpenAI provider
- [ ] Multimodal support for mimo-v2-omni (text + image input)
- [ ] Model config in models_config.json with context windows and defaults
- [ ] agent_compat.py integration (token mapping, model lookup)
- [ ] HA TTS platform entity using MiMo-V2-TTS model
- [ ] TTS supports built-in voices: mimo_default, default_zh, default_en
- [ ] TTS style control via `<style>` tags in text
- [ ] TTS audio output in WAV format (non-streaming) and PCM16 (streaming)
- [ ] TTS configurable via HA config flow or YAML

### Out of Scope

- Voice cloning — not supported by Xiaomi API yet
- OAuth authentication — Xiaomi uses simple API key auth only
- Singing synthesis integration — edge case, not needed for HA TTS
- Streaming TTS to HA media player in real-time — standard HA TTS returns audio files

## Context

- Xiaomi MiMo API launched March 18-19, 2026, currently free for limited time
- API is OpenAI-compatible at `https://api.xiaomimimo.com/v1`
- Auth uses `api-key: $KEY` header (also works with `Authorization: Bearer $KEY` via OpenAI SDK)
- TTS uses the **same chat completions endpoint** with an `audio` parameter, NOT a separate `/v1/audio/speech` endpoint
- TTS text must be in `assistant` role message (not `user`)
- TTS streaming uses pcm16 format at 24kHz mono
- OpenClaw project already has a basic Xiaomi chat provider (reference implementation)
- HomeClaw has established patterns: BaseHTTPClient, OpenAIProvider inheritance (Groq as template)
- HomeClaw providers auto-register via `@ProviderRegistry.register()` decorator

## Constraints

- **Tech stack**: Python, Home Assistant custom component, aiohttp for HTTP
- **API compatibility**: Must follow HomeClaw's AIProvider interface (get_response, supports_tools, etc.)
- **TTS platform**: Must implement HA's `tts.Provider` interface for native integration
- **Auth format**: Xiaomi uses `api-key` header (not standard Bearer), need to handle in _build_headers

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extend OpenAIProvider for chat | API is OpenAI-compatible, minimal code needed (like Groq) | — Pending |
| Separate TTS platform from chat provider | User wants TTS pluggable into HA TTS engine independently | — Pending |
| Use `api-key` header format | Xiaomi docs show this format in curl examples | — Pending |

---
*Last updated: 2026-03-20 after initialization*
