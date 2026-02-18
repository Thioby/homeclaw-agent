"""Google Gemini OAuth helpers for Gemini CLI authentication.

This module implements OAuth 2.0 PKCE flow for Google Gemini API,
similar to how gemini-cli authenticates users.
"""

from __future__ import annotations

import base64
import hashlib
import json as _json
import logging
import os
import secrets
import time
from urllib.parse import urlencode

import aiohttp

_LOGGER = logging.getLogger(__name__)


class GeminiOAuthRefreshError(Exception):
    """Raised when Gemini OAuth token refresh fails.

    Attributes:
        is_permanent: True when the error cannot be fixed by retrying
            (e.g. revoked refresh token).  Defaults to False.
    """

    def __init__(self, message: str, *, is_permanent: bool = False) -> None:
        super().__init__(message)
        self.is_permanent = is_permanent


# OAuth Constants — these are the PUBLIC client credentials from Gemini CLI
# (open source, not secret). See: github.com/google-gemini/gemini-cli
# They are embedded here because this is a desktop/CLI-style OAuth flow,
# not a web app flow. Google publishes these for public clients.
CLIENT_ID = os.environ.get(
    "GEMINI_OAUTH_CLIENT_ID",
    "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com",
)
CLIENT_SECRET = os.environ.get(
    "GEMINI_OAUTH_CLIENT_SECRET",
    "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",
)

# Google OAuth endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Scopes required for Gemini API access (space-separated string for OAuth)
SCOPES = "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"

# Redirect URI for manual code entry flow
# Using OOB (out-of-band) style redirect for Home Assistant integration
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

# Alternative: Use the same redirect as Gemini CLI for web flow
REDIRECT_URI_WEB = "http://localhost:8085/oauth2callback"


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256).

    Returns:
        tuple: (code_verifier, code_challenge)
    """
    # Generate a random code verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(64)

    # Create code challenge using S256 method
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    return code_verifier, code_challenge


def build_auth_url(challenge: str, state: str) -> str:
    """Build Google OAuth authorization URL.

    Args:
        challenge: PKCE code_challenge
        state: State parameter for CSRF protection (use code_verifier)

    Returns:
        Authorization URL string
    """
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI_WEB,
        "response_type": "code",
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",  # Required to get refresh_token
        "prompt": "consent",  # Force consent to always get refresh_token
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    session: aiohttp.ClientSession, code: str, verifier: str
) -> dict:
    """Exchange authorization code for tokens.

    Args:
        session: aiohttp ClientSession
        code: Authorization code from Google
        verifier: PKCE code_verifier

    Returns:
        dict with keys: access_token, refresh_token, expires_at
        or dict with key: error
    """
    async with session.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI_WEB,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ) as resp:
        if resp.status != 200:
            error_text = await resp.text()
            _LOGGER.error("Gemini token exchange failed: %s", error_text)
            return {"error": f"Token exchange failed: {resp.status} - {error_text}"}

        data = await resp.json()

        if "access_token" not in data:
            _LOGGER.error("Gemini token response missing access_token: %s", data)
            return {"error": "Invalid token response: missing access_token"}

        if "refresh_token" not in data:
            _LOGGER.warning(
                "Gemini token response missing refresh_token. "
                "Token refresh will not be possible."
            )

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": time.time() + data.get("expires_in", 3600),
            "token_type": data.get("token_type", "Bearer"),
        }


async def refresh_token(session: aiohttp.ClientSession, refresh: str) -> dict:
    """Refresh access token using refresh token.

    Args:
        session: aiohttp ClientSession
        refresh: Refresh token

    Returns:
        dict with keys: access_token, refresh_token, expires_at

    Raises:
        GeminiOAuthRefreshError: If refresh fails
    """
    async with session.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ) as resp:
        if resp.status != 200:
            error_text = await resp.text()
            _LOGGER.error("Gemini token refresh failed: %s", error_text)

            # Detect permanent failures (revoked / expired refresh token).
            is_permanent = False
            try:
                err_data = _json.loads(error_text)
                is_permanent = err_data.get("error") == "invalid_grant"
            except (ValueError, TypeError):
                pass

            if is_permanent:
                _LOGGER.error(
                    "Gemini refresh token is permanently invalid — "
                    "re-authentication required"
                )

            raise GeminiOAuthRefreshError(
                f"Token refresh failed: {resp.status}",
                is_permanent=is_permanent,
            )

        data = await resp.json()

        if "access_token" not in data:
            _LOGGER.error("Gemini refresh response missing access_token: %s", data)
            raise GeminiOAuthRefreshError(
                "Invalid refresh response: missing access_token"
            )

        return {
            "access_token": data["access_token"],
            # Google doesn't always return a new refresh_token, keep the old one
            "refresh_token": data.get("refresh_token", refresh),
            "expires_at": time.time() + data.get("expires_in", 3600),
            "token_type": data.get("token_type", "Bearer"),
        }


async def get_user_info(session: aiohttp.ClientSession, access_token: str) -> dict:
    """Get user info from Google to verify authentication.

    Args:
        session: aiohttp ClientSession
        access_token: Valid access token

    Returns:
        dict with user info (email, name, etc.) or error
    """
    async with session.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    ) as resp:
        if resp.status != 200:
            error_text = await resp.text()
            _LOGGER.error("Failed to get Gemini user info: %s", error_text)
            return {"error": f"Failed to get user info: {resp.status}"}

        return await resp.json()
