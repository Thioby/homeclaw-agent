"""Tests for Gemini schema sanitizer."""

import pytest
from custom_components.homeclaw.providers.gemini_schema_sanitizer import (
    clean_schema_for_gemini,
    clean_tools_for_gemini,
    try_flatten_literal_variants,
    GEMINI_UNSUPPORTED_KEYWORDS,
)


def test_removes_unsupported_keywords():
    """Test that unsupported keywords are removed."""
    schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,  # Should be removed
                "maxLength": 100,  # Should be removed
                "pattern": "^[a-z]+$",  # Should be removed
            },
            "age": {
                "type": "number",
                "minimum": 0,  # Should be removed
                "maximum": 150,  # Should be removed
            },
        },
        "additionalProperties": False,  # Should be removed
    }

    cleaned = clean_schema_for_gemini(schema)

    assert cleaned["type"] == "object"
    assert "properties" in cleaned
    assert "name" in cleaned["properties"]
    assert "age" in cleaned["properties"]

    # Unsupported keywords should be gone
    assert "minLength" not in cleaned["properties"]["name"]
    assert "maxLength" not in cleaned["properties"]["name"]
    assert "pattern" not in cleaned["properties"]["name"]
    assert "minimum" not in cleaned["properties"]["age"]
    assert "maximum" not in cleaned["properties"]["age"]
    assert "additionalProperties" not in cleaned


def test_preserves_supported_keywords():
    """Test that supported keywords are preserved."""
    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["active", "inactive"],
                "description": "User status",
            }
        },
        "required": ["status"],
    }

    cleaned = clean_schema_for_gemini(schema)

    assert cleaned["type"] == "object"
    assert cleaned["properties"]["status"]["type"] == "string"
    assert cleaned["properties"]["status"]["enum"] == ["active", "inactive"]
    assert cleaned["properties"]["status"]["description"] == "User status"
    assert cleaned["required"] == ["status"]


def test_flatten_literal_anyof():
    """Test flattening anyOf with literal constants to enum."""
    variants = [{"const": "option_a"}, {"const": "option_b"}, {"const": "option_c"}]

    result = try_flatten_literal_variants(variants)

    assert result is not None
    assert result["type"] == "string"
    assert set(result["enum"]) == {"option_a", "option_b", "option_c"}


def test_flatten_literal_oneof_with_single_enum():
    """Test flattening oneOf with single-item enums."""
    variants = [{"enum": [1]}, {"enum": [2]}, {"enum": [3]}]

    result = try_flatten_literal_variants(variants)

    assert result is not None
    assert result["type"] == "number"
    assert set(result["enum"]) == {1, 2, 3}


def test_flatten_mixed_types_returns_none():
    """Test that mixed types cannot be flattened."""
    variants = [
        {"const": "string"},
        {"const": 123},  # Different type
    ]

    result = try_flatten_literal_variants(variants)
    assert result is None


def test_flatten_complex_schema_returns_none():
    """Test that complex schemas cannot be flattened."""
    variants = [{"type": "string", "minLength": 1}, {"type": "number"}]

    result = try_flatten_literal_variants(variants)
    assert result is None


def test_schema_with_anyof_gets_flattened():
    """Test that anyOf with literals gets flattened in schema."""
    schema = {
        "type": "object",
        "properties": {
            "status": {
                "anyOf": [
                    {"const": "active"},
                    {"const": "inactive"},
                    {"const": "pending"},
                ]
            }
        },
    }

    cleaned = clean_schema_for_gemini(schema)

    # anyOf should be replaced with type + enum
    assert "anyOf" not in cleaned["properties"]["status"]
    assert cleaned["properties"]["status"]["type"] == "string"
    assert set(cleaned["properties"]["status"]["enum"]) == {
        "active",
        "inactive",
        "pending",
    }


def test_nested_objects_are_cleaned():
    """Test that nested objects are recursively cleaned."""
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",  # Should be removed
                        "pattern": ".+@.+",  # Should be removed
                    }
                },
                "additionalProperties": True,  # Should be removed
            }
        },
    }

    cleaned = clean_schema_for_gemini(schema)

    user_schema = cleaned["properties"]["user"]
    email_schema = user_schema["properties"]["email"]

    assert email_schema["type"] == "string"
    assert "format" not in email_schema
    assert "pattern" not in email_schema
    assert "additionalProperties" not in user_schema


def test_clean_tools_for_gemini():
    """Test cleaning OpenAI format tools."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "minLength": 1,  # Should be removed
                            "pattern": "^[A-Z]",  # Should be removed
                        },
                        "units": {
                            "anyOf": [{"const": "celsius"}, {"const": "fahrenheit"}]
                        },
                    },
                    "required": ["location"],
                    "additionalProperties": False,  # Should be removed
                },
            },
        }
    ]

    cleaned = clean_tools_for_gemini(tools)

    assert len(cleaned) == 1
    params = cleaned[0]["function"]["parameters"]

    # Check unsupported keywords removed
    assert "additionalProperties" not in params
    assert "minLength" not in params["properties"]["location"]
    assert "pattern" not in params["properties"]["location"]

    # Check anyOf flattened
    assert "anyOf" not in params["properties"]["units"]
    assert params["properties"]["units"]["type"] == "string"
    assert set(params["properties"]["units"]["enum"]) == {"celsius", "fahrenheit"}

    # Check required preserved
    assert params["required"] == ["location"]


def test_empty_schema():
    """Test that empty schema doesn't crash."""
    result = clean_schema_for_gemini({})
    assert result == {}


def test_all_gemini_unsupported_keywords_defined():
    """Verify all keywords from OpenClaw are included."""
    expected = {
        "patternProperties",
        "additionalProperties",
        "$schema",
        "$id",
        "$ref",
        "$defs",
        "definitions",
        "examples",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "multipleOf",
        "pattern",
        "format",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
    }

    assert GEMINI_UNSUPPORTED_KEYWORDS == expected


def test_realistic_tool_schema():
    """Test with a realistic tool schema that caused 400 errors."""
    tool = {
        "type": "function",
        "function": {
            "name": "get_entities_by_device_class",
            "description": "Get entities by device class",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Entity domain",
                        "minLength": 1,
                        "pattern": "^[a-z_]+$",
                    },
                    "device_class": {
                        "type": "string",
                        "description": "Device class",
                        "minLength": 1,
                    },
                },
                "required": ["device_class"],
                "additionalProperties": False,
            },
        },
    }

    cleaned = clean_tools_for_gemini([tool])
    params = cleaned[0]["function"]["parameters"]

    # Verify all unsupported keywords removed
    assert "minLength" not in params["properties"]["domain"]
    assert "pattern" not in params["properties"]["domain"]
    assert "minLength" not in params["properties"]["device_class"]
    assert "additionalProperties" not in params

    # Verify supported fields preserved
    assert params["type"] == "object"
    assert params["required"] == ["device_class"]
    assert params["properties"]["domain"]["type"] == "string"
    assert params["properties"]["domain"]["description"] == "Entity domain"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
