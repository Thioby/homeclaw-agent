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

    def test_canonical_format_uses_anthropic_not_openai(self, parser):
        """Test that our canonical format (from build_assistant_tool_message)
        goes through _try_anthropic, not _try_openai.

        build_assistant_tool_message produces JSON with both "tool_calls"
        (canonical) and "tool_use" (Anthropic) keys. The "tool_calls" key
        must NOT match _try_openai because our items lack the OpenAI
        "function" wrapper — that would produce FunctionCalls with empty
        names, causing repair_tool_history to orphan tool_use blocks.
        """
        from custom_components.homeclaw.core.tool_call_codec import (
            build_assistant_tool_message,
        )

        canonical = build_assistant_tool_message(
            [
                {
                    "id": "toolu_abc123",
                    "name": "get_entities_by_domain",
                    "args": {"domain": "light"},
                }
            ]
        )

        result = parser.detect(canonical)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "get_entities_by_domain"
        assert result[0].id == "toolu_abc123"
        assert result[0].arguments == {"domain": "light"}

    def test_canonical_format_parallel_tool_calls(self, parser):
        """Test canonical format with parallel tool calls (additional_tool_calls)."""
        from custom_components.homeclaw.core.tool_call_codec import (
            build_assistant_tool_message,
        )

        canonical = build_assistant_tool_message(
            [
                {
                    "id": "toolu_1",
                    "name": "get_state",
                    "args": {"entity_id": "light.a"},
                },
                {"id": "toolu_2", "name": "call_service", "args": {"domain": "light"}},
            ]
        )

        result = parser.detect(canonical)

        assert result is not None
        assert len(result) == 2
        assert result[0].name == "get_state"
        assert result[0].id == "toolu_1"
        assert result[1].name == "call_service"
        assert result[1].id == "toolu_2"

    def test_openai_format_still_works_with_function_wrapper(self, parser):
        """Ensure real OpenAI format with 'function' wrapper still works."""
        response = json.dumps(
            {
                "tool_calls": [
                    {
                        "id": "call_xyz",
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
        assert result[0].id == "call_xyz"


class TestRepairToolHistory:
    """Tests for repair_tool_history safety net."""

    def test_drops_assistant_msg_when_all_tool_calls_unrecognized(self):
        """When all tool calls in an assistant message have unknown names,
        the entire message should be removed to prevent orphaned tool_use."""
        from custom_components.homeclaw.core.context_builder import repair_tool_history
        from custom_components.homeclaw.core.tool_call_codec import (
            build_assistant_tool_message,
        )

        canonical = build_assistant_tool_message(
            [{"id": "toolu_1", "name": "nonexistent_tool", "args": {}}]
        )

        messages = [
            {"role": "user", "content": "do something"},
            {"role": "assistant", "content": canonical},
            {
                "role": "function",
                "name": "nonexistent_tool",
                "tool_use_id": "toolu_1",
                "content": '{"result": "ok"}',
            },
            {"role": "assistant", "content": "Done!"},
        ]

        def detect_fn(text):
            from custom_components.homeclaw.core.function_call_parser import (
                FunctionCallParser,
            )
            from custom_components.homeclaw.core.response_parser import ResponseParser

            return FunctionCallParser(ResponseParser()).detect(text)

        result = repair_tool_history(
            messages, detect_fn, allowed_tool_names={"get_state", "call_service"}
        )

        # Both the tool_use assistant msg and orphaned tool_result should be gone
        roles = [m["role"] for m in result]
        assert roles == ["user", "assistant"]
        assert result[1]["content"] == "Done!"

    def test_keeps_assistant_msg_when_tool_calls_recognized(self):
        """When tool calls are recognized, assistant message stays."""
        from custom_components.homeclaw.core.context_builder import repair_tool_history
        from custom_components.homeclaw.core.tool_call_codec import (
            build_assistant_tool_message,
        )

        canonical = build_assistant_tool_message(
            [{"id": "toolu_1", "name": "get_state", "args": {"entity_id": "light.a"}}]
        )

        messages = [
            {"role": "user", "content": "check light"},
            {"role": "assistant", "content": canonical},
            {
                "role": "function",
                "name": "get_state",
                "tool_use_id": "toolu_1",
                "content": '{"state": "on"}',
            },
            {"role": "assistant", "content": "The light is on."},
        ]

        def detect_fn(text):
            from custom_components.homeclaw.core.function_call_parser import (
                FunctionCallParser,
            )
            from custom_components.homeclaw.core.response_parser import ResponseParser

            return FunctionCallParser(ResponseParser()).detect(text)

        result = repair_tool_history(
            messages, detect_fn, allowed_tool_names={"get_state"}
        )

        roles = [m["role"] for m in result]
        assert roles == ["user", "assistant", "function", "assistant"]
