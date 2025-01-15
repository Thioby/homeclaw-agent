"""Response parser for AI provider responses.

This module extracts JSON/text parsing logic from the agent, providing
a clean interface for parsing AI responses into structured data.
"""
from __future__ import annotations

import json
import re
from typing import Any

# Characters to remove from responses before parsing
INVISIBLE_CHARS = [
    "\ufeff",  # BOM (Byte Order Mark)
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u2060",  # Word joiner
]


class ResponseParser:
    """Parses AI provider responses, extracting JSON or text.

    Handles various response formats including:
    - Plain text responses
    - Raw JSON objects
    - JSON embedded in markdown code blocks
    - Tool call structures (tool_calls or function_call)

    Automatically cleans invisible characters (BOM, zero-width chars)
    that can interfere with JSON parsing.
    """

    # Regex patterns for JSON extraction
    JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)```")
    JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")

    def parse(self, response: str) -> dict[str, Any]:
        """Parse response, returning structured result.

        Args:
            response: Raw response string from AI provider.

        Returns:
            Dictionary with:
                - type: "text" | "json" | "tool_calls"
                - content: str | dict (the parsed content)
                - raw: str (cleaned original response)
        """
        # Clean the response
        cleaned = self._clean_response(response)

        # Store the raw (cleaned) response
        raw = cleaned

        # Try to extract JSON
        extracted = self._extract_json(cleaned)

        if extracted is not None:
            # Check if it's a tool call
            if self._is_tool_call(extracted):
                return {
                    "type": "tool_calls",
                    "content": extracted,
                    "raw": raw,
                }
            # Regular JSON
            return {
                "type": "json",
                "content": extracted,
                "raw": raw,
            }

        # Fall back to plain text
        return {
            "type": "text",
            "content": cleaned.strip(),
            "raw": raw,
        }

    def _clean_response(self, text: str) -> str:
        """Remove invisible characters from text.

        Args:
            text: Input text that may contain invisible characters.

        Returns:
            Text with BOM, zero-width chars, and other invisible characters removed.
        """
        result = text
        for char in INVISIBLE_CHARS:
            result = result.replace(char, "")
        return result

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """Try to extract JSON from text.

        Attempts extraction in the following order:
        1. JSON code block (```json ... ``` or ``` ... ```)
        2. Direct JSON parsing
        3. JSON object embedded in text (finding { and })

        Args:
            text: Text that may contain JSON.

        Returns:
            Parsed JSON dict if found and valid, None otherwise.
        """
        text = text.strip()

        # 1. Try to extract from code block first
        code_block_match = self.JSON_BLOCK_PATTERN.search(text)
        if code_block_match:
            code_content = code_block_match.group(1).strip()
            try:
                parsed = json.loads(code_content)
                # Only accept dict objects, not primitives
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass  # Fall through to other methods

        # 2. Try direct JSON parsing
        try:
            parsed = json.loads(text)
            # Only accept dict objects, not primitives
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 3. Try to find JSON object boundaries
        json_start = text.find("{")
        json_end = text.rfind("}")

        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_candidate = text[json_start : json_end + 1]
            try:
                parsed = json.loads(json_candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        return None

    def _is_tool_call(self, data: dict[str, Any]) -> bool:
        """Check if parsed JSON is a tool call.

        Detects both OpenAI-style tool_calls and legacy function_call formats.

        Args:
            data: Parsed JSON dictionary.

        Returns:
            True if the data represents a tool call, False otherwise.
        """
        return "tool_calls" in data or "function_call" in data
