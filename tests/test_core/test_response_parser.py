"""Tests for ResponseParser."""
from __future__ import annotations

import pytest

from custom_components.homeclaw.core.response_parser import ResponseParser


class TestParseTextResponse:
    """Tests for parsing plain text responses."""

    def test_parse_text_response_returns_plain_text(self) -> None:
        """Test that plain text is returned as-is with type 'text'."""
        parser = ResponseParser()

        result = parser.parse("Hello, how can I help you today?")

        assert result["type"] == "text"
        assert result["content"] == "Hello, how can I help you today?"
        assert result["raw"] == "Hello, how can I help you today?"

    def test_parse_text_response_preserves_whitespace(self) -> None:
        """Test that internal whitespace in text is preserved."""
        parser = ResponseParser()

        text = "Line 1\nLine 2\n\nLine 4"
        result = parser.parse(text)

        assert result["type"] == "text"
        assert result["content"] == text

    def test_parse_text_response_strips_outer_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        parser = ResponseParser()

        result = parser.parse("  Hello World  \n")

        assert result["type"] == "text"
        assert result["content"] == "Hello World"


class TestParseJsonResponse:
    """Tests for parsing JSON responses."""

    def test_parse_json_response_extracts_json(self) -> None:
        """Test that valid JSON is extracted and parsed."""
        parser = ResponseParser()

        json_str = '{"message": "Hello", "value": 42}'
        result = parser.parse(json_str)

        assert result["type"] == "json"
        assert result["content"] == {"message": "Hello", "value": 42}
        assert result["raw"] == json_str

    def test_parse_json_response_handles_nested_objects(self) -> None:
        """Test that nested JSON objects are correctly parsed."""
        parser = ResponseParser()

        json_str = '{"outer": {"inner": {"deep": "value"}}}'
        result = parser.parse(json_str)

        assert result["type"] == "json"
        assert result["content"]["outer"]["inner"]["deep"] == "value"

    def test_parse_json_response_handles_arrays(self) -> None:
        """Test that JSON arrays are correctly parsed."""
        parser = ResponseParser()

        json_str = '{"items": [1, 2, 3], "names": ["a", "b"]}'
        result = parser.parse(json_str)

        assert result["type"] == "json"
        assert result["content"]["items"] == [1, 2, 3]
        assert result["content"]["names"] == ["a", "b"]

    def test_parse_json_response_with_surrounding_text(self) -> None:
        """Test that JSON is extracted even with surrounding text."""
        parser = ResponseParser()

        text = 'Here is the response: {"status": "ok"} That is all.'
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"status": "ok"}


class TestParseJsonWithMarkdownCodeBlock:
    """Tests for parsing JSON in markdown code blocks."""

    def test_parse_json_with_json_code_block(self) -> None:
        """Test that JSON in ```json ... ``` blocks is extracted."""
        parser = ResponseParser()

        text = '''Here is the data:
```json
{"request_type": "final_response", "message": "Done"}
```
'''
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"]["request_type"] == "final_response"
        assert result["content"]["message"] == "Done"

    def test_parse_json_with_plain_code_block(self) -> None:
        """Test that JSON in ``` ... ``` blocks (no language) is extracted."""
        parser = ResponseParser()

        text = '''```
{"key": "value"}
```'''
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"key": "value"}

    def test_parse_json_prefers_code_block_over_raw(self) -> None:
        """Test that code block JSON takes precedence over raw JSON in text."""
        parser = ResponseParser()

        text = '''{"wrong": "json"} text here
```json
{"correct": "json"}
```'''
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"correct": "json"}

    def test_parse_json_code_block_with_extra_whitespace(self) -> None:
        """Test that code blocks with extra whitespace are handled."""
        parser = ResponseParser()

        text = '''```json

    {"spaced": true}

```'''
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"spaced": True}


