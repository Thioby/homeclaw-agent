# Design: Port opencode-anthropic-auth v1.8.0 to HomeClaw

**Date**: 2026-05-05
**Status**: Approved (sections 1–8)
**Source**: `/Users/anowak/Projects/homeAssistant/opencode-anthropic-auth` v1.8.0 (TypeScript, MIT, © Ex Machina)
**Target**: `/Users/anowak/Projects/homeAssistant/ai_agent_ha/custom_components/homeclaw/` (Python 3.12+)

## Problem

HomeClaw's current Anthropic OAuth implementation is a Python port of opencode-anthropic-auth v0.0.13 (Jan 2026). Anthropic has since deployed a server-side classifier that detects third-party agent CLIs and returns HTTP 400 disguised as `"You're out of extra usage."` Mitigations have evolved over 8 months in the upstream plugin (now v1.8.0, May 2026). HomeClaw is missing those mitigations and will fail or be flagged in production.

## Goal

Reach feature parity with opencode-anthropic-auth v1.8.0, plus HomeClaw-specific adaptations:
- Pass Anthropic's server-side classifier (no 400 errors)
- Robust token refresh under concurrency
- Optional second OAuth method that mints a permanent API key (Console plan)

## Scope (full port — all tiers)

**Tier 1 — classifier mitigations**
- (a) URL migration: `console.anthropic.com` → `platform.claude.com` (token, callback, authorize-console)
- (b) OAuth scopes: 3 → 6 (`user:sessions:claude_code`, `user:mcp_servers`, `user:file_upload` added)
- (c) User-Agent: `claude-cli/2.1.87 (external, cli)` (was 2.1.2)
- (d) CCH (content-consistency-hash) billing header — SHA-256 with salt `59cf53e54c78`, inserted as a system text block
- (e) System prompt sanitization: identity swap, anchor-based paragraph removal, inline phrase rewrites (incl. critical `"Here is some useful information about the environment you are running in:"` → `"Environment context you are running in:"`)

**Tier 2 — robustness**
- (f) Inflight refresh promise (coalesces concurrent refreshes)
- (g) Network retry with exponential backoff (ECONNRESET / ECONNREFUSED / timeouts; 5xx)
- (h) Tool name namespacing: `mcp__homeclaw__<name>` (double-underscore convention from openclaw / Claude CLI MCP)
- Re-read refresh token from storage per refresh attempt (prevents stale-snapshot races)

**Tier 3 — optional**
- (i) Cost zeroing in UI for `anthropic_oauth` provider (Pro/Max subscription is unlimited)
- (j) `ANTHROPIC_BASE_URL` + `ANTHROPIC_INSECURE` env override for proxies/dev
- (k) "Create an API Key" OAuth method — exchanges Console-mode access token for a permanent API key

## Out of scope

- Adapter changes (`providers/adapters/anthropic_adapter.py`) — kept as-is
- Cost data in `models_config.json` — kept; zeroing applied only at UI render time
- Regular `anthropic.py` provider (API-key only) — kept
- Migration fallback to old endpoint — hard cutover; existing reauth flow handles failure

## Architecture

### Subpackage layout

```
custom_components/homeclaw/
├── oauth.py                          ← DELETED (content moves to anthropic_oauth/auth.py)
├── providers/
│   ├── anthropic_oauth.py            ← DELETED (content moves to anthropic_oauth/provider.py)
│   └── anthropic_oauth/              ← NEW subpackage
│       ├── __init__.py               (re-exports public API)
│       ├── constants.py              (URLs, scopes, salts, replacement rules)
│       ├── pkce.py                   (PKCE generation)
│       ├── cch.py                    (billing header SHA-256 helpers)
│       ├── auth.py                   (authorize URL, exchange, refresh, gate)
│       ├── transform.py              (sanitization, headers, tool prefix, URL rewrite)
│       └── provider.py               (AnthropicOAuthProvider — orchestration)
└── config_flow.py                    ← UPDATED (Create API Key step)
```

### Dependency graph

```
constants ← (no deps)
pkce      ← (no deps)
cch       ← constants
auth      ← constants, pkce
transform ← constants, cch
provider  ← constants, auth, transform, ../adapters/anthropic_adapter
__init__  ← provider, auth (public API surface)
```

### HA boundary

Only `provider.py` knows Home Assistant (`ConfigEntry`, `hass`). All other modules are pure Python — testable without HA fixtures. `auth.py` uses `aiohttp` but no HA.

## Module designs

### constants.py

