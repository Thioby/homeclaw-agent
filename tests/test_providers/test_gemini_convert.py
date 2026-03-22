"""Tests for Gemini message/tool format converters — thought_signature fixes."""

from __future__ import annotations

import json

from custom_components.homeclaw.providers._gemini_convert import (
    SYNTHETIC_THOUGHT_SIGNATURE,
    convert_messages,
    ensure_thought_signatures,
    process_gemini_chunk,
)


# --- Fix 1: process_gemini_chunk extracts thoughtSignature from part level ---


def test_process_gemini_chunk_preserves_thought_signature() -> None:
    """thoughtSignature should be extracted from the part level, not from inside functionCall."""
    chunk = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "call_service",
                                "args": {"entity_id": "light.bedroom"},
                            },
                            "thoughtSignature": "base64sig==",
                        }
                    ]
                }
            }
        ]
    }

    results = process_gemini_chunk(chunk)

    assert len(results) == 1
    assert results[0]["type"] == "tool_call"
    assert results[0]["name"] == "call_service"
    assert results[0]["thought_signature"] == "base64sig=="


def test_process_gemini_chunk_thought_signature_none_when_absent() -> None:
    """thought_signature should be None when no thoughtSignature on the part."""
    chunk = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "get_entity_state",
                                "args": {"entity_id": "sensor.temp"},
                            },
                        }
                    ]
                }
            }
        ]
    }

    results = process_gemini_chunk(chunk)

    assert len(results) == 1
    assert results[0]["thought_signature"] is None


# --- Fix 3: convert_messages places thoughtSignature at part level ---


def test_convert_messages_thought_signature_placement() -> None:
    """thoughtSignature should be a sibling of functionCall, not nested inside it."""
    tool_call_content = json.dumps(
        {
            "functionCall": {
                "name": "call_service",
                "args": {"entity_id": "light.bedroom"},
            },
            "thoughtSignature": "base64sig==",
        }
    )
    messages = [
        {"role": "user", "content": "Turn off the light"},
        {"role": "assistant", "content": tool_call_content},
    ]

    contents, _ = convert_messages(messages)

    # Find the model turn with the functionCall
    model_turn = next(c for c in contents if c["role"] == "model")
    fc_part = next(p for p in model_turn["parts"] if "functionCall" in p)

    # thoughtSignature should be at the part level
    assert "thoughtSignature" in fc_part
    assert fc_part["thoughtSignature"] == "base64sig=="
    # NOT inside functionCall
    assert "thoughtSignature" not in fc_part["functionCall"]


def test_convert_messages_no_thought_signature_when_absent() -> None:
    """Part should not have thoughtSignature key when it was not in the source."""
    tool_call_content = json.dumps(
        {
            "functionCall": {
                "name": "call_service",
                "args": {"entity_id": "light.bedroom"},
            },
        }
    )
    messages = [
        {"role": "user", "content": "Turn off the light"},
        {"role": "assistant", "content": tool_call_content},
    ]

    contents, _ = convert_messages(messages)

    model_turn = next(c for c in contents if c["role"] == "model")
    fc_part = next(p for p in model_turn["parts"] if "functionCall" in p)

    # When no thought_signature, ensure_thought_signatures will inject synthetic one
    # but the original placement logic should not add it
    assert "thoughtSignature" not in fc_part["functionCall"]


# --- Fix 4: ensure_thought_signatures ---


def test_ensure_thought_signatures_injects_synthetic() -> None:
    """Missing thoughtSignature in active loop should get synthetic fallback."""
    contents = [
        {"role": "user", "parts": [{"text": "Turn off the light"}]},
        {
            "role": "model",
            "parts": [
                {
                    "functionCall": {
                        "name": "call_service",
                        "args": {"entity_id": "light.bedroom"},
                    },
                }
            ],
        },
    ]

    result = ensure_thought_signatures(contents)

    model_turn = result[1]
    fc_part = model_turn["parts"][0]
    assert fc_part["thoughtSignature"] == SYNTHETIC_THOUGHT_SIGNATURE


