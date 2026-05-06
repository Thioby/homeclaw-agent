# Anthropic OAuth Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port opencode-anthropic-auth v1.8.0 (TypeScript, MIT) to HomeClaw as a Python subpackage so HomeClaw OAuth requests pass Anthropic's server-side classifier.

**Architecture:** New subpackage `custom_components/homeclaw/providers/anthropic_oauth/` with 6 modules (constants, pkce, cch, auth, transform, provider). Pure-Python helpers, HA-aware glue lives only in `provider.py`. Old flat files (`oauth.py`, `providers/anthropic_oauth.py`) deleted in commit 6.

**Tech Stack:** Python 3.12+, asyncio, aiohttp, dataclasses, hashlib, secrets, base64, urllib.parse. Tests with pytest (asyncio_mode=auto), unittest.mock + aioresponses for HTTP mocking.

**Spec:** `docs/superpowers/specs/2026-05-05-anthropic-oauth-port-design.md`

**Reference:** `/Users/anowak/Projects/homeAssistant/opencode-anthropic-auth/src/` (canonical TS source)

---

## File Map

**Created:**
- `custom_components/homeclaw/providers/anthropic_oauth/__init__.py` — public API exports
- `custom_components/homeclaw/providers/anthropic_oauth/constants.py`
- `custom_components/homeclaw/providers/anthropic_oauth/pkce.py`
- `custom_components/homeclaw/providers/anthropic_oauth/cch.py`
- `custom_components/homeclaw/providers/anthropic_oauth/auth.py`
- `custom_components/homeclaw/providers/anthropic_oauth/transform.py`
- `custom_components/homeclaw/providers/anthropic_oauth/provider.py`
- `tests/test_providers/test_anthropic_oauth/__init__.py` (empty)
- `tests/test_providers/test_anthropic_oauth/test_constants.py`
- `tests/test_providers/test_anthropic_oauth/test_pkce.py`
- `tests/test_providers/test_anthropic_oauth/test_cch.py`
- `tests/test_providers/test_anthropic_oauth/test_auth.py`
- `tests/test_providers/test_anthropic_oauth/test_transform.py`
- `tests/test_providers/test_anthropic_oauth/test_provider.py`
- `custom_components/homeclaw/frontend/src/lib/services/cost.service.ts` (if not exists; see Task 8)

**Deleted (in Task 6 atomically):**
- `custom_components/homeclaw/oauth.py`
- `custom_components/homeclaw/providers/anthropic_oauth.py`
- `tests/test_providers/test_anthropic_oauth.py`

**Modified:**
- `custom_components/homeclaw/config_flow.py` (Task 6: imports; Task 7: new steps)
- `custom_components/homeclaw/manifest.json` (Task 9: version)
- `CHANGELOG.md` (Task 9)
- `custom_components/homeclaw/frontend/src/lib/services/provider.service.ts` (Task 8)

---

## Conventions

All Python files start with:
```python
"""<module-docstring>.

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
"""
from __future__ import annotations
```

Test files use existing pattern from `tests/test_providers/test_anthropic.py` — no `@pytest.mark.asyncio` (pytest.ini has `asyncio_mode = auto`). Mock HTTP with `aioresponses` library if available, otherwise `unittest.mock.AsyncMock` on `aiohttp.ClientSession.post`.

Run tests from project root: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha`.

Commit messages: B1 simple English, 1 line, no extended description (per user's CLAUDE.md).

---

## Task 1: Subpackage skeleton + constants

**Files:**
- Create: `custom_components/homeclaw/providers/anthropic_oauth/__init__.py`
- Create: `custom_components/homeclaw/providers/anthropic_oauth/constants.py`
- Create: `tests/test_providers/test_anthropic_oauth/__init__.py`
- Create: `tests/test_providers/test_anthropic_oauth/test_constants.py`

- [ ] **Step 1.1: Create empty package `__init__.py`s**

```bash
mkdir -p custom_components/homeclaw/providers/anthropic_oauth
mkdir -p tests/test_providers/test_anthropic_oauth
```

Write `custom_components/homeclaw/providers/anthropic_oauth/__init__.py`:
```python
"""Anthropic OAuth subpackage for HomeClaw.

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
Public API will be filled in Task 6 (after provider.py exists).
"""
from __future__ import annotations
```

Write `tests/test_providers/test_anthropic_oauth/__init__.py` (empty file).

- [ ] **Step 1.2: Write test_constants.py**

Write `tests/test_providers/test_anthropic_oauth/test_constants.py`:
```python
"""Tests for anthropic_oauth.constants — sanity check on values."""
from __future__ import annotations

from custom_components.homeclaw.providers.anthropic_oauth import constants


class TestUrls:
    def test_token_url_is_platform_claude(self):
        assert constants.TOKEN_URL == "https://platform.claude.com/v1/oauth/token"

    def test_callback_url_is_platform_claude(self):
        assert constants.CODE_CALLBACK_URL == "https://platform.claude.com/oauth/code/callback"

    def test_authorize_console_is_platform_claude(self):
        assert constants.AUTHORIZE_URLS["console"] == "https://platform.claude.com/oauth/authorize"

    def test_authorize_max_is_claude_ai(self):
        assert constants.AUTHORIZE_URLS["max"] == "https://claude.ai/oauth/authorize"

    def test_create_api_key_url_is_anthropic_api(self):
        assert constants.CREATE_API_KEY_URL == "https://api.anthropic.com/api/oauth/claude_cli/create_api_key"


class TestScopes:
    def test_scopes_count_is_six(self):
        assert len(constants.OAUTH_SCOPES) == 6

    def test_scopes_includes_new_v18_scopes(self):
        assert "user:sessions:claude_code" in constants.OAUTH_SCOPES
        assert "user:mcp_servers" in constants.OAUTH_SCOPES
        assert "user:file_upload" in constants.OAUTH_SCOPES

    def test_scopes_keeps_legacy_three(self):
        assert "org:create_api_key" in constants.OAUTH_SCOPES
        assert "user:profile" in constants.OAUTH_SCOPES
        assert "user:inference" in constants.OAUTH_SCOPES


class TestToolPrefix:
    def test_tool_prefix_is_double_underscore_namespaced(self):
        assert constants.TOOL_PREFIX == "mcp__homeclaw__"

    def test_tool_prefix_namespace(self):
        assert constants.TOOL_PREFIX_NAMESPACE == "homeclaw"


class TestBetas:
    def test_required_betas_includes_oauth_2025_04_20(self):
        assert "oauth-2025-04-20" in constants.REQUIRED_BETAS

    def test_required_betas_includes_thinking(self):
        assert "interleaved-thinking-2025-05-14" in constants.REQUIRED_BETAS


class TestUserAgent:
    def test_user_agent_is_claude_cli_2_1_87(self):
        assert constants.USER_AGENT == "claude-cli/2.1.87 (external, cli)"


class TestCCHValues:
    def test_cch_salt(self):
        assert constants.CCH_SALT == "59cf53e54c78"

    def test_cch_positions(self):
        assert constants.CCH_POSITIONS == (4, 7, 20)

    def test_claude_code_version(self):
        assert constants.CLAUDE_CODE_VERSION == "2.1.87"

    def test_claude_code_entrypoint(self):
        assert constants.CLAUDE_CODE_ENTRYPOINT == "sdk-cli"


class TestSanitizationConfig:
    def test_opencode_identity_prefix(self):
        assert constants.OPENCODE_IDENTITY_PREFIX == "You are OpenCode"

    def test_claude_code_identity_is_agent_sdk_phrasing(self):
        assert constants.CLAUDE_CODE_IDENTITY == (
            "You are a Claude agent, built on Anthropic's Claude Agent SDK."
        )

    def test_anchors_include_anomalyco_url(self):
        assert "github.com/anomalyco/opencode" in constants.PARAGRAPH_REMOVAL_ANCHORS

    def test_anchors_include_opencode_docs(self):
        assert "opencode.ai/docs" in constants.PARAGRAPH_REMOVAL_ANCHORS

    def test_critical_phrase_replacement_present(self):
        match_strings = [pair[0] for pair in constants.TEXT_REPLACEMENTS]
        assert any(
            "Here is some useful information about the environment" in m
            for m in match_strings
        ), "Missing critical v1.7.5 classifier-fingerprint replacement"

    def test_inline_replacement_for_opencode_phrase(self):
        match_strings = [pair[0] for pair in constants.TEXT_REPLACEMENTS]
        assert "if OpenCode honestly" in match_strings


class TestRetryConfig:
    def test_refresh_max_retries(self):
        assert constants.REFRESH_MAX_RETRIES == 2

    def test_refresh_base_delay(self):
        assert constants.REFRESH_BASE_DELAY_S == 0.5
```

- [ ] **Step 1.3: Run tests to verify FAIL**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_constants.py -v`
Expected: FAIL with `ModuleNotFoundError` or `AttributeError` on `constants` module.

- [ ] **Step 1.4: Write constants.py**

Write `custom_components/homeclaw/providers/anthropic_oauth/constants.py`:
```python
"""OAuth client constants for Anthropic Claude (Pro/Max + Console).

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
Updates here track Anthropic's server-side classifier behavior;
see CHANGELOG of upstream plugin for rationale of each value.
"""
from __future__ import annotations

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

AUTHORIZE_URLS = {
    "console": "https://platform.claude.com/oauth/authorize",
    "max": "https://claude.ai/oauth/authorize",
}
CODE_CALLBACK_URL = "https://platform.claude.com/oauth/code/callback"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CREATE_API_KEY_URL = "https://api.anthropic.com/api/oauth/claude_cli/create_api_key"

OAUTH_SCOPES = (
    "org:create_api_key",
    "user:profile",
    "user:inference",
    "user:sessions:claude_code",
    "user:mcp_servers",
    "user:file_upload",
)

TOOL_PREFIX_NAMESPACE = "homeclaw"
TOOL_PREFIX = f"mcp__{TOOL_PREFIX_NAMESPACE}__"

REQUIRED_BETAS = (
    "oauth-2025-04-20",
    "interleaved-thinking-2025-05-14",
)

OPENCODE_IDENTITY_PREFIX = "You are OpenCode"
CLAUDE_CODE_IDENTITY = "You are a Claude agent, built on Anthropic's Claude Agent SDK."

CCH_SALT = "59cf53e54c78"
CCH_POSITIONS = (4, 7, 20)
CLAUDE_CODE_VERSION = "2.1.87"
CLAUDE_CODE_ENTRYPOINT = "sdk-cli"

USER_AGENT = "claude-cli/2.1.87 (external, cli)"

# Anchors identifying paragraphs to remove from system prompt.
# Resilient to upstream rewording — anchor (URL) persists across edits.
PARAGRAPH_REMOVAL_ANCHORS = (
    "github.com/anomalyco/opencode",
    "opencode.ai/docs",
)

# Inline replacements after paragraph removal.
# "Here is some useful information..." is the EXACT phrase Anthropic's
# server-side classifier matches as third-party agent CLI fingerprint;
# triggers 400 disguised as "You're out of extra usage." (upstream v1.7.5).
TEXT_REPLACEMENTS = (
    ("if OpenCode honestly", "if the assistant honestly"),
    (
        "Here is some useful information about the environment you are running in:",
        "Environment context you are running in:",
    ),
)

REFRESH_MAX_RETRIES = 2
REFRESH_BASE_DELAY_S = 0.5
```

- [ ] **Step 1.5: Run tests to verify PASS**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_constants.py -v`
Expected: all 22 tests PASS.

- [ ] **Step 1.6: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic_oauth/__init__.py \
        custom_components/homeclaw/providers/anthropic_oauth/constants.py \
        tests/test_providers/test_anthropic_oauth/__init__.py \
        tests/test_providers/test_anthropic_oauth/test_constants.py
git commit -m "add anthropic oauth subpackage skeleton with constants"
```

---

## Task 2: PKCE module

**Files:**
- Create: `custom_components/homeclaw/providers/anthropic_oauth/pkce.py`
- Create: `tests/test_providers/test_anthropic_oauth/test_pkce.py`

- [ ] **Step 2.1: Write test_pkce.py**

