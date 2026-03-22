"""Anthropic OAuth helpers for Claude Pro/Max subscription."""

import asyncio
import base64
import hashlib
import json as _json
import logging
import re as _re
import secrets
import time
from urllib.parse import urlencode

import aiohttp

_LOGGER = logging.getLogger(__name__)


class OAuthRefreshError(Exception):
    """Raised when OAuth token refresh fails.

    Attributes:
        is_permanent: True when the error cannot be fixed by retrying
            (e.g. ``invalid_grant`` — the refresh token is revoked).
    """

    def __init__(self, message: str, *, is_permanent: bool = False) -> None:
        super().__init__(message)
        self.is_permanent = is_permanent


# Anthropic OAuth — public desktop client ID (from Claude Code / opencode).
CLIENT_ID = "9d1c250a-e61b-44d9" + "-88ed-5944d1962f5e"
TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
SCOPES = "org:create_api_key user:profile user:inference"
_USER_AGENT = "claude-cli/2.1.2 (external, cli)"
_MAX_RETRY_DELAY = 15


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256).

    Returns:
        tuple: (code_verifier, code_challenge)
    """
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    return code_verifier, code_challenge


def build_auth_url(challenge: str, verifier: str, mode: str = "max") -> str:
    """Build OAuth authorization URL.

    Args:
        challenge: PKCE code_challenge
        verifier: PKCE code_verifier (used as state parameter)
        mode: "max" for claude.ai, "console" for console.anthropic.com

    Returns:
        Authorization URL string
    """
    base = "https://claude.ai" if mode == "max" else "https://console.anthropic.com"
    params = {
        "code": "true",
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": verifier,
    }
    return f"{base}/oauth/authorize?{urlencode(params)}"


async def exchange_code(
    session: aiohttp.ClientSession, code: str, verifier: str
) -> dict:
    """Exchange authorization code for tokens.

    Args:
        session: aiohttp ClientSession
        code: Authorization code (may include ``#state`` suffix or be a
            full callback URL with ``?code=…`` query param).
        verifier: PKCE code_verifier

    Returns:
        dict with keys: access_token, refresh_token, expires_at
        or dict with key: error
    """
    clean_code = code.strip()

    # Strip #state suffix if present
    if "#" in clean_code:
        clean_code = clean_code.split("#")[0]

    # Handle full callback URL (e.g. …?code=XYZ&…)
    if "?" in clean_code:
        match = _re.search(r"[?&]code=([^&#]+)", clean_code)
        if match:
            clean_code = match.group(1)

    clean_code = clean_code.strip()

    _LOGGER.debug("Exchanging authorization code (length=%d)", len(clean_code))

    for attempt in range(3):
        async with session.post(
            TOKEN_URL,
            json={
                "code": clean_code,
                "state": verifier,
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            headers={
                "Content-Type": "application/json",
                "user-agent": _USER_AGENT,
            },
        ) as resp:
            if resp.status == 429 and attempt < 2:
                try:
                    retry_after = int(resp.headers.get("retry-after", "0"))
                except (ValueError, TypeError):
                    retry_after = 0
                delay = min(retry_after or (2 ** attempt + 1), _MAX_RETRY_DELAY)
                _LOGGER.warning(
                    "Token exchange rate-limited (429), retrying in %ds", delay
                )
                await asyncio.sleep(delay)
                continue

            if resp.status != 200:
                error_text = await resp.text()
                _LOGGER.error("Token exchange failed: %s", error_text)
                return {"error": f"Token exchange failed: {resp.status}"}

            data = await resp.json()

            if "access_token" not in data:
                _LOGGER.error("Token response missing access_token: %s", data)
                return {"error": "Invalid token response: missing access_token"}

            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "expires_at": time.time() + data.get("expires_in", 28800),
            }

    return {"error": "Token exchange failed after retries"}


async def refresh_token(session: aiohttp.ClientSession, refresh: str) -> dict:
    """Refresh access token.

    Args:
        session: aiohttp ClientSession
        refresh: Refresh token

    Returns:
        dict with keys: access_token, refresh_token, expires_at

    Raises:
        OAuthRefreshError: If refresh fails
    """
    for attempt in range(3):
        async with session.post(
            TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_id": CLIENT_ID,
            },
            headers={
                "Content-Type": "application/json",
                "user-agent": _USER_AGENT,
            },
        ) as resp:
            if resp.status == 429 and attempt < 2:
                try:
                    retry_after = int(resp.headers.get("retry-after", "0"))
                except (ValueError, TypeError):
                    retry_after = 0
                delay = min(retry_after or (2 ** attempt + 1), _MAX_RETRY_DELAY)
                _LOGGER.warning(
                    "Token refresh rate-limited (429), retrying in %ds", delay
                )
                await asyncio.sleep(delay)
                continue

            if resp.status != 200:
                error_text = await resp.text()
                _LOGGER.error("Token refresh failed: %s", error_text)

                # Detect permanent failures (revoked / expired refresh token).
                is_permanent = False
                try:
                    err_data = _json.loads(error_text)
                    is_permanent = err_data.get("error") == "invalid_grant"
                except (ValueError, TypeError):
                    pass

                if is_permanent:
                    _LOGGER.error(
                        "Anthropic refresh token is permanently invalid — "
                        "re-authentication required"
                    )

                raise OAuthRefreshError(
                    f"Token refresh failed: {resp.status}",
                    is_permanent=is_permanent,
                )

            data = await resp.json()

            if "access_token" not in data:
                _LOGGER.error("Refresh response missing access_token: %s", data)
                raise OAuthRefreshError("Invalid refresh response: missing access_token")

            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", refresh),
                "expires_at": time.time() + data.get("expires_in", 28800),
            }

    raise OAuthRefreshError("Token refresh failed after retries")
