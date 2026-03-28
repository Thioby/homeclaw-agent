"""Tests for canonical tool-call codec helpers."""

from __future__ import annotations

import json

from custom_components.homeclaw.core.tool_call_codec import (
    build_assistant_tool_message,
    extract_tool_calls_from_assistant_content,
)


def test_build_assistant_tool_message_contains_only_canonical_tool_calls() -> None:
    """Canonical payload should only contain the tool_calls list."""
    content = build_assistant_tool_message(
        [
            {
                "id": "toolu_1",
                "name": "get_entity_state",
                "args": {"entity_id": "light.kitchen"},
            },
            {
                "id": "toolu_2",
                "name": "get_entity_state",
                "args": {"entity_id": "switch.kettle"},
            },
        ]
    )
    parsed = json.loads(content)

    assert len(parsed["tool_calls"]) == 2
    assert parsed["tool_calls"][0]["id"] == "toolu_1"
    assert parsed["tool_calls"][1]["id"] == "toolu_2"
    # Legacy keys should no longer be present in new messages
    assert "tool_use" not in parsed
    assert "additional_tool_calls" not in parsed


def test_extract_tool_calls_from_openai_style_tool_calls() -> None:
    """Extractor should parse OpenAI-style function tool_calls."""
    parsed_content = {
        "tool_calls": [
            {
                "id": "call_1",
                "function": {
                    "name": "get_entity_state",
                    "arguments": '{"entity_id":"light.kitchen"}',
                },
            }
        ]
    }

    calls = extract_tool_calls_from_assistant_content(parsed_content)
    assert calls == [
        {
            "id": "call_1",
            "name": "get_entity_state",
            "args": {"entity_id": "light.kitchen"},
        }
    ]


def test_extract_tool_calls_gemini_thought_signature() -> None:
    """Gemini thoughtSignature should be extracted from parsed_content (part level), not from functionCall."""
    # This is a Gemini part-level structure: thoughtSignature is sibling of functionCall
    parsed_content = {
        "functionCall": {
            "name": "call_service",
            "args": {"entity_id": "light.bedroom"},
        },
        "thoughtSignature": "base64sig==",
    }

    calls = extract_tool_calls_from_assistant_content(parsed_content)

    assert len(calls) == 1
    assert calls[0]["name"] == "call_service"
    assert calls[0]["thought_signature"] == "base64sig=="


def test_extract_tool_calls_gemini_no_thought_signature() -> None:
    """Without thoughtSignature, the key should not appear in the result."""
    parsed_content = {
        "functionCall": {
            "name": "call_service",
            "args": {"entity_id": "light.bedroom"},
        },
    }

    calls = extract_tool_calls_from_assistant_content(parsed_content)

    assert len(calls) == 1
    assert calls[0]["name"] == "call_service"
    assert "thought_signature" not in calls[0]
