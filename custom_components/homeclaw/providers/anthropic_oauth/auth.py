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


_NETWORK_ERRORS = (
    aiohttp.ClientConnectionError,
    aiohttp.ServerDisconnectedError,
    aiohttp.ClientPayloadError,
    asyncio.TimeoutError,
)


async def _do_refresh(session: aiohttp.ClientSession, refresh_token_value: str) -> TokenSet:
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
                self._task = asyncio.create_task(refresh_with_retry(session, read_refresh_token))
        try:
            return await self._task
        finally:
            async with self._lock:
                if self._task is not None and self._task.done():
                    self._task = None


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