```python
"""Tests for anthropic_oauth.pkce."""
from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import FrozenInstanceError

import pytest

from custom_components.homeclaw.providers.anthropic_oauth.pkce import (
    PKCEPair,
    generate_pkce,
)


class TestPKCEPair:
    def test_default_method_is_s256(self):
        pair = PKCEPair(verifier="v", challenge="c")
        assert pair.method == "S256"

    def test_pair_is_frozen(self):
        pair = PKCEPair(verifier="v", challenge="c")
        with pytest.raises(FrozenInstanceError):
            pair.verifier = "x"  # type: ignore[misc]


class TestGeneratePKCE:
    def test_returns_pkce_pair(self):
        pair = generate_pkce()
        assert isinstance(pair, PKCEPair)

    def test_method_is_s256(self):
        pair = generate_pkce()
        assert pair.method == "S256"

    def test_verifier_is_url_safe_no_padding(self):
        pair = generate_pkce()
        # base64url alphabet plus no '=' padding
        assert re.fullmatch(r"[A-Za-z0-9_-]+", pair.verifier)
        assert "=" not in pair.verifier

    def test_verifier_length_is_86_chars(self):
        # 64 random bytes -> base64 -> 88 chars with '==' padding -> 86 stripped
        pair = generate_pkce()
        assert len(pair.verifier) == 86

    def test_challenge_is_sha256_of_verifier(self):
        pair = generate_pkce()
        digest = hashlib.sha256(pair.verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        assert pair.challenge == expected

    def test_two_calls_produce_different_verifiers(self):
        a = generate_pkce()
        b = generate_pkce()
        assert a.verifier != b.verifier
```

- [ ] **Step 2.2: Run tests to verify FAIL**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_pkce.py -v`
Expected: FAIL with import error.

- [ ] **Step 2.3: Write pkce.py**

```python
"""PKCE (RFC 7636) helpers for OAuth 2.0 authorization code flow.

Ported from opencode-anthropic-auth v1.8.0 src/pkce.ts (MIT).
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PKCEPair:
    """PKCE verifier + S256 challenge bundle."""

    verifier: str
    challenge: str
    method: str = "S256"


def generate_pkce() -> PKCEPair:
    """Generate a fresh PKCE verifier + S256 challenge.

    Returns:
        PKCEPair with URL-safe base64 strings (no padding).
    """
    raw = secrets.token_bytes(64)
    verifier = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return PKCEPair(verifier=verifier, challenge=challenge)
```

- [ ] **Step 2.4: Run tests to verify PASS**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_pkce.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 2.5: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic_oauth/pkce.py \
        tests/test_providers/test_anthropic_oauth/test_pkce.py
git commit -m "add pkce helpers for anthropic oauth"
```

---

## Task 3: CCH billing header

**Files:**
- Create: `custom_components/homeclaw/providers/anthropic_oauth/cch.py`
- Create: `tests/test_providers/test_anthropic_oauth/test_cch.py`

- [ ] **Step 3.1: Write test_cch.py**

```python
"""Tests for anthropic_oauth.cch — billing header computation."""
from __future__ import annotations

import hashlib

from custom_components.homeclaw.providers.anthropic_oauth.cch import (
    build_billing_header_value,
    compute_cch,
    compute_version_suffix,
    extract_first_user_message_text,
)


class TestExtractFirstUserMessageText:
    def test_empty_list_returns_empty(self):
        assert extract_first_user_message_text([]) == ""

    def test_no_user_returns_empty(self):
        msgs = [{"role": "assistant", "content": "hi"}]
        assert extract_first_user_message_text(msgs) == ""

    def test_string_content(self):
        msgs = [{"role": "user", "content": "hello world"}]
        assert extract_first_user_message_text(msgs) == "hello world"

    def test_list_content_first_text_block(self):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {}},
                    {"type": "text", "text": "describe this"},
                ],
            }
        ]
        assert extract_first_user_message_text(msgs) == "describe this"

    def test_list_content_no_text_block_returns_empty(self):
        msgs = [{"role": "user", "content": [{"type": "image", "source": {}}]}]
        assert extract_first_user_message_text(msgs) == ""

    def test_skips_assistant_to_first_user(self):
        msgs = [
            {"role": "assistant", "content": "previous"},
            {"role": "user", "content": "find me"},
        ]
        assert extract_first_user_message_text(msgs) == "find me"

    def test_first_user_with_empty_text_returns_empty(self):
        # Matches TS behavior: returns first user; if no text, ""
        msgs = [{"role": "user", "content": ""}]
        assert extract_first_user_message_text(msgs) == ""


class TestComputeCCH:
    def test_known_value_hello(self):
        # First 5 hex chars of sha256("hello")
        expected = hashlib.sha256(b"hello").hexdigest()[:5]
        assert compute_cch("hello") == expected

    def test_empty_string_is_deterministic(self):
        expected = hashlib.sha256(b"").hexdigest()[:5]
        assert compute_cch("") == expected

    def test_returns_5_hex_chars(self):
        result = compute_cch("any text here")
        assert len(result) == 5
        assert all(c in "0123456789abcdef" for c in result)


class TestComputeVersionSuffix:
    def test_known_value(self):
        # Verify against deterministic inputs.
        # text="abcdefghijklmnopqrstuvwxyz", version="2.1.87"
        # chars = text[4]+text[7]+text[20] = "e" + "h" + "u" = "ehu"
        # payload = "59cf53e54c78" + "ehu" + "2.1.87"
        text = "abcdefghijklmnopqrstuvwxyz"
        payload = "59cf53e54c78ehu2.1.87"
        expected = hashlib.sha256(payload.encode()).hexdigest()[:3]
        assert compute_version_suffix(text, version="2.1.87") == expected

    def test_short_text_uses_zero_fallback(self):
        # text length 3 -> positions 4, 7, 20 all out of range -> "000"
        # chars = "000"
        # payload = "59cf53e54c78" + "000" + "2.1.87"
        payload = "59cf53e54c780002.1.87"
        expected = hashlib.sha256(payload.encode()).hexdigest()[:3]
        assert compute_version_suffix("abc", version="2.1.87") == expected

    def test_returns_3_hex_chars(self):
        result = compute_version_suffix("hello world this is a test", version="2.1.87")
        assert len(result) == 3
        assert all(c in "0123456789abcdef" for c in result)


class TestBuildBillingHeaderValue:
    def test_format_with_user_message(self):
        msgs = [{"role": "user", "content": "Hello there, this is a long enough message"}]
        header = build_billing_header_value(msgs)
        # Format check
        assert header.startswith("x-anthropic-billing-header: ")
        assert "cc_version=2.1.87." in header
        assert "cc_entrypoint=sdk-cli;" in header
        assert "cch=" in header
        assert header.endswith(";")

    def test_format_includes_correct_cch(self):
        text = "Hello there, this is a long enough message"
        msgs = [{"role": "user", "content": text}]
        header = build_billing_header_value(msgs)
        expected_cch = hashlib.sha256(text.encode()).hexdigest()[:5]
        assert f"cch={expected_cch};" in header

    def test_custom_version_and_entrypoint(self):
        msgs = [{"role": "user", "content": "hi"}]
        header = build_billing_header_value(msgs, version="9.9.9", entrypoint="custom")
        assert "cc_version=9.9.9." in header
        assert "cc_entrypoint=custom;" in header

    def test_empty_messages_still_produces_deterministic_header(self):
        # Anthropic might still accept this; should not raise.
        header = build_billing_header_value([])
        assert header.startswith("x-anthropic-billing-header: ")
        assert "cc_entrypoint=sdk-cli" in header
```

- [ ] **Step 3.2: Run tests to verify FAIL**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_cch.py -v`
Expected: FAIL.

- [ ] **Step 3.3: Write cch.py**

```python
"""Content-consistency-hash billing header for Anthropic OAuth requests.

Ported from opencode-anthropic-auth v1.8.0 src/cch.ts (MIT).
Reverse-engineered from Claude Code binary — Anthropic uses this
to verify subscription legitimacy.
"""
from __future__ import annotations

import hashlib
from typing import Any

from .constants import (
    CCH_POSITIONS,
    CCH_SALT,
    CLAUDE_CODE_ENTRYPOINT,
    CLAUDE_CODE_VERSION,
)


def extract_first_user_message_text(messages: list[dict[str, Any]]) -> str:
    """Extract text from the first user message's first text block.

    Handles both string and array-of-blocks content formats.
    Returns "" when no user message exists or when the first user
    message has no text content.
    """
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        return text
        return ""
    return ""


def compute_cch(message_text: str) -> str:
    """Compute cch: first 5 hex chars of SHA-256(message_text)."""
    return hashlib.sha256(message_text.encode()).hexdigest()[:5]


def compute_version_suffix(
    message_text: str, version: str = CLAUDE_CODE_VERSION
) -> str:
    """Compute 3-char version suffix from sampled message characters.

    Uses character positions from CCH_POSITIONS — when index is out of
    range, falls back to "0" (matches TS `messageText[i] || '0'`).
    """
    chars = "".join(
        message_text[i] if i < len(message_text) else "0"
        for i in CCH_POSITIONS
    )
    payload = f"{CCH_SALT}{chars}{version}"
    return hashlib.sha256(payload.encode()).hexdigest()[:3]


def build_billing_header_value(
    messages: list[dict[str, Any]],
    *,
    version: str = CLAUDE_CODE_VERSION,
    entrypoint: str = CLAUDE_CODE_ENTRYPOINT,
) -> str:
    """Build complete billing header string for insertion as system block."""
    text = extract_first_user_message_text(messages)
    suffix = compute_version_suffix(text, version)
    cch = compute_cch(text)
    return (
        "x-anthropic-billing-header: "
        f"cc_version={version}.{suffix}; "
        f"cc_entrypoint={entrypoint}; "
        f"cch={cch};"
    )
```

- [ ] **Step 3.4: Run tests to verify PASS**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_cch.py -v`
Expected: all 14 tests PASS.

- [ ] **Step 3.5: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic_oauth/cch.py \
        tests/test_providers/test_anthropic_oauth/test_cch.py
git commit -m "add cch billing header helpers"
```

---

## Task 4: Auth helpers (PKCE flow + token exchange + refresh + InflightRefreshGate)

This is the largest non-provider module — split into 4 sub-cycles.

**Files:**
- Create: `custom_components/homeclaw/providers/anthropic_oauth/auth.py`
- Create: `tests/test_providers/test_anthropic_oauth/test_auth.py`

### Task 4a: Authorize URL + parse_callback_input

- [ ] **Step 4.1: Write initial test_auth.py with helpers + URL/parser tests**

```python
"""Tests for anthropic_oauth.auth."""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.homeclaw.providers.anthropic_oauth.auth import (
    AuthorizationRequest,
    InflightRefreshGate,
    OAuthRefreshError,
    TokenSet,
    authorize,
    build_authorize_url,
    create_api_key,
    exchange_code,
    parse_callback_input,
    refresh_with_retry,
)
from custom_components.homeclaw.providers.anthropic_oauth.constants import (
    CLIENT_ID,
    CODE_CALLBACK_URL,
    OAUTH_SCOPES,
)
from custom_components.homeclaw.providers.anthropic_oauth.pkce import PKCEPair


class TestBuildAuthorizeUrl:
    def test_max_mode_uses_claude_ai(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="c" * 43)
        url = build_authorize_url(pkce, "state-xyz", mode="max")
        assert url.startswith("https://claude.ai/oauth/authorize?")

    def test_console_mode_uses_platform_claude(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="c" * 43)
        url = build_authorize_url(pkce, "state-xyz", mode="console")
        assert url.startswith("https://platform.claude.com/oauth/authorize?")

    def test_includes_required_params(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="abc123")
        url = build_authorize_url(pkce, "state-xyz", mode="max")
        assert f"client_id={CLIENT_ID}" in url
        assert "response_type=code" in url
        assert "code_challenge=abc123" in url
        assert "code_challenge_method=S256" in url
        assert "state=state-xyz" in url
        assert "code=true" in url

    def test_scope_is_space_joined(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="c")
        url = build_authorize_url(pkce, "s", mode="max")
        # space-separated scope, url-encoded as +
        assert "scope=" in url
        # six scopes joined by space (url-encoded as %20 or +)
        for scope in OAUTH_SCOPES:
            assert scope in url

    def test_redirect_uri_is_callback(self):
        pkce = PKCEPair(verifier="v", challenge="c")
        url = build_authorize_url(pkce, "s", mode="max")
        from urllib.parse import quote
        assert quote(CODE_CALLBACK_URL, safe="") in url


class TestAuthorize:
    def test_returns_authorization_request_and_pkce(self):
        request, pkce = authorize(mode="max")
        assert isinstance(request, AuthorizationRequest)
        assert isinstance(pkce, PKCEPair)

    def test_request_url_matches_pkce(self):
        request, pkce = authorize(mode="max")
        assert pkce.challenge in request.url
        assert request.state in request.url

    def test_two_calls_have_different_states(self):
        a, _ = authorize()
        b, _ = authorize()
        assert a.state != b.state


class TestParseCallbackInput:
    def test_full_url_format(self):
        url = "https://example.com/cb?code=ABC&state=XYZ&extra=foo"
        assert parse_callback_input(url) == ("ABC", "XYZ")

    def test_hash_format(self):
        assert parse_callback_input("CODE123#STATE456") == ("CODE123", "STATE456")

    def test_query_string_format(self):
        assert parse_callback_input("code=A&state=B") == ("A", "B")

    def test_url_missing_state_returns_none(self):
        assert parse_callback_input("https://example.com/cb?code=ABC") is None

    def test_empty_input_returns_none(self):
        assert parse_callback_input("") is None
        assert parse_callback_input("   ") is None

    def test_whitespace_handling(self):
        assert parse_callback_input("  CODE#STATE  ") == ("CODE", "STATE")

    def test_garbage_input_returns_none(self):
        assert parse_callback_input("nothing useful") is None

    def test_hash_with_empty_parts_returns_none(self):
        assert parse_callback_input("#STATE") is None
        assert parse_callback_input("CODE#") is None
```

- [ ] **Step 4.2: Run tests to verify FAIL**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py -v`
Expected: FAIL on import.

- [ ] **Step 4.3: Write initial auth.py (URL + parser only)**

```python
"""Anthropic OAuth flow: authorize URL, code exchange, token refresh.

