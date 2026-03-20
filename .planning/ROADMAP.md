# Roadmap: Xiaomi MiMo Provider + TTS for HomeClaw

## Overview

Two-phase delivery: first establish the Xiaomi MiMo chat provider by extending the existing OpenAI-compatible pattern (like Groq), then build the TTS platform entity on top of the same API endpoint. The chat provider is prerequisite since TTS shares authentication, endpoint, and HTTP plumbing.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Xiaomi Chat Provider** - Register MiMo as an OpenAI-compatible provider with auth, models, and agent integration
- [ ] **Phase 2: MiMo TTS Platform** - HA TTS entity using MiMo-V2-TTS via the chat completions endpoint

## Phase Details

### Phase 1: Xiaomi Chat Provider
**Goal**: Users can select Xiaomi MiMo as a conversation provider in HomeClaw and chat with mimo-v2-flash, mimo-v2-pro, or mimo-v2-omni models
**Depends on**: Nothing (first phase)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, CHAT-10
**Success Criteria** (what must be TRUE):
  1. User can select "xiaomi" as a provider in HomeClaw and send a chat message that returns a response from mimo-v2-flash
  2. User can switch between mimo-v2-flash, mimo-v2-pro, and mimo-v2-omni models via configuration
  3. User can send an image alongside text when using mimo-v2-omni and receive a multimodal response
  4. User can invoke HA tool/function calls through the Xiaomi provider (inherited OpenAI tool calling works)
  5. Provider appears in agent_compat model lookup and token mapping resolves correctly
**Plans:** 1 plan

Plans:
- [ ] 01-01-PLAN.md — Xiaomi provider implementation, integration wiring, and test suite

### Phase 2: MiMo TTS Platform
**Goal**: Users can use MiMo-V2-TTS as a Home Assistant TTS engine for voice synthesis in automations and voice pipelines
**Depends on**: Phase 1
**Requirements**: TTS-01, TTS-02, TTS-03, TTS-04, TTS-05
**Success Criteria** (what must be TRUE):
  1. MiMo TTS appears as a selectable TTS platform in Home Assistant
  2. User can type text and hear synthesized speech returned as WAV audio
  3. User can configure the TTS platform (API key, voice) via HA config flow or YAML
  4. TTS works in HA automations (e.g., `tts.speak` service call produces audible output)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Xiaomi Chat Provider | 0/1 | Planned | - |
| 2. MiMo TTS Platform | 0/? | Not started | - |