Pure constants, ported 1:1 from `src/constants.ts` with HomeClaw-specific tool prefix.

```python
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URLS = {
    "console": "https://platform.claude.com/oauth/authorize",
    "max":     "https://claude.ai/oauth/authorize",
}
CODE_CALLBACK_URL = "https://platform.claude.com/oauth/code/callback"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CREATE_API_KEY_URL = "https://api.anthropic.com/api/oauth/claude_cli/create_api_key"

OAUTH_SCOPES = (
    "org:create_api_key", "user:profile", "user:inference",
    "user:sessions:claude_code", "user:mcp_servers", "user:file_upload",
)

TOOL_PREFIX_NAMESPACE = "homeclaw"
TOOL_PREFIX = f"mcp__{TOOL_PREFIX_NAMESPACE}__"      # mcp__homeclaw__

REQUIRED_BETAS = ("oauth-2025-04-20", "interleaved-thinking-2025-05-14")

OPENCODE_IDENTITY_PREFIX = "You are OpenCode"
CLAUDE_CODE_IDENTITY = "You are a Claude agent, built on Anthropic's Claude Agent SDK."

CCH_SALT = "59cf53e54c78"
CCH_POSITIONS = (4, 7, 20)
CLAUDE_CODE_VERSION = "2.1.87"
CLAUDE_CODE_ENTRYPOINT = "sdk-cli"
USER_AGENT = "claude-cli/2.1.87 (external, cli)"

PARAGRAPH_REMOVAL_ANCHORS = ("github.com/anomalyco/opencode", "opencode.ai/docs")
TEXT_REPLACEMENTS = (
    ("if OpenCode honestly", "if the assistant honestly"),
    ("Here is some useful information about the environment you are running in:",
     "Environment context you are running in:"),
)

REFRESH_MAX_RETRIES = 2
REFRESH_BASE_DELAY_S = 0.5
```

### pkce.py

```python
@dataclass(frozen=True, slots=True)
class PKCEPair:
    verifier: str
    challenge: str
    method: str = "S256"

def generate_pkce() -> PKCEPair:
    raw = secrets.token_bytes(64)
    verifier = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return PKCEPair(verifier=verifier, challenge=challenge)
```

### cch.py

```python
def extract_first_user_message_text(messages) -> str: ...    # find first role=user, first text block
def compute_cch(text) -> str: ...                            # sha256(text)[:5]
def compute_version_suffix(text, version=CLAUDE_CODE_VERSION) -> str:
    chars = "".join(text[i] if i < len(text) else "0" for i in CCH_POSITIONS)
    return sha256(f"{CCH_SALT}{chars}{version}")[:3]
def build_billing_header_value(messages, *, version=..., entrypoint=CLAUDE_CODE_ENTRYPOINT) -> str:
    # "x-anthropic-billing-header: cc_version={V}.{suffix}; cc_entrypoint={E}; cch={hash};"
```

Edge cases (covered by tests):
- Empty messages → empty text → deterministic `'0'`-padded sample
- First user message has list content with image+text → first text block wins
- Text shorter than 4/7/20 → `'0'` fallback per missing position

### auth.py

Public API:
- `authorize(mode: AuthMode = "max") -> tuple[AuthorizationRequest, PKCEPair]`
- `parse_callback_input(raw: str) -> tuple[str, str] | None` — handles full URL, `code#state`, bare query string
- `exchange_code(session, callback_input, verifier, *, expected_state=None) -> TokenSet` — raises `OAuthRefreshError(is_permanent=True)` on parse/state/HTTP failure
- `refresh_with_retry(session, read_refresh_token: callable) -> TokenSet` — `read_refresh_token` is re-called per attempt to pick up rotated tokens
- `class InflightRefreshGate` — coalesces concurrent refreshes onto a single in-flight task
- `create_api_key(session, access_token) -> str` — Console-flow API key minting
- `class OAuthRefreshError(Exception)` with `is_permanent: bool` attribute
- `@dataclass(frozen=True, slots=True) class TokenSet(access_token, refresh_token, expires_at)`

Token endpoint headers mirror axios (used by Claude CLI):
```
Content-Type: application/json
Accept: application/json, text/plain, */*
User-Agent: axios/1.13.6
```

Network retry: 2 retries with `0.5s, 1.0s` backoff. Retry on `aiohttp.ClientConnectionError`, `ServerDisconnectedError`, `ClientPayloadError`, `asyncio.TimeoutError`, and HTTP 5xx. Non-retryable: `invalid_grant` (raises permanent), other 4xx (raises non-permanent then exhausts).

