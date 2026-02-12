"""Tests for canonical tool-call codec helpers."""

from __future__ import annotations

import json

from custom_components.homeclaw.core.tool_call_codec import (
    build_assistant_tool_message,
    extract_tool_calls_from_assistant_content,
)


def test_build_assistant_tool_message_contains_canonical_and_anthropic_shapes() -> None:
    """Canonical payload should keep both generic and Anthropic-friendly keys."""
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
    assert parsed["tool_use"]["id"] == "toolu_1"
    assert parsed["additional_tool_calls"][0]["id"] == "toolu_2"


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
