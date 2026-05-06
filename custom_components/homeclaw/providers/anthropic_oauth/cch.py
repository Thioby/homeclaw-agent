"""Content-consistency-hash billing header for Anthropic OAuth requests.

Ported from opencode-anthropic-auth v1.8.0 src/cch.ts (MIT, © Ex Machina).
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


def compute_version_suffix(message_text: str, version: str = CLAUDE_CODE_VERSION) -> str:
    """Compute 3-char version suffix from sampled message characters.

    Uses character positions from CCH_POSITIONS — when index is out of
    range, falls back to "0" (matches TS `messageText[i] || '0'`).
    """
    chars = "".join(message_text[i] if i < len(message_text) else "0" for i in CCH_POSITIONS)
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
    return "x-anthropic-billing-header: " f"cc_version={version}.{suffix}; " f"cc_entrypoint={entrypoint}; " f"cch={cch};"
