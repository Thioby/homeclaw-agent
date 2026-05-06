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