Ported from opencode-anthropic-auth v1.8.0 src/auth.ts and src/index.ts
refresh logic (MIT, © Ex Machina).
"""
from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from .constants import (
    AUTHORIZE_URLS,
    CLIENT_ID,
    CODE_CALLBACK_URL,
    CREATE_API_KEY_URL,
    OAUTH_SCOPES,
    REFRESH_BASE_DELAY_S,
    REFRESH_MAX_RETRIES,
    TOKEN_URL,
)
from .pkce import PKCEPair, generate_pkce


# Mimics axios — Anthropic accepts/expects this for token endpoint.
_TOKEN_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "axios/1.13.6",
}

AuthMode = Literal["max", "console"]


class OAuthRefreshError(Exception):
    """Raised when token refresh or exchange fails.

    Attributes:
        is_permanent: True when retrying won't help — refresh token is
            revoked/expired (Anthropic returns ``invalid_grant``).
    """

    def __init__(self, message: str, *, is_permanent: bool = False) -> None:
        super().__init__(message)
        self.is_permanent = is_permanent


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """Result of starting an OAuth flow — feed back into exchange_code."""

    url: str
    redirect_uri: str
    state: str
    verifier: str


@dataclass(frozen=True, slots=True)
class TokenSet:
    """OAuth token bundle as persisted by HomeClaw."""

    access_token: str
    refresh_token: str
    expires_at: float  # unix seconds


def _generate_state() -> str:
    """Random hex state parameter (mirrors TS uuid-no-dashes pattern)."""
    return secrets.token_hex(16)


def build_authorize_url(pkce: PKCEPair, state: str, mode: AuthMode = "max") -> str:
    """Construct OAuth authorize URL with PKCE + state."""
    base = AUTHORIZE_URLS[mode]
    params = {
        "code": "true",
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": CODE_CALLBACK_URL,
        "scope": " ".join(OAUTH_SCOPES),
        "code_challenge": pkce.challenge,
        "code_challenge_method": pkce.method,
        "state": state,
    }
    return f"{base}?{urlencode(params)}"


def authorize(mode: AuthMode = "max") -> tuple[AuthorizationRequest, PKCEPair]:
    """Begin OAuth: generate PKCE+state, return authorize URL + verifier."""
    pkce = generate_pkce()
    state = _generate_state()
    request = AuthorizationRequest(
        url=build_authorize_url(pkce, state, mode),
        redirect_uri=CODE_CALLBACK_URL,
        state=state,
        verifier=pkce.verifier,
    )
    return request, pkce


def parse_callback_input(raw: str) -> tuple[str, str] | None:
    """Parse callback input — three accepted formats:

    1. Full callback URL: ``https://.../callback?code=X&state=Y``
    2. Legacy ``code#state`` string
    3. URL-encoded ``code=X&state=Y`` query string

    Returns:
        Tuple ``(code, state)`` or None if unparseable.
    """
    trimmed = raw.strip()
    if not trimmed:
        return None

    # Format 1: full URL
    try:
        parsed = urlparse(trimmed)
        if parsed.scheme and parsed.netloc:
            qs = parse_qs(parsed.query)
            code = qs.get("code", [""])[0]
            state = qs.get("state", [""])[0]
            if code and state:
                return code, state
    except ValueError:
        pass

    # Format 2: code#state
    if "#" in trimmed:
        parts = trimmed.split("#", 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    # Format 3: bare query string
    qs = parse_qs(trimmed)
    code = qs.get("code", [""])[0]
    state = qs.get("state", [""])[0]
    if code and state:
        return code, state

    return None
```

- [ ] **Step 4.4: Run tests — URL/parser tests pass**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py::TestBuildAuthorizeUrl tests/test_providers/test_anthropic_oauth/test_auth.py::TestAuthorize tests/test_providers/test_anthropic_oauth/test_auth.py::TestParseCallbackInput -v`
Expected: ~16 tests PASS. Other tests (TestExchangeCode etc.) will fail due to missing functions — that's expected for now.

### Task 4b: exchange_code

- [ ] **Step 4.5: Append exchange_code tests to test_auth.py**

```python
class TestExchangeCode:
    async def test_success(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 200
        ctx.__aenter__.return_value.json = AsyncMock(return_value={
            "access_token": "AC", "refresh_token": "RF", "expires_in": 3600,
        })
        session.post = MagicMock(return_value=ctx)

        before = time.time()
        result = await exchange_code(session, "code#state", "verifier", expected_state="state")
        assert isinstance(result, TokenSet)
        assert result.access_token == "AC"
        assert result.refresh_token == "RF"
        assert result.expires_at >= before + 3599

    async def test_unparseable_input_raises_permanent(self):
        session = MagicMock()
        with pytest.raises(OAuthRefreshError) as exc:
            await exchange_code(session, "garbage", "v")
        assert exc.value.is_permanent is True

    async def test_state_mismatch_raises_permanent(self):
        session = MagicMock()
        with pytest.raises(OAuthRefreshError) as exc:
            await exchange_code(session, "code#WRONG", "v", expected_state="EXPECTED")
        assert exc.value.is_permanent is True

    async def test_http_error_raises_permanent(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 400
        ctx.__aenter__.return_value.text = AsyncMock(return_value="bad request")
        session.post = MagicMock(return_value=ctx)

        with pytest.raises(OAuthRefreshError) as exc:
            await exchange_code(session, "code#state", "v")
        assert exc.value.is_permanent is True
```

- [ ] **Step 4.6: Run tests — exchange tests fail**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py::TestExchangeCode -v`
Expected: FAIL on import of `exchange_code`.

- [ ] **Step 4.7: Append exchange_code to auth.py**

```python
async def exchange_code(
    session: aiohttp.ClientSession,
    callback_input: str,
    verifier: str,
    *,
    expected_state: str | None = None,
) -> TokenSet:
    """Exchange authorization code for tokens.

    Args:
        session: aiohttp session.
        callback_input: code or full callback URL pasted by user.
        verifier: PKCE verifier from the original authorize() call.
        expected_state: original state — when set, mismatch raises permanent.

    Raises:
        OAuthRefreshError: on parse failure, state mismatch, or HTTP error.
    """
    parsed = parse_callback_input(callback_input)
    if parsed is None:
        raise OAuthRefreshError("Unparseable callback input", is_permanent=True)
    code, state = parsed
    if expected_state is not None and state != expected_state:
        raise OAuthRefreshError("OAuth state mismatch", is_permanent=True)

    payload = {
        "code": code,
        "state": state,
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": CODE_CALLBACK_URL,
        "code_verifier": verifier,
    }
    async with session.post(TOKEN_URL, json=payload, headers=_TOKEN_HEADERS) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise OAuthRefreshError(
                f"Token exchange failed: {resp.status} — {body[:300]}",
                is_permanent=True,
            )
        data = await resp.json()

    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        expires_at=time.time() + data.get("expires_in", 28800),
    )
```

- [ ] **Step 4.8: Run tests — exchange tests pass**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py::TestExchangeCode -v`
Expected: 4 tests PASS.

### Task 4c: refresh_with_retry + InflightRefreshGate

- [ ] **Step 4.9: Append refresh + gate tests to test_auth.py**

```python
class TestRefreshWithRetry:
    @staticmethod
    def _mock_session(*responses):
        """Build a session whose `.post` returns the given mocked responses in order.

        Each item is a dict like {"status": 200, "json": {...}} or {"status": 500, "text": "..."}
        or {"raise": <exception>} for transport errors.
        """
        session = MagicMock()
        contexts = []
        for r in responses:
            ctx = AsyncMock()
            if "raise" in r:
                ctx.__aenter__.side_effect = r["raise"]
            else:
                ctx.__aenter__.return_value.status = r["status"]
                if "json" in r:
                    ctx.__aenter__.return_value.json = AsyncMock(return_value=r["json"])
                if "text" in r:
                    ctx.__aenter__.return_value.text = AsyncMock(return_value=r["text"])
            contexts.append(ctx)
        session.post = MagicMock(side_effect=contexts)
        return session

    async def test_success_on_first_try(self):
        session = self._mock_session(
            {"status": 200, "json": {"access_token": "A", "refresh_token": "R", "expires_in": 3600}}
        )
        read = AsyncMock(return_value="REFRESH")

        tokens = await refresh_with_retry(session, read)
        assert tokens.access_token == "A"
        assert tokens.refresh_token == "R"
        assert read.await_count == 1

    async def test_5xx_retried_and_succeeds(self):
        session = self._mock_session(
            {"status": 503, "text": "boom"},
            {"status": 200, "json": {"access_token": "A2", "refresh_token": "R2", "expires_in": 3600}},
        )
        read = AsyncMock(return_value="REFRESH")

        tokens = await refresh_with_retry(session, read)
        assert tokens.access_token == "A2"
        assert read.await_count == 2  # re-read each attempt

    async def test_invalid_grant_raises_permanent_no_retry(self):
        session = self._mock_session(
            {"status": 400, "text": '{"error":"invalid_grant"}'},
        )
        read = AsyncMock(return_value="REFRESH")

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read)
        assert exc.value.is_permanent is True
        assert read.await_count == 1

    async def test_network_error_retried(self):
        session = self._mock_session(
            {"raise": aiohttp.ClientConnectionError("ECONNRESET")},
            {"status": 200, "json": {"access_token": "A3", "refresh_token": "R3", "expires_in": 3600}},
        )
        read = AsyncMock(return_value="REFRESH")

        tokens = await refresh_with_retry(session, read)
        assert tokens.access_token == "A3"
        assert read.await_count == 2

    async def test_exhausts_retries_on_persistent_network_error(self):
        # Fail on every attempt (max_retries + 1 = 3 attempts total)
        session = self._mock_session(
            {"raise": aiohttp.ClientConnectionError("err")},
            {"raise": aiohttp.ClientConnectionError("err")},
            {"raise": aiohttp.ClientConnectionError("err")},
        )
        read = AsyncMock(return_value="REFRESH")

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read)
        assert exc.value.is_permanent is False
        assert read.await_count == 3

    async def test_no_refresh_token_raises_permanent(self):
        session = MagicMock()
        read = AsyncMock(return_value="")

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read)
        assert exc.value.is_permanent is True


class TestInflightRefreshGate:
    async def test_concurrent_calls_share_one_refresh(self):
        gate = InflightRefreshGate()

        call_count = 0

        async def fake_refresh(session, read):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # simulate latency
            return TokenSet("A", "R", time.time() + 3600)

        session = MagicMock()
        read = AsyncMock(return_value="REFRESH")

        with patch(
            "custom_components.homeclaw.providers.anthropic_oauth.auth.refresh_with_retry",
            side_effect=fake_refresh,
        ):
            results = await asyncio.gather(*[gate.refresh(session, read) for _ in range(5)])

        assert call_count == 1
        assert all(r.access_token == "A" for r in results)

    async def test_gate_resets_after_completion(self):
        gate = InflightRefreshGate()

        call_count = 0

        async def fake_refresh(session, read):
            nonlocal call_count
            call_count += 1
            return TokenSet(f"A{call_count}", "R", time.time() + 3600)

        session = MagicMock()
        read = AsyncMock(return_value="REFRESH")

        with patch(
            "custom_components.homeclaw.providers.anthropic_oauth.auth.refresh_with_retry",
            side_effect=fake_refresh,
        ):
            r1 = await gate.refresh(session, read)
            r2 = await gate.refresh(session, read)

        assert r1.access_token == "A1"
        assert r2.access_token == "A2"

    async def test_exception_propagates_to_all_waiters(self):
        gate = InflightRefreshGate()

        async def failing_refresh(session, read):
            await asyncio.sleep(0.01)
            raise OAuthRefreshError("nope", is_permanent=True)

        session = MagicMock()
        read = AsyncMock(return_value="REFRESH")

        with patch(
            "custom_components.homeclaw.providers.anthropic_oauth.auth.refresh_with_retry",
            side_effect=failing_refresh,
        ):
            results = await asyncio.gather(
                *[gate.refresh(session, read) for _ in range(3)],
                return_exceptions=True,
            )

        assert all(isinstance(r, OAuthRefreshError) for r in results)
```

- [ ] **Step 4.10: Run tests — refresh + gate tests fail**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py -v`
Expected: TestRefreshWithRetry + TestInflightRefreshGate FAIL on import.

- [ ] **Step 4.11: Append refresh + gate to auth.py**

```python
_NETWORK_ERRORS = (
    aiohttp.ClientConnectionError,
    aiohttp.ServerDisconnectedError,
    aiohttp.ClientPayloadError,
    asyncio.TimeoutError,
)


async def _do_refresh(
    session: aiohttp.ClientSession, refresh_token_value: str
) -> TokenSet:
    """Single refresh attempt — raises on any failure."""
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
        "client_id": CLIENT_ID,
    }
    async with session.post(TOKEN_URL, json=payload, headers=_TOKEN_HEADERS) as resp:
        if resp.status >= 500:
            # Treat as network-level transient — let outer retry handle.
            raise aiohttp.ServerDisconnectedError(f"5xx: {resp.status}")
        if resp.status != 200:
            body = await resp.text()
            is_permanent = '"error":"invalid_grant"' in body
            raise OAuthRefreshError(
                f"Token refresh failed: {resp.status} — {body[:300]}",
                is_permanent=is_permanent,
            )
        data = await resp.json()

    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", refresh_token_value),
        expires_at=time.time() + data.get("expires_in", 28800),
    )


async def refresh_with_retry(
    session: aiohttp.ClientSession,
    read_refresh_token: Callable[[], Awaitable[str]],
) -> TokenSet:
    """Refresh access token with network retry + fresh refresh-token re-read.

    Args:
        session: aiohttp session.
        read_refresh_token: zero-arg async callable that returns the current
            refresh token from persistent storage. Called per attempt so
            concurrent rotations are picked up (v1.7.4 fix).

    Raises:
        OAuthRefreshError: on permanent failure or exhausted retries.
    """
    last_error: Exception | None = None
    for attempt in range(REFRESH_MAX_RETRIES + 1):
        if attempt > 0:
            await asyncio.sleep(REFRESH_BASE_DELAY_S * (2 ** (attempt - 1)))

        current_refresh = await read_refresh_token()
        if not current_refresh:
            raise OAuthRefreshError("No refresh token available", is_permanent=True)

        try:
            return await _do_refresh(session, current_refresh)
        except _NETWORK_ERRORS as err:
            last_error = err
            continue
        except OAuthRefreshError as err:
            if err.is_permanent:
                raise
            last_error = err
            continue

    raise OAuthRefreshError(
        f"Token refresh exhausted {REFRESH_MAX_RETRIES} retries: {last_error}",
        is_permanent=False,
    )


class InflightRefreshGate:
    """Coalesces concurrent refresh attempts into a single in-flight request.

    Without this: N concurrent /v1/messages requests find token expired ->
    N simultaneous refresh requests -> Anthropic rotates N times -> N-1
    waiters get stale tokens -> 401 cascade.

    With this: first caller triggers refresh, others await the same task,
    everyone gets the same fresh access token.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task[TokenSet] | None = None
        self._lock = asyncio.Lock()

    async def refresh(
        self,
        session: aiohttp.ClientSession,
        read_refresh_token: Callable[[], Awaitable[str]],
    ) -> TokenSet:
        async with self._lock:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(
                    refresh_with_retry(session, read_refresh_token)
                )
        try:
            return await self._task
        finally:
            async with self._lock:
                if self._task is not None and self._task.done():
                    self._task = None
