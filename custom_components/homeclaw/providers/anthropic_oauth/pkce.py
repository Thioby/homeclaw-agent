"""PKCE (RFC 7636) helpers for OAuth 2.0 authorization code flow.

Ported from opencode-anthropic-auth v1.8.0 src/pkce.ts (MIT, © Ex Machina).
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
