"""Gemini JSON Schema sanitizer.

Gemini API rejects many standard JSON Schema keywords.
This module cleans schemas to be compatible with Gemini.

Based on OpenClaw's implementation:
https://github.com/mariozechner/openclaw
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Keywords that Gemini does NOT support
GEMINI_UNSUPPORTED_KEYWORDS = {
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


def clean_schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    """Clean a JSON schema to be compatible with Gemini API.

    Removes unsupported keywords and flattens certain structures.

    Args:
        schema: JSON Schema dict (possibly with unsupported keywords)

    Returns:
        Cleaned schema compatible with Gemini
    """
    if not isinstance(schema, dict):
        return schema

    cleaned = {}

    for key, value in schema.items():
        # Skip unsupported keywords
        if key in GEMINI_UNSUPPORTED_KEYWORDS:
            continue

        # Handle anyOf/oneOf with literal constants
        if key in ("anyOf", "oneOf") and isinstance(value, list):
            flattened = try_flatten_literal_variants(value)
            if flattened:
                # Replace anyOf/oneOf with simple enum
                cleaned.update(flattened)
                continue

        # Recursively clean nested objects
        if isinstance(value, dict):
            cleaned[key] = clean_schema_for_gemini(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_schema_for_gemini(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value

    return cleaned


def try_flatten_literal_variants(variants: list[Any]) -> dict[str, Any] | None:
    """Try to flatten anyOf/oneOf with literal constants to a simple enum.

    Converts: { "anyOf": [{"const": "a"}, {"const": "b"}] }
    To: { "type": "string", "enum": ["a", "b"] }

    Args:
        variants: List of schema variants

    Returns:
        Flattened enum schema, or None if cannot flatten
    """
    if not variants:
        return None

    # Extract all constant values
    constants = []
    for variant in variants:
        if not isinstance(variant, dict):
            return None

        if "const" in variant:
            constants.append(variant["const"])
        elif "enum" in variant and len(variant.get("enum", [])) == 1:
            constants.append(variant["enum"][0])
        else:
            # Not a simple literal variant
            return None

    if not constants:
        return None

    # Infer type from first constant
    first_type = type(constants[0]).__name__
    if first_type == "bool":
        first_type = "boolean"
    elif first_type == "int" or first_type == "float":
        first_type = "number"
    elif first_type == "str":
        first_type = "string"
    elif first_type == "NoneType":
        first_type = "null"

    # Verify all constants have same type
    for const in constants:
        const_type = type(const).__name__
        if const_type == "bool":
            const_type = "boolean"
        elif const_type == "int" or const_type == "float":
            const_type = "number"
        elif const_type == "str":
            const_type = "string"
        elif const_type == "NoneType":
            const_type = "null"

        if const_type != first_type:
            # Mixed types, cannot flatten
            return None

    return {
        "type": first_type,
        "enum": constants,
    }


def clean_tools_for_gemini(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clean a list of OpenAI-format tools for Gemini compatibility.

    Args:
        tools: List of tool definitions in OpenAI format

    Returns:
        Cleaned tools list
    """
    cleaned_tools = []

    for tool in tools:
        if tool.get("type") != "function":
            cleaned_tools.append(tool)
            continue

        function = tool.get("function", {})
        parameters = function.get("parameters", {})

        # Clean the parameters schema
        cleaned_parameters = clean_schema_for_gemini(parameters)

        cleaned_tool = {
            **tool,
            "function": {
                **function,
                "parameters": cleaned_parameters,
            },
        }

        cleaned_tools.append(cleaned_tool)

        # Log if we removed any keywords
        original_keys = set(_get_all_keys(parameters))
        cleaned_keys = set(_get_all_keys(cleaned_parameters))
        removed_keys = original_keys & GEMINI_UNSUPPORTED_KEYWORDS
        if removed_keys:
            _LOGGER.debug(
                "Removed unsupported keywords from tool %s: %s",
                function.get("name", "unknown"),
                removed_keys,
            )

    return cleaned_tools


def _get_all_keys(obj: Any, keys: set[str] | None = None) -> set[str]:
    """Recursively collect all keys from a nested dict."""
    if keys is None:
        keys = set()

    if isinstance(obj, dict):
        keys.update(obj.keys())
        for value in obj.values():
            _get_all_keys(value, keys)
    elif isinstance(obj, list):
        for item in obj:
            _get_all_keys(item, keys)

    return keys