```

- [ ] **Step 4.12: Run tests — refresh + gate tests pass**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py -v`
Expected: TestRefreshWithRetry (6 tests) + TestInflightRefreshGate (3 tests) PASS.

### Task 4d: create_api_key

- [ ] **Step 4.13: Append create_api_key tests**

```python
class TestCreateApiKey:
    async def test_success_returns_raw_key(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 200
        ctx.__aenter__.return_value.json = AsyncMock(return_value={"raw_key": "sk-ant-XYZ"})
        session.post = MagicMock(return_value=ctx)

        result = await create_api_key(session, "ACCESS")
        assert result == "sk-ant-XYZ"

    async def test_http_error_raises_permanent(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 403
        ctx.__aenter__.return_value.text = AsyncMock(return_value="forbidden")
        session.post = MagicMock(return_value=ctx)

        with pytest.raises(OAuthRefreshError) as exc:
            await create_api_key(session, "ACCESS")
        assert exc.value.is_permanent is True
```

- [ ] **Step 4.14: Run tests — fail**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py::TestCreateApiKey -v`
Expected: FAIL.

- [ ] **Step 4.15: Append create_api_key to auth.py**

```python
async def create_api_key(session: aiohttp.ClientSession, access_token: str) -> str:
    """Exchange OAuth access token for permanent API key (Console flow).

    Used by the "Create an API Key" auth method — user can then use the
    regular AnthropicProvider (x-api-key) without OAuth refresh forever.
    """
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {access_token}",
    }
    async with session.post(CREATE_API_KEY_URL, headers=headers) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise OAuthRefreshError(
                f"API key creation failed: {resp.status} — {body[:300]}",
                is_permanent=True,
            )
        data = await resp.json()
    return data["raw_key"]
```

- [ ] **Step 4.16: Run all auth tests**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_auth.py -v`
Expected: ~28 tests PASS.

- [ ] **Step 4.17: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic_oauth/auth.py \
        tests/test_providers/test_anthropic_oauth/test_auth.py
git commit -m "add anthropic oauth auth helpers with refresh retry and inflight gate"
```

---

## Task 5: Transform helpers (sanitization + tool prefix + headers + URL)

Split into 4 sub-cycles for manageability.

**Files:**
- Create: `custom_components/homeclaw/providers/anthropic_oauth/transform.py`
- Create: `tests/test_providers/test_anthropic_oauth/test_transform.py`

### Task 5a: Tool name prefix/unprefix

- [ ] **Step 5.1: Write initial test_transform.py**

```python
"""Tests for anthropic_oauth.transform."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from custom_components.homeclaw.providers.anthropic_oauth.constants import (
    CLAUDE_CODE_IDENTITY,
    REQUIRED_BETAS,
    USER_AGENT,
)


class TestPrefixToolName:
    def test_simple_name(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prefix_tool_name
        assert prefix_tool_name("memory") == "mcp__homeclaw__memory"

    def test_snake_case_preserved(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prefix_tool_name
        assert prefix_tool_name("ha_native") == "mcp__homeclaw__ha_native"
        assert prefix_tool_name("shell_execute") == "mcp__homeclaw__shell_execute"


class TestUnprefixToolName:
    def test_strips_prefix(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import unprefix_tool_name
        assert unprefix_tool_name("mcp__homeclaw__memory") == "memory"

    def test_idempotent_when_unprefixed(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import unprefix_tool_name
        assert unprefix_tool_name("memory") == "memory"

    def test_preserves_snake_case(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import unprefix_tool_name
        assert unprefix_tool_name("mcp__homeclaw__ha_native") == "ha_native"


class TestPrefixToolNamesInPayload:
    def test_prefixes_tools_array(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )
        payload = {"tools": [{"name": "memory", "description": "x"}]}
        prefix_tool_names_in_payload(payload)
        assert payload["tools"][0]["name"] == "mcp__homeclaw__memory"

    def test_prefixes_tool_use_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )
        payload = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": "1", "name": "memory", "input": {}}
                    ],
                }
            ]
        }
        prefix_tool_names_in_payload(payload)
        assert payload["messages"][0]["content"][0]["name"] == "mcp__homeclaw__memory"

    def test_leaves_tool_result_blocks_alone(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "1", "content": "ok"}
                    ],
                }
            ]
        }
        prefix_tool_names_in_payload(payload)
        # tool_result has no `name` field — nothing to do
        assert payload["messages"][0]["content"][0] == {
            "type": "tool_result", "tool_use_id": "1", "content": "ok"
        }

    def test_no_tools_no_messages_does_nothing(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )
        payload = {"model": "x"}
        prefix_tool_names_in_payload(payload)
        assert payload == {"model": "x"}


class TestUnprefixToolNamesInEvent:
    def test_unprefixes_content_block_start(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            unprefix_tool_names_in_event,
        )
        event = {
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "id": "1", "name": "mcp__homeclaw__memory"},
        }
        unprefix_tool_names_in_event(event)
        assert event["content_block"]["name"] == "memory"

    def test_no_op_for_text_delta_event(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            unprefix_tool_names_in_event,
        )
        event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}}
        unprefix_tool_names_in_event(event)
        assert event == {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}}


class TestUnprefixToolNamesInResponse:
    def test_unprefixes_tool_use_in_content(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            unprefix_tool_names_in_response,
        )
        data = {
            "content": [
                {"type": "text", "text": "let me check"},
                {"type": "tool_use", "id": "1", "name": "mcp__homeclaw__memory", "input": {}},
            ]
        }
        unprefix_tool_names_in_response(data)
        assert data["content"][1]["name"] == "memory"
        assert data["content"][0] == {"type": "text", "text": "let me check"}
```

- [ ] **Step 5.2: Run tests — FAIL**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v`
Expected: FAIL on import.

- [ ] **Step 5.3: Write initial transform.py with tool prefix functions**

```python
"""Request/response transforms for Anthropic OAuth.

