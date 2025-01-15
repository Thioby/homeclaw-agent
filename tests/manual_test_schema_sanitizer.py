"""Manual tests for Gemini schema sanitizer - no pytest needed."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.homeclaw.providers.gemini_schema_sanitizer import (
    clean_schema_for_gemini,
    clean_tools_for_gemini,
)


def test_realistic_tool():
    """Test with realistic tool that was causing 400 errors."""
    print("\n=== Test: Realistic Tool Schema ===")

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

    print("BEFORE:")
    print(tool["function"]["parameters"])

    cleaned = clean_tools_for_gemini([tool])
    params = cleaned[0]["function"]["parameters"]

    print("\nAFTER:")
    print(params)

    # Assertions
    assert "minLength" not in str(params), "minLength should be removed"
    assert "pattern" not in str(params), "pattern should be removed"
    assert "additionalProperties" not in params, (
        "additionalProperties should be removed"
    )
    assert params["type"] == "object"
    assert params["required"] == ["device_class"]

    print("✅ PASSED")


def test_anyof_flattening():
    """Test anyOf flattening."""
    print("\n=== Test: anyOf Flattening ===")

    schema = {
        "type": "object",
        "properties": {
            "units": {"anyOf": [{"const": "celsius"}, {"const": "fahrenheit"}]}
        },
    }

    print("BEFORE:")
    print(schema)

    cleaned = clean_schema_for_gemini(schema)

    print("\nAFTER:")
    print(cleaned)

    # Assertions
    assert "anyOf" not in str(cleaned), "anyOf should be flattened"
    assert cleaned["properties"]["units"]["type"] == "string"
    assert set(cleaned["properties"]["units"]["enum"]) == {"celsius", "fahrenheit"}

    print("✅ PASSED")


def test_all_unsupported_keywords():
    """Test that all unsupported keywords are removed."""
    print("\n=== Test: All Unsupported Keywords ===")

    schema = {
        "type": "object",
        "properties": {
            "test": {
                "type": "string",
                # All the unsupported keywords:
                "minLength": 1,
                "maxLength": 100,
                "pattern": ".*",
                "format": "email",
            }
        },
        "minProperties": 1,
        "maxProperties": 10,
        "additionalProperties": False,
        "$schema": "http://json-schema.org/draft-07/schema#",
    }

    print(
        "BEFORE keywords:",
        list(schema.keys()) + list(schema["properties"]["test"].keys()),
    )

    cleaned = clean_schema_for_gemini(schema)

    print(
        "AFTER keywords:",
        list(cleaned.keys()) + list(cleaned["properties"]["test"].keys()),
    )

    # Check all unsupported keywords are gone
    unsupported = [
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minProperties",
        "maxProperties",
        "additionalProperties",
        "$schema",
    ]

    for keyword in unsupported:
        assert keyword not in str(cleaned), f"{keyword} should be removed"

    # Check type is preserved
    assert cleaned["type"] == "object"
    assert cleaned["properties"]["test"]["type"] == "string"

    print("✅ PASSED")


if __name__ == "__main__":
    print("Running Gemini Schema Sanitizer Tests")
    print("=" * 50)

    try:
        test_realistic_tool()
        test_anyof_flattening()
        test_all_unsupported_keywords()

        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