### transform.py

Public API:
- `prefix_tool_name(name) -> str` / `unprefix_tool_name(name) -> str` (idempotent)
- `prefix_tool_names_in_payload(payload)` — mutates `tools[].name` and `messages[].content[].name` for `tool_use` blocks
- `unprefix_tool_names_in_event(event)` — mutates SSE event `content_block.name` if `tool_use`
- `unprefix_tool_names_in_response(data)` — mutates non-streaming `content[].name` for `tool_use`
- `sanitize_system_text(text) -> str` — three-phase pipeline (identity drop, anchor drop, inline replacements)
- `prepend_claude_code_identity(system) -> list[block]` — handles None / str / dict / list inputs; idempotent
- `merge_beta_headers(existing) -> str` — deduplicates with required betas first
- `build_oauth_headers(access_token, *, extra=None) -> dict[str, str]` — drops x-api-key from extra; sets authorization, beta, user-agent, version, content-type
- `_resolve_base_url() -> str | None` — env-driven origin override; rejects non-http(s), userinfo, malformed
- `is_tls_insecure() -> bool` — only when ANTHROPIC_BASE_URL set AND ANTHROPIC_INSECURE in {"1", "true"}
- `rewrite_url(url) -> str` — applies base URL override; adds `?beta=true` to /v1/messages if missing
- `transform_request_payload(payload) -> dict` — orchestrates: build billing header from first user message, sanitize+prepend identity, prepend billing block, prefix tool names

In-place mutation by sub-helpers (Pythonic, like `list.sort()`); top-level `transform_request_payload` returns the dict for chaining.

We do NOT port `mergeHeaders(input, init)` (TS-specific Headers vs RequestInit duality) nor `createStrippedStream` (raw-byte regex risks chunk boundary splits). Stream stripping is done at parsed-event level instead.

### provider.py

Replaces existing `providers/anthropic_oauth.py`. Slim — delegates to modules above.

```python
@ProviderRegistry.register("anthropic_oauth")
class AnthropicOAuthProvider(AIProvider):
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 8192

    def __init__(self, hass, config):
        ...
        self._refresh_gate = InflightRefreshGate()
        self.adapter = AnthropicAdapter()

    @property
    def supports_tools(self) -> bool: return True

    # Token management
    def _read_oauth_data(self) -> dict: ...           # always reads fresh from config_entry
    async def _read_refresh_token(self) -> str: ...   # callback for InflightRefreshGate
    def _persist_tokens(self, access, refresh, expires_at): ...   # async_update_entry
    def _trigger_reauth(self): ...
    async def _get_valid_access_token(self) -> str:   # 5-min buffer; gate.refresh on miss

    # Request execution
    def _build_payload(self, messages, *, stream, tools) -> dict   # adapter + transform_request_payload
    def _build_session(self) -> aiohttp.ClientSession              # honors is_tls_insecure
    async def get_response(self, messages, **kwargs) -> str
    async def get_response_stream(self, messages, **kwargs)
```

Key behaviors:
- No `_oauth_data` instance state — every call re-reads `config_entry.data`
- `_persist_tokens` writes immediately after refresh (Anthropic rotates refresh tokens)
- `unprefix_tool_names_in_event` runs before `adapter.extract_stream_events` (adapter sees clean names)
- `is_tls_insecure() == True` → connector with `ssl=False`

### __init__.py (public API)

```python
from .auth import AuthorizationRequest, OAuthRefreshError, TokenSet, authorize, create_api_key, exchange_code
from .provider import AnthropicOAuthProvider

__all__ = ["AnthropicOAuthProvider", "AuthorizationRequest", "OAuthRefreshError",
           "TokenSet", "authorize", "create_api_key", "exchange_code"]

def is_oauth_zero_cost_provider(provider_name: str) -> bool:
    return provider_name == "anthropic_oauth"
```

## Config flow changes (`config_flow.py`)

Adds a method-selection step in front of OAuth:

```
[Add Anthropic provider]
  ├─ "Manual API key"           → existing async_step_anthropic
  └─ "OAuth"                    → NEW async_step_anthropic_method
       ├─ "Claude Pro/Max"      → async_step_anthropic_oauth (mode="max", existing)
       └─ "Generate API key"    → NEW async_step_anthropic_create_key (mode="console")
```

`async_step_anthropic_create_key` performs OAuth (mode=console), then calls `create_api_key()` to mint a permanent key, and stores the result as a regular `anthropic` provider entry (not `anthropic_oauth`). User gets a permanent key without OAuth refresh thereafter.

