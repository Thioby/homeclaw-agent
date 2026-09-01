# Design: Grok SuperGrok OAuth provider

**Date**: 2026-09-01
**Status**: Approved
**Target**: `custom_components/homeclaw/`

## Problem

HomeClaw can add Anthropic via Claude Pro/Max subscription OAuth, but Grok only exists as Groq (unrelated). SuperGrok / X Premium+ subscribers cannot add Grok as an agent without an `XAI_API_KEY`.

## Goal

Add a single new config-flow option: **Grok (SuperGrok / X Premium+)**. Login is subscription OAuth. No API-key path in this work.

## Out of scope

- `xai` API-key provider (`api.x.ai` + `XAI_API_KEY`)
- Loopback PKCE (`127.0.0.1:56121`) — HA OS cannot receive that callback
- OpenAI Responses adapter
- Image / video / TTS / `x_search` via the same token
- Reading `~/.grok/auth.json` from the HA host

## Auth is not Anthropic

| | Anthropic Pro/Max | Grok SuperGrok |
|---|---|---|
| Grant | Authorization code + PKCE, user pastes `code` | RFC 8628 device code, HA polls |
| Issuer | `platform.claude.com` / `claude.ai` | `https://auth.x.ai` |
| Inference | `api.anthropic.com` | `https://cli-chat-proxy.grok.com/v1` |
| Token body | JSON | `application/x-www-form-urlencoded` |
| Refresh | same refresh token (sometimes rotated) | **always rotated** — persist immediately |
| `api.x.ai` | n/a | rejects this bearer with 402/403 |

Public Grok CLI client id: `b1a00492-073a-47ea-816f-4c329264a828`.

Device: `POST https://auth.x.ai/oauth2/device/code`
Token: `POST https://auth.x.ai/oauth2/token`
Grant: `urn:ietf:params:oauth:grant-type:device_code`
Scopes (match official CLI JWT): `openid profile email offline_access grok-cli:access api:access conversations:read conversations:write workspaces:read workspaces:write`

## Config flow

1. User picks `grok_oauth` from the provider list.
2. HA requests a device code and shows `verification_uri` + `user_code` (or `verification_uri_complete`).
3. User opens that URL on any device, signs in, approves.
4. HA polls the token endpoint (`authorization_pending` keep going, `slow_down` +5s, `access_denied` / `expired_token` / timeout fail).
5. Success stores config entry:

```json
{
  "ai_provider": "grok_oauth",
  "grok_oauth": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": 1770000000.0
  }
}
```

Reauth uses the same device-code flow. No paste-code field.

Polling UX: `async_show_progress` while the poll loop runs, so the user does not have to click Submit at the exact moment of approval.

## Provider

Id: `grok_oauth` (must not collide with `groq`).

Layout:

```
providers/grok_oauth/
  __init__.py      re-exports
  constants.py     URLs, client id, scopes, CLI headers
  auth.py          device code, poll, refresh, InflightRefreshGate
  provider.py      HA glue + OpenAI chat completions
```

`provider.py` is the only HA-aware module.

Inference:

- URL: `https://cli-chat-proxy.grok.com/v1/chat/completions`
- Always `stream: true`. `get_response()` collects the stream.
- Headers:
  - `Authorization: Bearer <access_token>`
  - `X-XAI-Token-Auth: xai-grok-cli`
  - `x-grok-client-identifier: grok-shell`
  - `x-grok-client-version: 1.0.13`
  - `x-grok-model-override: <model>`
- Do not send OpenAI `reasoning_effort`.
- Token refresh: 5-minute skew, single-flight gate, persist rotated refresh token before the next call.
- Reuse `OpenAICompatAdapter` / `OpenAIProvider` streaming path.

CLI catalog marks `api_backend: responses`. The same proxy documents Chat Completions (`grok-build` README curl). We use Chat Completions because HomeClaw already has that adapter. If live inference fails on `/chat/completions`, switch that one URL to `/responses` in a follow-up — not in this spec.

## Models

Pinned from live `grok models` on SuperGrok (CLI 1.0.13, origin `cli-chat-proxy.grok.com/v1/models`):

| id | name | context | role |
|---|---|---|---|
| `grok-4.6` | Grok 4.6 | 500000 | default |
| `grok-4.5` | Grok 4.5 | 500000 | previous + lightweight |

`allow_custom_model: true` so a user can type `grok-build-0.1` / `grok-4-fast` if the proxy accepts them. Do not list those by default — the subscription picker does not.

UI cost: 0 for `grok_oauth` (same as `anthropic_oauth`).

## Errors

| Signal | Action |
|---|---|
| `invalid_grant` / 401 on refresh | permanent → HA reauth (device code again) |
| 402 / 403 on inference | not reauth; tell the user the SuperGrok seat is not entitled to Grok Build |
| 426 | client version too old; bump `x-grok-client-version` |
| device `expired_token` / timeout / denied | restart device-code step |

Never log access or refresh tokens.

## Wiring

- `const.py`: add `grok_oauth` to `AI_PROVIDERS`, `CONF_GROK_OAUTH`
- `config_flow.py`: provider label, device-code steps, reauth
- `strings.json` + `translations/{en,de,es,ca}.json`
- `models_config.json`: `grok_oauth` catalog
- `providers/__init__.py`: import to register
- `provider.service.ts`: `isOAuthZeroCostProvider` includes `grok_oauth`
- Python `is_oauth_zero_cost_provider` includes `grok_oauth`
- `agent_compat` / default-model lookups pick up `grok_oauth` via registry + models config (no special fallback)

## Testing

Unit tests only (no live xAI):

- device-code request/parse
- poll: pending → slow_down → success; denied; expired
- refresh rotation + persist; concurrent callers share one refresh
- provider headers and `stream: true`
- config flow create + reauth (aiohttp mocked)

## Success

User adds HomeClaw → Grok (SuperGrok / X Premium+) → opens the shown URL → approves → chats with `grok-4.6` billed to the subscription, not an API key.