class TestParseToolCalls:
    """Tests for parsing tool_calls structure."""

    def test_parse_tool_calls_with_tool_calls_key(self) -> None:
        """Test that responses with tool_calls are identified."""
        parser = ResponseParser()

        json_str = '''{"tool_calls": [{"name": "get_weather", "arguments": {"city": "NYC"}}]}'''
        result = parser.parse(json_str)

        assert result["type"] == "tool_calls"
        assert "tool_calls" in result["content"]
        assert result["content"]["tool_calls"][0]["name"] == "get_weather"

    def test_parse_tool_calls_with_function_call_key(self) -> None:
        """Test that responses with function_call are identified."""
        parser = ResponseParser()

        json_str = '''{"function_call": {"name": "search", "arguments": "{\\\"query\\\": \\\"test\\\"}"}}'''
        result = parser.parse(json_str)

        assert result["type"] == "tool_calls"
        assert "function_call" in result["content"]

    def test_parse_tool_calls_multiple_tools(self) -> None:
        """Test parsing multiple tool calls."""
        parser = ResponseParser()

        json_str = '''{"tool_calls": [
            {"name": "tool1", "arguments": {}},
            {"name": "tool2", "arguments": {"x": 1}}
        ]}'''
        result = parser.parse(json_str)

        assert result["type"] == "tool_calls"
        assert len(result["content"]["tool_calls"]) == 2


class TestExtractFinalResponse:
    """Tests for extracting final_response field."""

    def test_extract_final_response_from_json(self) -> None:
        """Test that final_response field is extracted when present."""
        parser = ResponseParser()

        json_str = '{"request_type": "final_response", "final_response": "The answer is 42."}'
        result = parser.parse(json_str)

        assert result["type"] == "json"
        assert result["content"]["final_response"] == "The answer is 42."

    def test_extract_final_response_with_response_field(self) -> None:
        """Test that response field is also recognized."""
        parser = ResponseParser()

        json_str = '{"request_type": "final_response", "response": "All done!"}'
        result = parser.parse(json_str)

        assert result["type"] == "json"
        assert result["content"]["response"] == "All done!"

    def test_extract_final_response_preserves_full_structure(self) -> None:
        """Test that the full JSON structure is preserved."""
        parser = ResponseParser()

        json_str = '{"request_type": "final_response", "final_response": "Done", "metadata": {"tokens": 100}}'
        result = parser.parse(json_str)

        assert result["type"] == "json"
        assert result["content"]["final_response"] == "Done"
        assert result["content"]["metadata"]["tokens"] == 100


class TestHandleMalformedJson:
    """Tests for handling malformed JSON."""

    def test_handle_malformed_json_returns_text(self) -> None:
        """Test that malformed JSON returns original text."""
        parser = ResponseParser()

        malformed = '{"broken: json'
        result = parser.parse(malformed)

        assert result["type"] == "text"
        assert result["content"] == '{"broken: json'

    def test_handle_malformed_json_missing_closing_brace(self) -> None:
        """Test handling JSON missing closing brace."""
        parser = ResponseParser()

        malformed = '{"key": "value"'
        result = parser.parse(malformed)

        assert result["type"] == "text"
        assert result["content"] == malformed

    def test_handle_malformed_json_extra_comma(self) -> None:
        """Test handling JSON with trailing comma."""
        parser = ResponseParser()

        # Trailing comma is invalid JSON
        malformed = '{"key": "value",}'
        result = parser.parse(malformed)

        assert result["type"] == "text"

    def test_handle_malformed_json_in_code_block(self) -> None:
        """Test that malformed JSON in code block falls back to text."""
        parser = ResponseParser()

        text = '''```json
{"invalid": json}
```'''
        result = parser.parse(text)

        # Should fall back to text since JSON is invalid
        assert result["type"] == "text"

    def test_handle_single_value_not_object(self) -> None:
        """Test that non-object JSON (like strings, numbers) returns text."""
        parser = ResponseParser()

        # A plain string in quotes is valid JSON but not useful for our purposes
        result = parser.parse('"just a string"')

        # We only want to parse JSON objects, not primitives
        assert result["type"] == "text"