`async_step_anthropic_oauth` keeps the same data shape (`config_entry.data["anthropic_oauth"]`) — no migration needed for existing entries beyond what URL/scope changes imply (handled transparently via reauth on first refresh failure).

## Frontend cost zeroing (Tier 3.i)

Single point of change in the cost calculation service:

```typescript
import { isOAuthZeroCostProvider } from './provider.service';
export function getModelCost(provider: string, model: string): Cost {
  if (isOAuthZeroCostProvider(provider)) return zeroCost();
  return modelsConfig.cost[provider][model];
}
```

`models_config.json` retains official per-token costs (single source of truth for what Anthropic charges); zeroing is a UI-time decision based on provider type.

## Testing

Test layout mirrors source layout. Old `tests/test_providers/test_anthropic_oauth.py` is deleted entirely.

```
tests/test_providers/test_anthropic_oauth/
├── __init__.py
├── test_constants.py      (~10 tests — sanity checks on values)
├── test_pkce.py           (~5 tests)
├── test_cch.py            (~15 tests — including critical edge cases)
├── test_auth.py           (~25 tests — incl. InflightRefreshGate concurrency)
├── test_transform.py      (~30 tests — sanitization, headers, URL, payload)
└── test_provider.py       (~20 tests — integration, mocked aiohttp + ConfigEntry)
```

Total: ~105 tests.

Critical coverage:
- `compute_cch` and `compute_version_suffix` against pinned reference inputs (deterministic)
- `sanitize_system_text` includes the v1.7.5 critical phrase test (input contains exact `"Here is some useful information..."`, output contains `"Environment context..."`)
- `prepend_claude_code_identity` idempotency — already-identity input not double-prepended
- `InflightRefreshGate`: 5 concurrent calls → 1 underlying refresh; exception propagates to all callers; gate resets after completion
- `transform_request_payload` ordering: billing header computed BEFORE tool name prefixing
- Provider integration: `get_response` and `get_response_stream` happy paths assert URL, headers, payload shape, and unprefixed response

## Implementation plan (commit sequence)

Each commit leaves the project in a green state:

1. `add anthropic_oauth subpackage skeleton with constants` — `constants.py` + `test_constants.py`
2. `add pkce helpers` — `pkce.py` + tests
3. `add cch billing header` — `cch.py` + tests
4. `add auth helpers` — `auth.py` (PKCE flow, exchange, refresh, gate) + tests
5. `add transform helpers` — `transform.py` + tests
6. `port AnthropicOAuthProvider to use new modules` — `provider.py` + `__init__.py` + tests; updates `config_flow.py` imports (`from .oauth import …` → `from .providers.anthropic_oauth import …`) WITHOUT functional changes; deletes old `oauth.py`, old `providers/anthropic_oauth.py`, and old test file. Atomic — leaves project green.
7. `add Create API Key OAuth flow to config flow` — adds `async_step_anthropic_method` + `async_step_anthropic_create_key` to `config_flow.py` + tests
8. `add cost zeroing for anthropic_oauth in frontend` — `cost.service.ts` + provider helper
9. `bump homeclaw version to 1.3.0` — `manifest.json` + `CHANGELOG.md` (BREAKING — existing OAuth users may need reauth)

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Old refresh tokens rejected by `platform.claude.com` | Low | Existing reauth flow triggers automatically |
| Tool prefix regex hits a chunk boundary in stream | Low | Stripping is done on parsed event dicts, not raw text |
| CCH salt or version becomes stale | Medium | Constants in one file; test_cch pins values for visibility |
| `?beta=true` query becomes deprecated | Low | Easy revert in `rewrite_url` |
| `anthropic-beta` flag list drift from upstream | Medium | Single tuple in constants; test asserts membership |

## Decisions log (from brainstorming)

| Question | Decision |
|---|---|
| Scope | C — full port (Tier 1 + 2 + 3) |
| File structure | A — subpackage `providers/anthropic_oauth/` |
| Tool prefix | B — `mcp__homeclaw__<name>` (double-underscore namespace) |
| Tests strategy | A — full TDD rewrite per module |
| Migration of existing OAuth tokens | A — hard cutover; reauth flow handles failures |

## Provenance

This port copies code patterns and reverse-engineered values (CCH salt, version, tool prefix convention, classifier-fingerprint phrase) from MIT-licensed opencode-anthropic-auth v1.8.0 by Ex Machina. CHANGELOG references in code comments preserve traceability.