Ported from opencode-anthropic-auth v1.8.0 src/transform.ts (MIT, © Ex Machina).
"""
from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .cch import build_billing_header_value
from .constants import (
    CLAUDE_CODE_IDENTITY,
    OPENCODE_IDENTITY_PREFIX,
    PARAGRAPH_REMOVAL_ANCHORS,
    REQUIRED_BETAS,
    TEXT_REPLACEMENTS,
    TOOL_PREFIX,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


# ---------- Tool name prefixing ----------

def prefix_tool_name(name: str) -> str:
    """Prefix a tool name with the homeclaw MCP namespace.

    Examples:
        ``ha_native`` -> ``mcp__homeclaw__ha_native``
        ``memory`` -> ``mcp__homeclaw__memory``
    """
    return f"{TOOL_PREFIX}{name}"


def unprefix_tool_name(name: str) -> str:
    """Reverse prefix_tool_name. Idempotent if prefix not present."""
    if name.startswith(TOOL_PREFIX):
        return name[len(TOOL_PREFIX):]
    return name


def prefix_tool_names_in_payload(payload: dict[str, Any]) -> None:
    """Mutate payload in-place: prefix all outgoing tool names."""
    tools = payload.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict) and isinstance(tool.get("name"), str):
                tool["name"] = prefix_tool_name(tool["name"])

    messages = payload.get("messages")
    if not isinstance(messages, list):
        return
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and isinstance(block.get("name"), str)
            ):
                block["name"] = prefix_tool_name(block["name"])


def unprefix_tool_names_in_event(event: dict[str, Any]) -> None:
    """Mutate streaming event in-place: strip tool prefix from tool_use names."""
    block = event.get("content_block")
    if (
        isinstance(block, dict)
        and block.get("type") == "tool_use"
        and isinstance(block.get("name"), str)
    ):
        block["name"] = unprefix_tool_name(block["name"])


def unprefix_tool_names_in_response(data: dict[str, Any]) -> None:
    """Mutate non-streaming response in-place: strip prefix from tool_use names."""
    content = data.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and isinstance(block.get("name"), str)
        ):
            block["name"] = unprefix_tool_name(block["name"])
```

- [ ] **Step 5.4: Run tests — tool prefix tests pass**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v -k "prefix or unprefix"`
Expected: ~13 tool tests PASS.

### Task 5b: System prompt sanitization

- [ ] **Step 5.5: Append sanitization tests**

```python
class TestSanitizeSystemText:
    def test_drops_opencode_identity_paragraph(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        text = "Para1\n\nYou are OpenCode, an agent.\n\nPara3"
        result = sanitize_system_text(text)
        assert "OpenCode" not in result
        assert "Para1" in result
        assert "Para3" in result

    def test_drops_paragraph_with_anomalyco_anchor(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        text = "Keep me\n\nFeedback at github.com/anomalyco/opencode/issues\n\nKeep me too"
        result = sanitize_system_text(text)
        assert "github.com/anomalyco/opencode" not in result
        assert "Keep me" in result
        assert "Keep me too" in result

    def test_drops_paragraph_with_opencode_docs_anchor(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        text = "Useful\n\nDocs: opencode.ai/docs/agents\n\nMore"
        result = sanitize_system_text(text)
        assert "opencode.ai/docs" not in result

    def test_critical_phrase_v175_replacement(self):
        """v1.7.5 critical phrase rewrite — must trigger to bypass classifier."""
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        text = "Here is some useful information about the environment you are running in:\nLinux x86_64"
        result = sanitize_system_text(text)
        assert "Environment context you are running in:" in result
        assert "useful information about the environment" not in result

    def test_inline_opencode_replacement(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        text = "Be honest if OpenCode honestly does not know."
        result = sanitize_system_text(text)
        assert "if the assistant honestly" in result
        assert "OpenCode" not in result

    def test_empty_input_returns_empty(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        assert sanitize_system_text("") == ""

    def test_only_whitespace_returns_empty(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text
        assert sanitize_system_text("   \n\n   ") == ""


class TestPrependClaudeCodeIdentity:
    def test_none_returns_only_identity_block(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        result = prepend_claude_code_identity(None)
        assert result == [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]

    def test_string_with_content(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        result = prepend_claude_code_identity("You are a helpful assistant.")
        assert len(result) == 2
        assert result[0]["text"] == CLAUDE_CODE_IDENTITY
        assert result[1]["text"] == "You are a helpful assistant."

    def test_empty_string_collapses_to_identity_only(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        result = prepend_claude_code_identity("")
        assert result == [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]

    def test_list_of_text_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        system = [
            {"type": "text", "text": "First block."},
            {"type": "text", "text": "Second block."},
        ]
        result = prepend_claude_code_identity(system)
        assert len(result) == 3
        assert result[0]["text"] == CLAUDE_CODE_IDENTITY
        assert result[1]["text"] == "First block."
        assert result[2]["text"] == "Second block."

    def test_idempotent_when_first_block_is_identity(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        system = [
            {"type": "text", "text": CLAUDE_CODE_IDENTITY},
            {"type": "text", "text": "Existing."},
        ]
        result = prepend_claude_code_identity(system)
        assert len(result) == 2
        assert result[0]["text"] == CLAUDE_CODE_IDENTITY

    def test_preserves_extra_fields_on_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        system = [{"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}]
        result = prepend_claude_code_identity(system)
        assert result[1]["cache_control"] == {"type": "ephemeral"}

    def test_sanitizes_content_in_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity
        system = [{"type": "text", "text": "Here is some useful information about the environment you are running in:"}]
        result = prepend_claude_code_identity(system)
        assert "Environment context" in result[1]["text"]
```

- [ ] **Step 5.6: Run tests — sanitization tests fail**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v -k "Sanitize or Prepend"`
Expected: FAIL.

- [ ] **Step 5.7: Append sanitization to transform.py**

```python
# ---------- System prompt sanitization ----------

def sanitize_system_text(text: str) -> str:
    """Sanitize OpenCode-branded strings from system prompt text.

    Three-phase pipeline (matches TS reference):
    1. Drop paragraph containing OPENCODE_IDENTITY_PREFIX.
    2. Drop paragraphs whose text contains any PARAGRAPH_REMOVAL_ANCHORS.
    3. Apply inline TEXT_REPLACEMENTS (incl. critical phrase rewrite
       that unblocks Anthropic's third-party agent classifier).
    """
    paragraphs = text.split("\n\n")
    kept: list[str] = []
    for p in paragraphs:
        if OPENCODE_IDENTITY_PREFIX in p:
            continue
        if any(anchor in p for anchor in PARAGRAPH_REMOVAL_ANCHORS):
            continue
        kept.append(p)

    result = "\n\n".join(kept)
    for match, replacement in TEXT_REPLACEMENTS:
        result = result.replace(match, replacement)
    return result.strip()


def prepend_claude_code_identity(system: Any) -> list[dict[str, Any]]:
    """Sanitize system prompt and prepend Claude Code identity block.

    Handles all three Anthropic ``system`` field formats:
    - None / missing: returns single identity block.
    - String: wrap as block, sanitize, prepend identity.
    - List of blocks: sanitize each text block, prepend identity (idempotent
      — won't double-prepend if first block already contains identity).
    """
    identity_block = {"type": "text", "text": CLAUDE_CODE_IDENTITY}

    if system is None:
        return [identity_block]

    if isinstance(system, str):
        sanitized = sanitize_system_text(system)
        if not sanitized or sanitized == CLAUDE_CODE_IDENTITY:
            return [identity_block]
        return [identity_block, {"type": "text", "text": sanitized}]

    if not isinstance(system, list):
        return [identity_block]

    sanitized_blocks: list[dict[str, Any]] = []
    for item in system:
        if isinstance(item, str):
            sanitized_blocks.append({"type": "text", "text": sanitize_system_text(item)})
        elif (
            isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        ):
            sanitized_blocks.append({**item, "text": sanitize_system_text(item["text"])})
        else:
            sanitized_blocks.append({"type": "text", "text": str(item)})

    if sanitized_blocks and sanitized_blocks[0].get("text") == CLAUDE_CODE_IDENTITY:
        return sanitized_blocks
    return [identity_block, *sanitized_blocks]
```

- [ ] **Step 5.8: Run tests — sanitization tests pass**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v -k "Sanitize or Prepend"`
Expected: ~14 tests PASS.

### Task 5c: Header management + URL rewriting

- [ ] **Step 5.9: Append header + URL tests**

```python
class TestMergeBetaHeaders:
    def test_none_returns_required_only(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers
        result = merge_beta_headers(None)
        assert result == ",".join(REQUIRED_BETAS)

    def test_existing_appended(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers
        result = merge_beta_headers("custom-beta-1,foo")
        parts = result.split(",")
        for required in REQUIRED_BETAS:
            assert required in parts
        assert "custom-beta-1" in parts
        assert "foo" in parts

    def test_dedupes_required_collision(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers
        result = merge_beta_headers("oauth-2025-04-20,extra")
        parts = result.split(",")
        assert parts.count("oauth-2025-04-20") == 1
        assert "extra" in parts

    def test_empty_string_treated_as_none(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers
        result = merge_beta_headers("")
        assert result == ",".join(REQUIRED_BETAS)


class TestBuildOauthHeaders:
    def test_required_headers_set(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers
        h = build_oauth_headers("ACCESS")
        assert h["authorization"] == "Bearer ACCESS"
        assert h["content-type"] == "application/json"
        assert h["anthropic-version"] == "2023-06-01"
        assert h["user-agent"] == USER_AGENT
        for required in REQUIRED_BETAS:
            assert required in h["anthropic-beta"]

    def test_drops_x_api_key_from_extra(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers
        h = build_oauth_headers("ACCESS", extra={"x-api-key": "leaked"})
        assert "x-api-key" not in h

    def test_extra_headers_preserved(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers
        h = build_oauth_headers("ACCESS", extra={"x-custom": "v"})
        assert h["x-custom"] == "v"

    def test_extra_betas_merged(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers
        h = build_oauth_headers("ACCESS", extra={"anthropic-beta": "extra-beta"})
        assert "extra-beta" in h["anthropic-beta"]
        for required in REQUIRED_BETAS:
            assert required in h["anthropic-beta"]


class TestRewriteUrl:
    def test_v1_messages_gets_beta_query(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url
        result = rewrite_url("https://api.anthropic.com/v1/messages")
        assert "beta=true" in result

    def test_existing_beta_query_not_doubled(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url
        result = rewrite_url("https://api.anthropic.com/v1/messages?beta=true")
        # Should still have exactly one beta param
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(result).query)
        assert qs["beta"] == ["true"]

    def test_other_path_not_modified_when_no_base_url(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            result = rewrite_url("https://api.anthropic.com/v1/models")
            assert "beta" not in result

    def test_base_url_override(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "http://localhost:8080"}):
            result = rewrite_url("https://api.anthropic.com/v1/messages")
            assert result.startswith("http://localhost:8080/v1/messages")
            assert "beta=true" in result


class TestResolveBaseUrl:
    def test_unset_returns_none(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            assert _resolve_base_url() is None

    def test_valid_https_returned(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://proxy.example.com"}):
            assert _resolve_base_url() == "https://proxy.example.com"

    def test_userinfo_rejected(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://user:pass@proxy.com"}):
            assert _resolve_base_url() is None

    def test_non_http_scheme_rejected(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "ftp://proxy.com"}):
            assert _resolve_base_url() is None


class TestIsTlsInsecure:
    def test_no_base_url_means_secure(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import is_tls_insecure
        with patch.dict(os.environ, {"ANTHROPIC_INSECURE": "1"}, clear=False):
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            assert is_tls_insecure() is False

    def test_with_base_url_and_flag(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import is_tls_insecure
        with patch.dict(os.environ, {
            "ANTHROPIC_BASE_URL": "http://localhost",
            "ANTHROPIC_INSECURE": "true",
        }):
            assert is_tls_insecure() is True

    def test_with_base_url_no_flag(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import is_tls_insecure
        with patch.dict(os.environ, {
            "ANTHROPIC_BASE_URL": "http://localhost",
        }, clear=False):
            os.environ.pop("ANTHROPIC_INSECURE", None)
            assert is_tls_insecure() is False
```

- [ ] **Step 5.10: Run tests — header/URL tests fail**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v -k "MergeBeta or BuildOauth or RewriteUrl or ResolveBase or IsTls"`
Expected: FAIL.

- [ ] **Step 5.11: Append header + URL helpers to transform.py**

```python
# ---------- Header management ----------

def merge_beta_headers(existing: str | None) -> str:
    """Merge required OAuth betas with any incoming anthropic-beta value, dedupe."""
    incoming = [b.strip() for b in (existing or "").split(",") if b.strip()]
    seen: dict[str, None] = {}  # ordered dedup (Python 3.7+ dict preserves order)
    for beta in (*REQUIRED_BETAS, *incoming):
        seen.setdefault(beta, None)
    return ",".join(seen.keys())


def build_oauth_headers(
    access_token: str, *, extra: dict[str, str] | None = None
) -> dict[str, str]:
    """Build full request headers for /v1/messages with OAuth token.

    Drops any incoming x-api-key (we're using Bearer); sets authorization,
    merged anthropic-beta, user-agent, content-type, anthropic-version.
    """
    base: dict[str, str] = {
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": merge_beta_headers((extra or {}).get("anthropic-beta")),
        "user-agent": USER_AGENT,
    }
    if extra:
        for key, value in extra.items():
            lower = key.lower()
            if lower == "x-api-key":
                continue
            if lower in {"authorization", "anthropic-beta", "user-agent"}:
                continue
            base[lower] = value
    return base


# ---------- URL rewriting ----------

def _resolve_base_url() -> str | None:
    """Read ANTHROPIC_BASE_URL env var. Returns origin (scheme://host) or None.

    Validates: must be http/https, no userinfo. Mirrors TS behavior.
    """
    raw = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username or parsed.password:
        return None
    if not parsed.hostname:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def is_tls_insecure() -> bool:
    """Skip TLS verify only when ANTHROPIC_BASE_URL set AND ANTHROPIC_INSECURE in {1,true}."""
    if not _resolve_base_url():
        return False
    raw = os.environ.get("ANTHROPIC_INSECURE", "").strip().lower()
    return raw in {"1", "true"}


def rewrite_url(url: str) -> str:
    """Apply env-driven base URL override and add ?beta=true for /v1/messages."""
    parsed = urlparse(url)
    base = _resolve_base_url()
    if base:
        base_parsed = urlparse(base)
        parsed = parsed._replace(scheme=base_parsed.scheme, netloc=base_parsed.netloc)

    if parsed.path == "/v1/messages":
        qs = parse_qs(parsed.query)
        if "beta" not in qs:
            qs["beta"] = ["true"]
            parsed = parsed._replace(query=urlencode(qs, doseq=True))

    return urlunparse(parsed)
```

- [ ] **Step 5.12: Run tests — header/URL tests pass**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v`
Expected: header/URL tests PASS (~17 more tests).

### Task 5d: Top-level transform_request_payload

- [ ] **Step 5.13: Append payload transform tests**

```python
class TestTransformRequestPayload:
    def test_user_message_produces_billing_block(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload
        payload = {
            "messages": [{"role": "user", "content": "hello"}],
            "system": "You are helpful.",
        }
        result = transform_request_payload(payload)
        assert isinstance(result["system"], list)
        assert result["system"][0]["text"].startswith("x-anthropic-billing-header:")
        assert result["system"][1]["text"] == CLAUDE_CODE_IDENTITY
        assert result["system"][2]["text"] == "You are helpful."

    def test_no_user_message_no_billing(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload
        payload = {
            "messages": [{"role": "assistant", "content": "hi"}],
            "system": "S",
        }
        result = transform_request_payload(payload)
        assert result["system"][0]["text"] == CLAUDE_CODE_IDENTITY  # no billing prepended
        assert result["system"][1]["text"] == "S"

    def test_tools_prefixed(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload
        payload = {
            "messages": [{"role": "user", "content": "x"}],
            "tools": [{"name": "memory", "description": "d"}],
        }
        result = transform_request_payload(payload)
        assert result["tools"][0]["name"] == "mcp__homeclaw__memory"

    def test_billing_header_uses_first_user_text(self):
        """Billing computed BEFORE prefixing — first user message text matters."""
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload
        from custom_components.homeclaw.providers.anthropic_oauth.cch import compute_cch
        payload = {
            "messages": [{"role": "user", "content": "specific message"}],
        }
        result = transform_request_payload(payload)
        billing = result["system"][0]["text"]
        expected_cch = compute_cch("specific message")
        assert f"cch={expected_cch};" in billing

    def test_returns_same_dict(self):
        """Mutates and returns payload (allows chaining)."""
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload
        payload = {"messages": [{"role": "user", "content": "x"}]}
        result = transform_request_payload(payload)
        assert result is payload
```

- [ ] **Step 5.14: Run — fail**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v -k "TransformRequest"`
Expected: FAIL.

- [ ] **Step 5.15: Append transform_request_payload to transform.py**

```python
# ---------- Top-level payload transform ----------

def transform_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply all outgoing transforms to a /v1/messages payload.

    Mutates and returns the payload dict. Order:
    1. Compute billing header from first user message text BEFORE prefix changes.
    2. Sanitize + prepend identity to system.
    3. Prepend billing header as system block (becomes system[0]).
    4. Prefix tool names (tools[] and tool_use messages).
    """
    messages = payload.get("messages") or []
    has_user = any(
        isinstance(m, dict) and m.get("role") == "user" for m in messages
    )
    billing_header_text = build_billing_header_value(messages) if has_user else None

    payload["system"] = prepend_claude_code_identity(payload.get("system"))

    if billing_header_text is not None:
        payload["system"].insert(0, {"type": "text", "text": billing_header_text})

    prefix_tool_names_in_payload(payload)
    return payload
```

- [ ] **Step 5.16: Run all transform tests**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_transform.py -v`
Expected: all ~32 tests PASS.

- [ ] **Step 5.17: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic_oauth/transform.py \
        tests/test_providers/test_anthropic_oauth/test_transform.py
git commit -m "add transform helpers for sanitization tool prefix and headers"
```

---

## Task 6: Provider class + delete old files + update config_flow imports

The atomic "swap" commit. Adds provider.py + __init__.py public API, deletes old `oauth.py`, old `providers/anthropic_oauth.py`, old test file. Updates `config_flow.py` imports (still using same Pro/Max flow — new step added in Task 7).

**Files:**
- Create: `custom_components/homeclaw/providers/anthropic_oauth/provider.py`
- Modify: `custom_components/homeclaw/providers/anthropic_oauth/__init__.py` (real public exports)
- Create: `tests/test_providers/test_anthropic_oauth/test_provider.py`
- Modify: `custom_components/homeclaw/config_flow.py` (line 30 import)
- Delete: `custom_components/homeclaw/oauth.py`
- Delete: `custom_components/homeclaw/providers/anthropic_oauth.py`
- Delete: `tests/test_providers/test_anthropic_oauth.py`

- [ ] **Step 6.1: Verify config_flow.py current import line**

Run: `grep -n "from .oauth\|providers.anthropic_oauth\|providers/anthropic_oauth" custom_components/homeclaw/config_flow.py`

Expected output: line 30 references `from .oauth import generate_pkce, build_auth_url, exchange_code`.

If config_flow uses other functions from `oauth.py`, list them — they must be re-exported by new `__init__.py`.

- [ ] **Step 6.2: Write test_provider.py**

```python
"""Integration tests for AnthropicOAuthProvider."""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.providers.anthropic_oauth import AnthropicOAuthProvider
from custom_components.homeclaw.providers.anthropic_oauth.auth import OAuthRefreshError, TokenSet


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.data = {
        "anthropic_oauth": {
            "access_token": "ACCESS",
            "refresh_token": "REFRESH",
            "expires_at": time.time() + 3600,
        }
    }
    return entry


@pytest.fixture
def provider(mock_hass, mock_config_entry):
    return AnthropicOAuthProvider(
        mock_hass, {"config_entry": mock_config_entry, "model": "claude-sonnet-4-20250514"}
    )


class TestInit:
    def test_default_model(self, mock_hass, mock_config_entry):
        p = AnthropicOAuthProvider(mock_hass, {"config_entry": mock_config_entry})
        assert p._model == AnthropicOAuthProvider.DEFAULT_MODEL

    def test_custom_model(self, mock_hass, mock_config_entry):
        p = AnthropicOAuthProvider(
            mock_hass, {"config_entry": mock_config_entry, "model": "claude-opus-4-1"}
        )
        assert p._model == "claude-opus-4-1"

    def test_supports_tools(self, provider):
        assert provider.supports_tools is True


class TestTokenManagement:
    def test_read_oauth_data_returns_fresh(self, provider, mock_config_entry):
        # Simulate config_entry mutation between reads
        mock_config_entry.data = {
            "anthropic_oauth": {"access_token": "NEW", "refresh_token": "RNEW", "expires_at": 9e9}
        }
        result = provider._read_oauth_data()
        assert result["access_token"] == "NEW"

    async def test_get_valid_access_token_cached(self, provider):
        # Token valid in window — no refresh
        token = await provider._get_valid_access_token()
        assert token == "ACCESS"

    async def test_get_valid_access_token_triggers_refresh(self, provider, mock_config_entry):
        mock_config_entry.data = {
            "anthropic_oauth": {
                "access_token": "OLD",
                "refresh_token": "REFRESH",
                "expires_at": time.time() - 1000,  # already expired
            }
        }
        new_tokens = TokenSet("FRESH", "NEW_REFRESH", time.time() + 3600)
        with patch.object(provider._refresh_gate, "refresh", AsyncMock(return_value=new_tokens)):
            token = await provider._get_valid_access_token()
        assert token == "FRESH"
        # Verify persistence call
        provider.hass.config_entries.async_update_entry.assert_called_once()
        call_args = provider.hass.config_entries.async_update_entry.call_args
        assert call_args.kwargs["data"]["anthropic_oauth"]["access_token"] == "FRESH"
        assert call_args.kwargs["data"]["anthropic_oauth"]["refresh_token"] == "NEW_REFRESH"

    async def test_permanent_failure_triggers_reauth(self, provider, mock_config_entry):
        mock_config_entry.data = {
            "anthropic_oauth": {"access_token": "", "refresh_token": "", "expires_at": 0}
        }
        with patch.object(
            provider._refresh_gate,
            "refresh",
            AsyncMock(side_effect=OAuthRefreshError("dead", is_permanent=True)),
        ):
            with pytest.raises(OAuthRefreshError):
                await provider._get_valid_access_token()
        mock_config_entry.async_start_reauth.assert_called_once_with(provider.hass)


class TestGetResponse:
    async def test_happy_path_assembles_correct_request(self, provider):
        with patch.object(
            provider, "_get_valid_access_token", AsyncMock(return_value="ACCESS")
        ):
            ctx = AsyncMock()
            ctx.__aenter__.return_value.status = 200
            ctx.__aenter__.return_value.text = AsyncMock(return_value=json.dumps({
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }))
            captured = {}

            def capture_post(url, headers=None, json=None, timeout=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return ctx

            session_ctx = AsyncMock()
            session_mock = MagicMock()
            session_mock.post = MagicMock(side_effect=capture_post)
            session_ctx.__aenter__.return_value = session_mock

            with patch("aiohttp.ClientSession", return_value=session_ctx):
                await provider.get_response(
                    [{"role": "user", "content": "hello"}],
                )

        # Assertions on captured payload/headers
        assert "?beta=true" in captured["url"]
        assert captured["headers"]["authorization"] == "Bearer ACCESS"
        assert "oauth-2025-04-20" in captured["headers"]["anthropic-beta"]
        assert captured["headers"]["user-agent"] == "claude-cli/2.1.87 (external, cli)"
        # System should be a list with billing + identity
        sys_blocks = captured["json"]["system"]
        assert sys_blocks[0]["text"].startswith("x-anthropic-billing-header:")
        assert "Claude Agent SDK" in sys_blocks[1]["text"]
```

- [ ] **Step 6.3: Run tests — FAIL on import**

Run: `pytest tests/test_providers/test_anthropic_oauth/test_provider.py -v`
Expected: FAIL on import (provider.py doesn't exist).

- [ ] **Step 6.4: Write provider.py**

```python
"""AnthropicOAuthProvider — HA-aware glue around the OAuth modules.

Ported from opencode-anthropic-auth v1.8.0 src/index.ts (MIT, © Ex Machina).
"""
from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

import aiohttp

from ..adapters.anthropic_adapter import AnthropicAdapter
from ..adapters.stream_utils import SSEParser, ToolAccumulator
from ..registry import AIProvider, ProviderRegistry
from .auth import InflightRefreshGate, OAuthRefreshError, TokenSet
from .transform import (
    build_oauth_headers,
    is_tls_insecure,
    rewrite_url,
    transform_request_payload,
    unprefix_tool_names_in_event,
    unprefix_tool_names_in_response,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_BASE_API_URL = "https://api.anthropic.com/v1/messages"
_OAUTH_DATA_KEY = "anthropic_oauth"


@ProviderRegistry.register("anthropic_oauth")
class AnthropicOAuthProvider(AIProvider):
    """Anthropic provider using Claude Pro/Max OAuth credentials."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 8192

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._max_tokens = config.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self._config_entry: ConfigEntry | None = config.get("config_entry")
        self._refresh_gate = InflightRefreshGate()
        self.adapter = AnthropicAdapter()

    @property
    def supports_tools(self) -> bool:
        return True

    # ---------- Token management ----------

    def _read_oauth_data(self) -> dict[str, Any]:
        """Re-read latest OAuth tokens from config entry storage."""
        if not self._config_entry:
            return {}
        return dict(self._config_entry.data.get(_OAUTH_DATA_KEY, {}))

    async def _read_refresh_token(self) -> str:
        """Callback for InflightRefreshGate: returns current refresh token."""
        return self._read_oauth_data().get("refresh_token", "")

    def _persist_tokens(self, tokens: TokenSet) -> None:
        """Write refreshed tokens back to config entry IMMEDIATELY.

        Anthropic rotates the refresh token on each use — we must persist
        before the next request, otherwise concurrent refreshers may use
        a revoked token.
        """
        if not self._config_entry:
            return
        new_oauth = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        }
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={**self._config_entry.data, _OAUTH_DATA_KEY: new_oauth},
        )

    def _trigger_reauth(self) -> None:
        if not self._config_entry:
            return
        try:
            self._config_entry.async_start_reauth(self.hass)
            _LOGGER.warning(
                "Anthropic OAuth: triggered re-authentication — "
                "check Home Assistant notifications"
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not trigger reauth flow", exc_info=True)

    async def _get_valid_access_token(self) -> str:
        """Return a valid access token, refreshing if needed.

        Concurrent callers coalesce on a single in-flight refresh via
        InflightRefreshGate — prevents 401 cascades from token rotation.
        """
        oauth = self._read_oauth_data()
        access = oauth.get("access_token", "")
        expires_at = oauth.get("expires_at", 0)

        # 5-minute safety buffer.
        if access and time.time() < expires_at - 300:
            return access

        async with aiohttp.ClientSession() as session:
            try:
                tokens = await self._refresh_gate.refresh(session, self._read_refresh_token)
            except OAuthRefreshError as err:
                _LOGGER.error("Anthropic OAuth refresh failed: %s", err)
                if err.is_permanent:
                    self._trigger_reauth()
                raise

        self._persist_tokens(tokens)
        return tokens.access_token

    # ---------- Request execution ----------

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        *,
        stream: bool,
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        anthropic_messages, system_message = self.adapter.transform_messages(messages)
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self.config.get("temperature", 0.2),
            "messages": anthropic_messages,
            "system": system_message,
        }
        if stream:
            payload["stream"] = True
        if tools:
            anthropic_tools = self.adapter.transform_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        return transform_request_payload(payload)

    def _build_session(self) -> aiohttp.ClientSession:
        connector = aiohttp.TCPConnector(ssl=False) if is_tls_insecure() else None
        return aiohttp.ClientSession(connector=connector)

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        access_token = await self._get_valid_access_token()
        headers = build_oauth_headers(access_token)
        url = rewrite_url(_BASE_API_URL)
        payload = self._build_payload(messages, stream=False, tools=kwargs.get("tools"))

        _LOGGER.debug("Anthropic OAuth POST %s", url)

        async with self._build_session() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                response_text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error(
                        "Anthropic OAuth API error %d: %s", resp.status, response_text[:500]
                    )
                    raise RuntimeError(
                        f"Anthropic OAuth API error {resp.status}: {response_text[:200]}"
                    )
                data = json.loads(response_text)

        unprefix_tool_names_in_response(data)
        parsed = self.adapter.extract_response(data)
        return self.adapter.format_response_as_legacy_string(parsed)

    async def get_response_stream(self, messages: list[dict[str, Any]], **kwargs: Any):
        access_token = await self._get_valid_access_token()
        headers = build_oauth_headers(access_token)
        url = rewrite_url(_BASE_API_URL)
        payload = self._build_payload(messages, stream=True, tools=kwargs.get("tools"))

        sse_parser = SSEParser()
        tool_acc = ToolAccumulator()

        try:
            async with self._build_session() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.error(
                            "Anthropic OAuth stream API error %d: %s",
                            resp.status, error_text[:500],
                        )
                        yield {
                            "type": "error",
                            "message": f"Anthropic OAuth API error {resp.status}: {error_text[:200]}",
                        }
                        return

                    async for raw_chunk in resp.content.iter_any():
                        if not raw_chunk:
                            continue
                        for data_text in sse_parser.feed(
                            raw_chunk.decode("utf-8", errors="ignore")
                        ):
                            if data_text == "[DONE]":
                                break
                            try:
                                event_data = json.loads(data_text)
                            except (TypeError, ValueError, json.JSONDecodeError):
                                _LOGGER.debug(
                                    "Skipping unparsable Anthropic OAuth event: %s",
                                    data_text[:200],
                                )
                                continue
                            unprefix_tool_names_in_event(event_data)
                            for out_chunk in self.adapter.extract_stream_events(
                                event_data, tool_acc
                            ):
                                yield out_chunk

                    for data_text in sse_parser.flush():
                        try:
                            event_data = json.loads(data_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            continue
                        unprefix_tool_names_in_event(event_data)
                        for out_chunk in self.adapter.extract_stream_events(
                            event_data, tool_acc
                        ):
                            yield out_chunk

                    if tool_acc.has_pending:
                        for tc in tool_acc.flush_all():
                            yield {
                                "type": "tool_call",
                                "id": tc["id"],
                                "name": tc["name"],
                                "args": tc["args"],
                            }

        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Anthropic OAuth streaming exception: %s", err)
            yield {"type": "error", "message": str(err)}
```

- [ ] **Step 6.5: Update __init__.py with public API exports**

Replace `custom_components/homeclaw/providers/anthropic_oauth/__init__.py`:
```python
"""Anthropic OAuth subpackage for HomeClaw.

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
"""
from __future__ import annotations

from .auth import (
    AuthorizationRequest,
    OAuthRefreshError,
    TokenSet,
    authorize,
    create_api_key,
    exchange_code,
)
from .provider import AnthropicOAuthProvider

__all__ = [
    "AnthropicOAuthProvider",
    "AuthorizationRequest",
    "OAuthRefreshError",
    "TokenSet",
    "authorize",
    "create_api_key",
    "exchange_code",
    "is_oauth_zero_cost_provider",
]


def is_oauth_zero_cost_provider(provider_name: str) -> bool:
    """Provider names whose model usage is unlimited under OAuth subscription.

    Used by the Settings/Models UI to render cost as 0 for these providers.
    """
    return provider_name == "anthropic_oauth"
```

- [ ] **Step 6.6: Update config_flow.py imports and call sites**

The old `oauth.py` API was: `(verifier, challenge) = generate_pkce()`, `build_auth_url(challenge, verifier, mode)`, and `exchange_code(session, code, verifier)` returning a dict with `access_token`/`refresh_token`/`expires_at`/`error` keys.

The new API: `(request, pkce) = authorize(mode)` where request has `.url`, `.state`, `.verifier`, and `await exchange_code(session, code, verifier, expected_state=...)` returns a `TokenSet` dataclass (raises `OAuthRefreshError` on failure).

**Replace line 30:**
```python
# OLD
from .oauth import generate_pkce, build_auth_url, exchange_code
# NEW
from .providers.anthropic_oauth import authorize, exchange_code
from .providers.anthropic_oauth.auth import OAuthRefreshError
```

**Update lines ~146-152 in `_reauth_anthropic`:**
```python
# OLD
if not hasattr(self, "_pkce_verifier") or self._pkce_verifier is None:
    verifier, challenge = generate_pkce()
    self._pkce_verifier = verifier
    self._pkce_challenge = challenge
    self._auth_url = build_auth_url(
        self._pkce_challenge, self._pkce_verifier, mode="max"
    )
# NEW
if not hasattr(self, "_pkce_verifier") or self._pkce_verifier is None:
    request, pkce = authorize(mode="max")
    self._pkce_verifier = pkce.verifier
    self._pkce_challenge = pkce.challenge
    self._oauth_state = request.state
    self._auth_url = request.url
```

**Update lines ~159-176 in `_reauth_anthropic` (exchange_code call site):**
```python
# OLD
async with aiohttp.ClientSession() as session:
    result = await exchange_code(session, code, self._pkce_verifier)

if "error" in result:
    _LOGGER.error(
        "Reauth OAuth exchange failed: %s", result.get("error")
    )
    errors["base"] = "oauth_failed"
else:
    new_data = {
        **self._reauth_entry.data,
        "anthropic_oauth": {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "expires_at": result["expires_at"],
        },
    }
# NEW
try:
    async with aiohttp.ClientSession() as session:
        tokens = await exchange_code(
            session, code, self._pkce_verifier,
            expected_state=getattr(self, "_oauth_state", None),
        )
except OAuthRefreshError as err:
    _LOGGER.error("Reauth OAuth exchange failed: %s", err)
    errors["base"] = "oauth_failed"
else:
    new_data = {
        **self._reauth_entry.data,
        "anthropic_oauth": {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        },
    }
```

**Update lines ~471-485 in `async_step_anthropic_oauth` (mirror of above):**
Apply the SAME replacement pattern: PKCE init via `authorize(mode="max")` storing `_oauth_state`, and exchange wrapped in `try/except OAuthRefreshError`. Token data accessed via `tokens.access_token` etc. instead of `result["access_token"]`.

**DO NOT touch the Gemini OAuth lines (206, 209, 221, 542, 545, 563)** — they use `gemini_oauth.generate_pkce` etc., a separate module unaffected by this port.

Verify with: `grep -n "generate_pkce\|build_auth_url" custom_components/homeclaw/config_flow.py | grep -v gemini_oauth`
Expected: no matches (all Anthropic-side calls migrated; only `gemini_oauth.*` calls remain).

- [ ] **Step 6.7: Delete old files**

```bash
rm custom_components/homeclaw/oauth.py
rm custom_components/homeclaw/providers/anthropic_oauth.py
rm tests/test_providers/test_anthropic_oauth.py
```

- [ ] **Step 6.8: Run new provider tests + full provider tests**

Run: `pytest tests/test_providers/test_anthropic_oauth/ -v`
Expected: all module tests + provider tests PASS.

- [ ] **Step 6.9: Run full test suite to catch any breakage**

Run: `pytest tests/ -x --tb=short`
Expected: full suite PASS (or, if config_flow tests break, fix them before commit — config_flow.py changes may have broken existing tests for the OAuth step).

- [ ] **Step 6.10: Run lint and type check**

Run:
```bash
black --check --diff custom_components/homeclaw/providers/anthropic_oauth/ tests/test_providers/test_anthropic_oauth/
isort --check --diff custom_components/homeclaw/providers/anthropic_oauth/ tests/test_providers/test_anthropic_oauth/
flake8 custom_components/homeclaw/providers/anthropic_oauth/
```
Expected: green. Fix any issues with `black --line-length 127` and `isort --profile black`.

- [ ] **Step 6.11: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic_oauth/ \
        tests/test_providers/test_anthropic_oauth/ \
        custom_components/homeclaw/config_flow.py
git rm custom_components/homeclaw/oauth.py \
       custom_components/homeclaw/providers/anthropic_oauth.py \
       tests/test_providers/test_anthropic_oauth.py
git commit -m "port anthropic oauth provider to new subpackage"
```

---

## Task 7: Add Create API Key OAuth flow to config_flow.py

**Files:**
- Modify: `custom_components/homeclaw/config_flow.py`
- Modify: `tests/test_config_flow.py` (if exists; otherwise create it for the new step)

- [ ] **Step 7.1: Locate existing OAuth step structure**

Run: `grep -n "async_step_anthropic\|step_id.*anthropic" custom_components/homeclaw/config_flow.py`

Identify:
- The existing `async_step_anthropic_oauth` (Pro/Max flow)
- The choice point that selects "OAuth" vs "Manual API key"

- [ ] **Step 7.2: Write failing tests for new steps**

In `tests/test_config_flow.py` (or create `tests/test_config_flow_anthropic_oauth.py`):

```python
"""Tests for config_flow Anthropic OAuth method selection and Create API Key step."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.config_flow import HomeclawConfigFlow


class TestAnthropicMethodStep:
    async def test_shows_form_with_max_and_console_choices(self):
        flow = HomeclawConfigFlow()
        result = await flow.async_step_anthropic_method()
        assert result["type"] == "form"
        assert result["step_id"] == "anthropic_method"
        # Form should offer both options
        # (exact assertion depends on existing schema patterns in the file)


class TestAnthropicCreateKeyStep:
    async def test_shows_authorize_url(self):
        flow = HomeclawConfigFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_anthropic_create_key()
        assert result["type"] == "form"
        assert "auth_url" in result.get("description_placeholders", {})

    async def test_exchange_then_create_key_creates_anthropic_entry(self):
        flow = HomeclawConfigFlow()
        flow.hass = MagicMock()
        # First call to display the form
        await flow.async_step_anthropic_create_key()
        with patch(
            "custom_components.homeclaw.config_flow.exchange_code",
            AsyncMock(return_value=MagicMock(access_token="ACCESS")),
        ), patch(
            "custom_components.homeclaw.config_flow.create_api_key",
            AsyncMock(return_value="sk-ant-XYZ"),
        ):
            result = await flow.async_step_anthropic_create_key({"code": "callback#state"})
        assert result["type"] == "create_entry"
        assert result["data"]["provider"] == "anthropic"
        assert result["data"]["api_key"] == "sk-ant-XYZ"
```

- [ ] **Step 7.3: Run tests — expect FAIL (steps don't exist)**

Run: `pytest tests/test_config_flow_anthropic_oauth.py -v`
Expected: FAIL.

- [ ] **Step 7.4: Add new steps to config_flow.py**

Locate the existing `async_step_anthropic_oauth`. Add immediately above it:

```python
async def async_step_anthropic_method(self, user_input=None):
    """Choose between Pro/Max OAuth and Console (Create API Key)."""
    if user_input is not None:
        method = user_input["method"]
        if method == "max":
            return await self.async_step_anthropic_oauth()
        return await self.async_step_anthropic_create_key()

    return self.async_show_form(
        step_id="anthropic_method",
        data_schema=vol.Schema({
            vol.Required("method", default="max"): vol.In({
                "max": "Claude Pro/Max (subscription)",
                "console": "Console plan (generates permanent API key)",
            }),
        }),
    )

async def async_step_anthropic_create_key(self, user_input=None):
    """Console OAuth that exchanges access token for permanent API key."""
    from .providers.anthropic_oauth import authorize, create_api_key, exchange_code, OAuthRefreshError

    if not getattr(self, "_anthropic_create_key_request", None):
        request, _pkce = authorize(mode="console")
        self._anthropic_create_key_request = request

    request = self._anthropic_create_key_request

    if user_input is None:
        return self.async_show_form(
            step_id="anthropic_create_key",
            data_schema=vol.Schema({vol.Required("code"): str}),
            description_placeholders={"auth_url": request.url},
        )

    try:
        async with aiohttp.ClientSession() as session:
            tokens = await exchange_code(
                session,
                user_input["code"],
                request.verifier,
                expected_state=request.state,
            )
            api_key = await create_api_key(session, tokens.access_token)
    except OAuthRefreshError as err:
        return self.async_show_form(
            step_id="anthropic_create_key",
            data_schema=vol.Schema({vol.Required("code"): str}),
            description_placeholders={"auth_url": request.url, "error": str(err)},
            errors={"base": "exchange_failed"},
        )

    return self.async_create_entry(
        title="Anthropic (API key from Console OAuth)",
        data={
            "provider": "anthropic",
            "api_key": api_key,
        },
    )
```

Then update the existing entry point that lands on `async_step_anthropic_oauth`. Find the place where the user's choice flows into Anthropic OAuth and route it through `async_step_anthropic_method` instead. (Existing code likely has `if provider == "anthropic_oauth": return await self.async_step_anthropic_oauth()` — change `anthropic_oauth` step call to `anthropic_method`.)

Add `import aiohttp` at top of config_flow.py if not already present.

- [ ] **Step 7.5: Run tests for new steps**

Run: `pytest tests/test_config_flow_anthropic_oauth.py -v`
Expected: PASS.

- [ ] **Step 7.6: Run full config_flow tests**

Run: `pytest tests/ -k config_flow -v`
Expected: all tests PASS.

- [ ] **Step 7.7: Commit**

```bash
git add custom_components/homeclaw/config_flow.py \
        tests/test_config_flow_anthropic_oauth.py
git commit -m "add create api key flow to anthropic oauth config"
```

---

## Task 8: Frontend cost zeroing for anthropic_oauth

**Files:**
- Modify: `custom_components/homeclaw/frontend/src/lib/services/provider.service.ts`
- Possibly create/modify: `custom_components/homeclaw/frontend/src/lib/services/cost.service.ts` (depends on existing structure)

- [ ] **Step 8.1: Inspect existing provider/cost service**

Run:
```bash
cat custom_components/homeclaw/frontend/src/lib/services/provider.service.ts | head -50
grep -rn "cost\|Cost" custom_components/homeclaw/frontend/src/lib/services/ | head -20
grep -rn "input_cost\|output_cost\|model.cost" custom_components/homeclaw/frontend/src/lib/ | head -20
```

Goal: find where model costs are displayed/calculated. The exact location depends on existing structure — common patterns:
- `provider.service.ts` reads provider config (incl. cost data)
- `models_config.json` shape: `{ provider: { model: { input_cost, output_cost, ... } } }`
- Settings/Models editor renders the cost numbers

- [ ] **Step 8.2: Add helper export to provider.service.ts**

Add at end of `provider.service.ts`:
```typescript
/**
 * Provider names whose model usage is unlimited under OAuth subscription
 * (Pro/Max plan). UI should render cost as 0 for these providers.
 */
export function isOAuthZeroCostProvider(providerName: string): boolean {
  return providerName === 'anthropic_oauth';
}
```

- [ ] **Step 8.3: Find cost render site and add zeroing**

Locate the Svelte component or service that reads `model.cost` or similar. Wrap the cost lookup:

```typescript
import { isOAuthZeroCostProvider } from '$lib/services/provider.service';

function getDisplayedCost(providerName: string, modelCost: ModelCost): ModelCost {
  if (isOAuthZeroCostProvider(providerName)) {
    return { input: 0, output: 0, cache_read: 0, cache_write: 0 };
  }
  return modelCost;
}
```

The exact integration depends on existing code — search for cost-related code:
```bash
grep -rn "input_cost\|cost.input\|cost\.output" custom_components/homeclaw/frontend/src/
```

Apply the helper at the rendering layer (Svelte component prop derivation) — NOT at the storage layer. This keeps `models_config.json` as canonical source of truth for actual Anthropic pricing.

- [ ] **Step 8.4: Build frontend and run linter**

```bash
cd custom_components/homeclaw/frontend
npm run check
npm run lint
npm run build
```
Expected: green. Fix Prettier/ESLint issues.

- [ ] **Step 8.5: Commit**

```bash
cd /Users/anowak/Projects/homeAssistant/ai_agent_ha
git add custom_components/homeclaw/frontend/src/lib/services/provider.service.ts \
        custom_components/homeclaw/frontend/src/lib/  # whatever else changed
git add custom_components/homeclaw/frontend/homeclaw-panel.js \
        custom_components/homeclaw/frontend/homeclaw-panel.css \
        custom_components/homeclaw/frontend/homeclaw-panel.js.map  # built artifacts
git commit -m "zero out cost in ui for anthropic oauth provider"
```

---

## Task 9: Bump version + CHANGELOG

**Files:**
- Modify: `custom_components/homeclaw/manifest.json`
- Modify: `CHANGELOG.md`

- [ ] **Step 9.1: Bump version in manifest.json**

Open `custom_components/homeclaw/manifest.json` and change line:
```json
"version": "1.3.1"
```
to:
```json
"version": "1.4.0"
```

- [ ] **Step 9.2: Add CHANGELOG entry**

Open `CHANGELOG.md` and prepend (after the `# Changelog` line):
```markdown
## v1.4.0 — Anthropic OAuth port from opencode-anthropic-auth v1.8.0

### Breaking
- **OAuth endpoints migrated** from `console.anthropic.com` to `platform.claude.com`. Existing OAuth refresh tokens may need re-authentication. HA will prompt automatically via the standard reauth flow if old tokens are rejected.
- **OAuth scopes expanded** from 3 to 6 (added `user:sessions:claude_code`, `user:mcp_servers`, `user:file_upload`). Re-authentication required on first refresh after upgrade.

### Added
- Server-side classifier mitigations: CCH (content-consistency-hash) billing header, system prompt sanitization pipeline, identity swap to "Claude agent / Claude Agent SDK".
- "Create API Key" OAuth flow for Console plan users — exchanges OAuth access token for a permanent API key, then configures a regular Anthropic provider entry.
- `ANTHROPIC_BASE_URL` env override for proxies/dev (with `ANTHROPIC_INSECURE=1` for local TLS bypass).
- Tool name namespacing (`mcp__homeclaw__<tool>`) — bidirectional, transparent to the agent code.

### Changed
- User-Agent bumped to `claude-cli/2.1.87 (external, cli)`.
- Refresh token network errors retried with exponential backoff (2 retries, 0.5s/1s).
- Concurrent token refreshes coalesce on a single in-flight task (prevents 401 cascades).
- Refresh token re-read from storage per attempt (prevents stale-snapshot races).
- Cost UI zeroed out for `anthropic_oauth` provider (subscription is unlimited).

### Removed
- Old `oauth.py` and flat `providers/anthropic_oauth.py` files — replaced by `providers/anthropic_oauth/` subpackage.

### Provenance
Code patterns and reverse-engineered values (CCH salt, classifier-fingerprint phrases, tool prefix convention) ported from MIT-licensed opencode-anthropic-auth v1.8.0 by Ex Machina.
```

- [ ] **Step 9.3: Verify version bump**

Run: `grep -A1 -B1 '"version"' custom_components/homeclaw/manifest.json`
Expected: `"version": "1.4.0"`

- [ ] **Step 9.4: Commit**

```bash
git add custom_components/homeclaw/manifest.json CHANGELOG.md
git commit -m "bump version to 1.4.0 for anthropic oauth port"
```

---

## Self-Review Checklist (run before declaring plan complete)

- [ ] **Spec coverage:**
  - Tier 1 (a-e): URL ✓ Task 1, scopes ✓ Task 1, user-agent ✓ Task 1, CCH ✓ Task 3, sanitization ✓ Task 5b
  - Tier 2 (f-h): inflight refresh ✓ Task 4c, network retry ✓ Task 4c, tool prefix ✓ Task 5a
  - Tier 3 (i-k): cost zeroing ✓ Task 8, ANTHROPIC_BASE_URL ✓ Task 5c, Create API Key ✓ Task 7
  - Old code deletion ✓ Task 6
  - Version bump ✓ Task 9

- [ ] **Placeholder scan:** no TBD, TODO, "implement later", "similar to". All code blocks complete.

- [ ] **Type consistency:**
  - `TokenSet(access_token, refresh_token, expires_at)` used identically in auth.py and provider.py
  - `AuthorizationRequest(url, redirect_uri, state, verifier)` used identically in auth.py and config_flow.py
  - `OAuthRefreshError(message, *, is_permanent)` constructor consistent across all uses
  - `read_refresh_token: Callable[[], Awaitable[str]]` callback signature consistent in auth.py and provider.py

---

## Final Verification

After all tasks complete:

- [ ] **Run full test suite:** `pytest tests/ -v --cov=custom_components/homeclaw --cov-report=term`
  - Expected: 70%+ coverage maintained, all new modules at 90%+
- [ ] **Run lints:** `black --check custom_components/`, `isort --check custom_components/`, `flake8 custom_components/`
- [ ] **Frontend build:** `cd custom_components/homeclaw/frontend && npm run build`
- [ ] **Show commit summary:** `git log --oneline -10`
- [ ] **Ask user about squash:** present commit list, ask if they want all 9 squashed into 1

---

## Notes for the Engineer

1. **TDD discipline** — write the test, run it, verify it fails for the right reason (import error or assertion failure), then implement minimum to pass. Don't write multiple functions before testing.

2. **Mocking aiohttp is fiddly** — the pattern `session.post = MagicMock(return_value=ctx)` where `ctx = AsyncMock(); ctx.__aenter__.return_value.status = 200` works for `async with session.post(...) as resp: ...` flows. Use `side_effect=[ctx1, ctx2, ...]` for multiple calls.

3. **Existing test patterns** — see `tests/test_providers/test_anthropic.py` for the existing fixture style; tests are async without `@pytest.mark.asyncio` thanks to `asyncio_mode=auto` in pytest.ini.

4. **HomeAssistant ConfigEntry mutation** — `mock_config_entry.data` is a regular dict; assigning to it just replaces the dict in tests, but in production HA mutates via `async_update_entry(entry, data=new_dict)`. Tests assert against `mock_hass.config_entries.async_update_entry.call_args.kwargs["data"]`.

5. **Don't break the worktree** — Task 6 is the only task that deletes files. Make sure all tests pass before AND after Task 6 commits.

6. **License attribution** — every new module's docstring must include `Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).` Don't omit this.
