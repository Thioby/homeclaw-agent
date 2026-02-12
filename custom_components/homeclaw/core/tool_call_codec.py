"""Canonical tool-call encoding and decoding helpers.

This module provides provider-agnostic helpers for representing tool calls
inside assistant messages and extracting them back across provider-specific
formats.
"""

from __future__ import annotations

import json
from typing import Any


def normalize_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize tool-call dictionaries to a canonical shape.

    Canonical shape:
        {"id": str, "name": str, "args": dict}
    """
    normalized: list[dict[str, Any]] = []
    for tc in tool_calls:
        name = tc.get("name")
        if not isinstance(name, str) or not name:
            continue

        raw_args = tc.get("args", {})
        args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}

        normalized.append(
            {
                "id": str(tc.get("id", "") or name),
                "name": name,
                "args": args,
            }
        )

    return normalized


def build_assistant_tool_message(tool_calls: list[dict[str, Any]]) -> str:
    """Build a canonical JSON assistant content for tool calls.

    Stores:
    - `tool_calls` for provider-agnostic parsing
    - `tool_use` + `additional_tool_calls` for Anthropic compatibility
    """
    normalized = normalize_tool_calls(tool_calls)
    if not normalized:
        return json.dumps({"tool_calls": []})

    payload: dict[str, Any] = {
        "tool_calls": normalized,
    }

    first = normalized[0]
    payload["tool_use"] = {
        "id": first["id"],
        "name": first["name"],
        "input": first["args"],
    }
    if len(normalized) > 1:
        payload["additional_tool_calls"] = [
            {
                "id": tc["id"],
                "name": tc["name"],
                "input": tc["args"],
            }
            for tc in normalized[1:]
        ]

    return json.dumps(payload)


def extract_tool_calls_from_assistant_content(
    parsed_content: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract canonical tool calls from known assistant payload formats."""
    calls: list[dict[str, Any]] = []

    # Canonical format used by our runtime.
    tool_calls = parsed_content.get("tool_calls", [])
    if isinstance(tool_calls, list):
        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            name = tc.get("name")
            args = tc.get("args", {})
            if not isinstance(name, str) or not name:
                function = tc.get("function", {})
                if isinstance(function, dict):
                    name = function.get("name")
                    raw_args = function.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            args = {}
                    elif isinstance(raw_args, dict):
                        args = raw_args
            if not isinstance(name, str) or not name:
                continue
            calls.append(
                {
                    "id": str(tc.get("id", "") or name),
                    "name": name,
                    "args": args if isinstance(args, dict) else {},
                }
            )

    # Anthropic shape.
    primary = parsed_content.get("tool_use")
    if isinstance(primary, dict):
        name = primary.get("name", "")
        if isinstance(name, str) and name:
            calls.append(
                {
                    "id": str(primary.get("id", "") or name),
                    "name": name,
                    "args": (
                        primary.get("input", {})
                        if isinstance(primary.get("input", {}), dict)
                        else {}
                    ),
                }
            )
    additional = parsed_content.get("additional_tool_calls", [])
    if isinstance(additional, list):
        for extra in additional:
            if not isinstance(extra, dict):
                continue
            name = extra.get("name", "")
            if isinstance(name, str) and name:
                calls.append(
                    {
                        "id": str(extra.get("id", "") or name),
                        "name": name,
                        "args": (
                            extra.get("input", {})
                            if isinstance(extra.get("input", {}), dict)
                            else {}
                        ),
                    }
                )

    # Gemini fallback shape.
    fc = parsed_content.get("functionCall")
    if isinstance(fc, dict):
        name = fc.get("name", "")
        if isinstance(name, str) and name:
            calls.append(
                {
                    "id": str(parsed_content.get("id", "") or name),
                    "name": name,
                    "args": (
                        fc.get("args", {})
                        if isinstance(fc.get("args", {}), dict)
                        else {}
                    ),
                }
            )

    # Deduplicate while preserving order.
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for tc in calls:
        key = (tc["id"], tc["name"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(tc)

    return deduped