def test_ensure_thought_signatures_preserves_existing() -> None:
    """Existing thoughtSignature should not be overwritten."""
    contents = [
        {"role": "user", "parts": [{"text": "Turn off the light"}]},
        {
            "role": "model",
            "parts": [
                {
                    "functionCall": {
                        "name": "call_service",
                        "args": {"entity_id": "light.bedroom"},
                    },
                    "thoughtSignature": "real_signature_abc",
                }
            ],
        },
    ]

    result = ensure_thought_signatures(contents)

    model_turn = result[1]
    fc_part = model_turn["parts"][0]
    assert fc_part["thoughtSignature"] == "real_signature_abc"


def test_ensure_thought_signatures_only_active_loop() -> None:
    """Model turns before the last user text turn should not be modified."""
    contents = [
        {"role": "user", "parts": [{"text": "First question"}]},
        {
            "role": "model",
            "parts": [
                {
                    "functionCall": {"name": "old_tool", "args": {}},
                    # No thoughtSignature — but this is before the active loop
                }
            ],
        },
        {
            "role": "user",
            "parts": [
                {"functionResponse": {"name": "old_tool", "response": {"ok": True}}}
            ],
        },
        {"role": "user", "parts": [{"text": "Second question"}]},
        {
            "role": "model",
            "parts": [
                {
                    "functionCall": {"name": "new_tool", "args": {}},
                }
            ],
        },
    ]

    result = ensure_thought_signatures(contents)

    # Old model turn (index 1) — before active loop, should NOT be modified
    old_fc = result[1]["parts"][0]
    assert "thoughtSignature" not in old_fc

    # New model turn (index 4) — in active loop, SHOULD get synthetic
    new_fc = result[4]["parts"][0]
    assert new_fc["thoughtSignature"] == SYNTHETIC_THOUGHT_SIGNATURE


def test_ensure_thought_signatures_no_user_text_returns_unchanged() -> None:
    """If there are no user turns with text, contents should be returned unchanged."""
    contents = [
        {
            "role": "user",
            "parts": [{"functionResponse": {"name": "tool", "response": {"ok": True}}}],
        },
        {
            "role": "model",
            "parts": [{"functionCall": {"name": "tool", "args": {}}}],
        },
    ]

    result = ensure_thought_signatures(contents)

    assert result == contents


def test_ensure_thought_signatures_only_first_function_call_per_turn() -> None:
    """Only the first functionCall in a model turn should get synthetic signature."""
    contents = [
        {"role": "user", "parts": [{"text": "Do two things"}]},
        {
            "role": "model",
            "parts": [
                {"functionCall": {"name": "tool_a", "args": {}}},
                {"functionCall": {"name": "tool_b", "args": {}}},
            ],
        },
    ]

    result = ensure_thought_signatures(contents)

    model_parts = result[1]["parts"]
    assert model_parts[0]["thoughtSignature"] == SYNTHETIC_THOUGHT_SIGNATURE
    assert "thoughtSignature" not in model_parts[1]


# --- Fix 5: process_gemini_chunk filters thought parts ---


def test_process_gemini_chunk_filters_thought_parts() -> None:
    """Parts with thought=true should be skipped, not yielded as text."""
    chunk = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Internal reasoning...", "thought": True},
                        {"text": "The light is now off."},
                    ]
                }
            }
        ]
    }

    results = process_gemini_chunk(chunk)

    assert len(results) == 1
    assert results[0]["type"] == "text"
    assert results[0]["content"] == "The light is now off."


def test_process_gemini_chunk_thought_false_not_filtered() -> None:
    """Parts with thought=false should not be filtered."""
    chunk = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Normal text", "thought": False},
                    ]
                }
            }
        ]
    }

    results = process_gemini_chunk(chunk)

    assert len(results) == 1
    assert results[0]["content"] == "Normal text"
