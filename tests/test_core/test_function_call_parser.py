"""Tests for FunctionCallParser.

Tests the provider-specific strategy pattern for parsing function calls
from raw AI response text.
"""

import json

import pytest

from custom_components.homeclaw.core.function_call_parser import FunctionCallParser
from custom_components.homeclaw.core.response_parser import ResponseParser


@pytest.fixture
def parser():
    """Create a FunctionCallParser with a real ResponseParser."""
    return FunctionCallParser(ResponseParser())


class TestOpenAIFormat:
    """Tests for OpenAI tool_calls format detection."""

    def test_openai_single_tool_call(self, parser):
        """Test single OpenAI tool call detection."""
        response = json.dumps(
            {
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": json.dumps({"city": "NYC"}),
                        },
                    }
                ]
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "get_weather"
        assert result[0].arguments == {"city": "NYC"}

    def test_openai_multiple_tool_calls(self, parser):
        """Test multiple parallel OpenAI tool calls."""
        response = json.dumps(
            {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": json.dumps({"city": "NYC"}),
                        },
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "get_time",
                            "arguments": json.dumps({"timezone": "EST"}),
                        },
                    },
                ]
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 2
        assert result[0].name == "get_weather"
        assert result[1].name == "get_time"


class TestGeminiFormat:
    """Tests for Gemini functionCall format detection."""

    def test_gemini_function_call(self, parser):
        """Test Gemini-style function call."""
        response = json.dumps(
            {"functionCall": {"name": "get_weather", "args": {"location": "NYC"}}}
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "get_weather"
        assert result[0].arguments == {"location": "NYC"}
        assert result[0].id == "gemini_get_weather"

    def test_gemini_function_call_empty_args(self, parser):
        """Test Gemini function call with no arguments."""
        response = json.dumps({"functionCall": {"name": "list_entities"}})

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "list_entities"
        assert result[0].arguments == {}


class TestAnthropicFormat:
    """Tests for Anthropic tool_use format detection."""

    def test_anthropic_tool_use(self, parser):
        """Test Anthropic-style tool_use."""
        response = json.dumps(
            {
                "tool_use": {
                    "id": "tool_123",
                    "name": "search",
                    "input": {"query": "weather"},
                }
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "search"
        assert result[0].id == "tool_123"
        assert result[0].arguments == {"query": "weather"}

    def test_anthropic_with_additional_tool_calls(self, parser):
        """Test Anthropic parallel tool use with additional_tool_calls."""
        response = json.dumps(
            {
                "tool_use": {
                    "id": "tool_1",
                    "name": "get_state",
                    "input": {"entity_id": "light.bedroom"},
                },
                "additional_tool_calls": [
                    {
                        "id": "tool_2",
                        "name": "get_state",
                        "input": {"entity_id": "light.kitchen"},
                    }
                ],
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 2
        assert result[0].name == "get_state"
        assert result[0].arguments == {"entity_id": "light.bedroom"}
        assert result[1].name == "get_state"
        assert result[1].arguments == {"entity_id": "light.kitchen"}


class TestSimpleFormat:
    """Tests for simple/custom function call formats."""

    def test_function_parameters_format(self, parser):
        """Test {"function": ..., "parameters": ...} format."""
        response = json.dumps(
            {
                "function": "get_entities",
                "parameters": {"domain": "light"},
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "get_entities"
        assert result[0].arguments == {"domain": "light"}

    def test_name_arguments_format(self, parser):
        """Test {"name": ..., "arguments": ...} format."""
        response = json.dumps(
            {
                "name": "turn_on",
                "arguments": {"entity_id": "light.bedroom"},
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "turn_on"

    def test_tool_args_format(self, parser):
        """Test {"tool": ..., "args": ...} format."""
        response = json.dumps(
            {
                "tool": "call_service",
                "args": {"domain": "light", "service": "turn_on"},
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert result[0].name == "call_service"


class TestNonFunctionCallResponses:
    """Tests for responses that should NOT be detected as function calls."""

    def test_plain_text(self, parser):
        """Test plain text response."""
        result = parser.detect("Hello, how can I help you?")
        assert result is None

    def test_regular_json(self, parser):
        """Test regular JSON without function markers."""
        response = json.dumps({"temperature": 72, "humidity": 45})
        result = parser.detect(response)
        assert result is None

    def test_empty_string(self, parser):
        """Test empty string."""
        result = parser.detect("")
        assert result is None

    def test_json_with_unrelated_keys(self, parser):
        """Test JSON that has no function call markers."""
        response = json.dumps(
            {
                "status": "ok",
                "data": {"entities": ["light.test"]},
            }
        )
        result = parser.detect(response)
        assert result is None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_json_in_markdown_code_block(self, parser):
        """Test function call embedded in markdown code block."""
        response = '```json\n{"functionCall": {"name": "test", "args": {}}}\n```'

        result = parser.detect(response)

        assert result is not None
        assert result[0].name == "test"

    def test_priority_openai_over_simple(self, parser):
        """Test that OpenAI format takes priority over simple format."""
        response = json.dumps(
            {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "correct_tool",
                            "arguments": json.dumps({}),
                        },
                    }
                ],
                "name": "wrong_tool",
                "arguments": {},
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert result[0].name == "correct_tool"

    def test_priority_gemini_over_anthropic(self, parser):
        """Test that Gemini format takes priority over Anthropic."""
        response = json.dumps(
            {
                "functionCall": {"name": "gemini_tool", "args": {}},
                "tool_use": {"id": "t1", "name": "anthropic_tool", "input": {}},
            }
        )

        result = parser.detect(response)

        assert result is not None
        assert result[0].name == "gemini_tool"