class TestRemoveInvisibleChars:
    """Tests for removing invisible characters."""

    def test_remove_bom_character(self) -> None:
        """Test that BOM (Byte Order Mark) is removed."""
        parser = ResponseParser()

        text_with_bom = '\ufeff{"message": "hello"}'
        result = parser.parse(text_with_bom)

        assert result["type"] == "json"
        assert result["content"] == {"message": "hello"}
        assert "\ufeff" not in result["raw"]

    def test_remove_zero_width_space(self) -> None:
        """Test that zero-width space is removed."""
        parser = ResponseParser()

        text = '{"key":\u200b"value"}'
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"key": "value"}

    def test_remove_zero_width_non_joiner(self) -> None:
        """Test that zero-width non-joiner is removed."""
        parser = ResponseParser()

        text = '{"key":\u200c"value"}'
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"key": "value"}

    def test_remove_zero_width_joiner(self) -> None:
        """Test that zero-width joiner is removed."""
        parser = ResponseParser()

        text = '{"key":\u200d"value"}'
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"key": "value"}

    def test_remove_word_joiner(self) -> None:
        """Test that word joiner character is removed."""
        parser = ResponseParser()

        text = '{"key":\u2060"value"}'
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"key": "value"}

    def test_remove_multiple_invisible_chars(self) -> None:
        """Test that multiple invisible characters are all removed."""
        parser = ResponseParser()

        # Text with BOM, zero-width space, and word joiner
        text = '\ufeff{\u200b"message"\u200c:\u200d"hello"\u2060}'
        result = parser.parse(text)

        assert result["type"] == "json"
        assert result["content"] == {"message": "hello"}

    def test_clean_response_method_directly(self) -> None:
        """Test _clean_response method directly."""
        parser = ResponseParser()

        dirty = "\ufeffHello\u200bWorld\u200c!\u200d\u2060"
        clean = parser._clean_response(dirty)

        assert clean == "HelloWorld!"
        # Verify no invisible chars remain
        invisible_chars = ["\ufeff", "\u200b", "\u200c", "\u200d", "\u2060"]
        for char in invisible_chars:
            assert char not in clean


class TestExtractJson:
    """Tests for the _extract_json method."""

    def test_extract_json_from_valid_json_string(self) -> None:
        """Test extracting JSON from a valid JSON string."""
        parser = ResponseParser()

        result = parser._extract_json('{"valid": "json"}')

        assert result == {"valid": "json"}

    def test_extract_json_returns_none_for_invalid(self) -> None:
        """Test that invalid JSON returns None."""
        parser = ResponseParser()

        result = parser._extract_json("not valid json")

        assert result is None

    def test_extract_json_from_text_with_json(self) -> None:
        """Test extracting JSON embedded in text."""
        parser = ResponseParser()

        result = parser._extract_json('Some text {"embedded": "json"} more text')

        assert result == {"embedded": "json"}

    def test_extract_json_from_code_block(self) -> None:
        """Test extracting JSON from markdown code block."""
        parser = ResponseParser()

        text = '```json\n{"from": "block"}\n```'
        result = parser._extract_json(text)

        assert result == {"from": "block"}


class TestIsToolCall:
    """Tests for the _is_tool_call method."""

    def test_is_tool_call_with_tool_calls(self) -> None:
        """Test detecting tool_calls key."""
        parser = ResponseParser()

        assert parser._is_tool_call({"tool_calls": []}) is True
        assert parser._is_tool_call({"tool_calls": [{"name": "test"}]}) is True

    def test_is_tool_call_with_function_call(self) -> None:
        """Test detecting function_call key."""
        parser = ResponseParser()

        assert parser._is_tool_call({"function_call": {}}) is True
        assert parser._is_tool_call({"function_call": {"name": "test"}}) is True

    def test_is_tool_call_returns_false_for_regular_json(self) -> None:
        """Test that regular JSON is not detected as tool call."""
        parser = ResponseParser()

        assert parser._is_tool_call({"message": "hello"}) is False
        assert parser._is_tool_call({"request_type": "final_response"}) is False
        assert parser._is_tool_call({}) is False
