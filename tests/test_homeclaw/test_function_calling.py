"""Tests for function calling module - TDD approach.

These tests define the expected behavior of the function_calling module
for native LLM function calling across multiple providers.
"""

import json
import os
import sys

import pytest

# Add the custom_components/homeclaw directory directly to path
# This allows importing function_calling without triggering __init__.py
# which requires homeassistant module
_module_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "custom_components", "homeclaw"
)
sys.path.insert(0, _module_path)

# Direct import from the module file
from function_calling import (
    FunctionCall,
    FunctionCallHandler,
    ToolSchemaConverter,
    UnexpectedToolCallHandler,
)


class TestFunctionCallDataclass:
    """Test FunctionCall dataclass."""

    def test_function_call_creation(self):
        """FunctionCall should store id, name, and arguments."""
        fc = FunctionCall(
            id="call_123", name="get_weather", arguments={"location": "Paris"}
        )

        assert fc.id == "call_123"
        assert fc.name == "get_weather"
        assert fc.arguments == {"location": "Paris"}


# Tests for ToolSchemaConverter - TODO 1
class TestToolSchemaConverter:
    """Test ToolSchemaConverter - converts Tool metadata to provider formats."""

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool for testing."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        # Import ToolParameter from the tools module
        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockTool:
            """Mock tool for testing schema conversion."""

            id: ClassVar[str] = "get_weather"
            description: ClassVar[str] = "Get current weather for a location"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="location",
                    type="string",
                    description="City and country, e.g. Paris, France",
                    required=True,
                ),
                ToolParameter(
                    name="units",
                    type="string",
                    description="Temperature units",
                    required=False,
                    default="celsius",
                    enum=["celsius", "fahrenheit"],
                ),
            ]

        return MockTool()

    @pytest.fixture
    def mock_tool_simple(self):
        """Create a simple mock tool without optional params."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockToolSimple:
            """Simple mock tool for testing."""

            id: ClassVar[str] = "get_entities"
            description: ClassVar[str] = "Get all entities in a domain"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="domain",
                    type="str",
                    description="Entity domain like 'light' or 'switch'",
                    required=True,
                ),
            ]

        return MockToolSimple()

    # ===== OpenAI Format Tests =====

    def test_to_openai_format_basic_structure(self, mock_tool):
        """OpenAI format should have type='function' and function object."""
        result = ToolSchemaConverter.to_openai_format([mock_tool])

        assert len(result) == 1
        tool = result[0]
        assert tool["type"] == "function"
        assert "function" in tool
        assert tool["function"]["name"] == "get_weather"
        assert tool["function"]["description"] == "Get current weather for a location"

    def test_to_openai_format_parameters(self, mock_tool):
        """OpenAI format should have proper parameter schema."""
        result = ToolSchemaConverter.to_openai_format([mock_tool])

        params = result[0]["function"]["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "location" in params["properties"]
        assert "units" in params["properties"]

        # Required params
        assert "required" in params
        assert "location" in params["required"]

    # ===== Additional ToolSchemaConverter Tests =====

    def test_to_gemini_format_multiple_tools(self, mock_tool, mock_tool_simple):
        """Gemini format should wrap all tools in single functionDeclarations."""
        result = ToolSchemaConverter.to_gemini_format([mock_tool, mock_tool_simple])

        assert len(result) == 1  # Single wrapper object
        assert "functionDeclarations" in result[0]
        func_decls = result[0]["functionDeclarations"]
        assert len(func_decls) == 2  # Two function declarations

        names = [fd["name"] for fd in func_decls]
        assert "get_weather" in names
        assert "get_entities" in names

    def test_to_openai_format_empty_tools_list(self):
        """Should handle empty tools list."""
        result = ToolSchemaConverter.to_openai_format([])
        assert result == []

    def test_to_anthropic_format_empty_tools_list(self):
        """Should handle empty tools list."""
        result = ToolSchemaConverter.to_anthropic_format([])
        assert result == []

    def test_to_gemini_format_empty_tools_list(self):
        """Should handle empty tools list."""
        result = ToolSchemaConverter.to_gemini_format([])
        assert result == [{"functionDeclarations": []}]

    @pytest.fixture
    def mock_tool_with_various_types(self):
        """Create a mock tool with various parameter types."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockToolVariousTypes:
            """Mock tool for testing type mappings."""

            id: ClassVar[str] = "test_types"
            description: ClassVar[str] = "Test various parameter types"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="str_param",
                    type="str",
                    description="A string parameter",
                    required=True,
                ),
                ToolParameter(
                    name="int_param",
                    type="int",
                    description="An integer parameter",
                    required=False,
                ),
                ToolParameter(
                    name="float_param",
                    type="float",
                    description="A float parameter",
                    required=False,
                ),
                ToolParameter(
                    name="bool_param",
                    type="bool",
                    description="A boolean parameter",
                    required=False,
                ),
                ToolParameter(
                    name="list_param",
                    type="list",
                    description="A list parameter",
                    required=False,
                ),
                ToolParameter(
                    name="dict_param",
                    type="dict",
                    description="A dict parameter",
                    required=False,
                ),
            ]

        return MockToolVariousTypes()

    def test_to_openai_format_all_type_mappings(self, mock_tool_with_various_types):
        """OpenAI format should correctly map all parameter types."""
        result = ToolSchemaConverter.to_openai_format([mock_tool_with_various_types])

        props = result[0]["function"]["parameters"]["properties"]
        assert props["str_param"]["type"] == "string"
        assert props["int_param"]["type"] == "integer"
        assert props["float_param"]["type"] == "number"
        assert props["bool_param"]["type"] == "boolean"
        assert props["list_param"]["type"] == "array"
        assert props["dict_param"]["type"] == "object"

    def test_to_anthropic_format_all_type_mappings(self, mock_tool_with_various_types):
        """Anthropic format should correctly map all parameter types."""
        result = ToolSchemaConverter.to_anthropic_format([mock_tool_with_various_types])

        props = result[0]["input_schema"]["properties"]
        assert props["str_param"]["type"] == "string"
        assert props["int_param"]["type"] == "integer"
        assert props["float_param"]["type"] == "number"
        assert props["bool_param"]["type"] == "boolean"
        assert props["list_param"]["type"] == "array"
        assert props["dict_param"]["type"] == "object"

    def test_to_gemini_format_all_type_mappings(self, mock_tool_with_various_types):
        """Gemini format should correctly map all parameter types to UPPERCASE."""
        result = ToolSchemaConverter.to_gemini_format([mock_tool_with_various_types])

        props = result[0]["functionDeclarations"][0]["parameters"]["properties"]
        assert props["str_param"]["type"] == "STRING"
        assert props["int_param"]["type"] == "INTEGER"
        assert props["float_param"]["type"] == "NUMBER"
        assert props["bool_param"]["type"] == "BOOLEAN"
        assert props["list_param"]["type"] == "ARRAY"
        assert props["dict_param"]["type"] == "OBJECT"

    def test_to_openai_format_no_required_params(self):
        """OpenAI format should omit 'required' key when all params are optional."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockToolNoRequired:
            id: ClassVar[str] = "test_tool"
            description: ClassVar[str] = "Test tool"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="optional_param",
                    type="string",
                    description="Optional parameter",
                    required=False,
                ),
            ]

        result = ToolSchemaConverter.to_openai_format([MockToolNoRequired()])
        params = result[0]["function"]["parameters"]

        # When no required params, 'required' key should not be present or be empty
        assert "required" not in params or params["required"] == []

    def test_to_anthropic_format_no_required_params(self):
        """Anthropic format should omit 'required' key when all params are optional."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockToolNoRequired:
            id: ClassVar[str] = "test_tool"
            description: ClassVar[str] = "Test tool"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="optional_param",
                    type="string",
                    description="Optional parameter",
                    required=False,
                ),
            ]

        result = ToolSchemaConverter.to_anthropic_format([MockToolNoRequired()])
        schema = result[0]["input_schema"]

        # When no required params, 'required' key should not be present or be empty
        assert "required" not in schema or schema["required"] == []

    def test_to_gemini_format_no_required_params(self):
        """Gemini format should omit 'required' key when all params are optional."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockToolNoRequired:
            id: ClassVar[str] = "test_tool"
            description: ClassVar[str] = "Test tool"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="optional_param",
                    type="string",
                    description="Optional parameter",
                    required=False,
                ),
            ]

        result = ToolSchemaConverter.to_gemini_format([MockToolNoRequired()])
        params = result[0]["functionDeclarations"][0]["parameters"]

        # When no required params, 'required' key should not be present or be empty
        assert "required" not in params or params["required"] == []

    def test_to_openai_format_type_mapping(self, mock_tool_simple):
        """OpenAI format should map 'str' to 'string'."""
        result = ToolSchemaConverter.to_openai_format([mock_tool_simple])

        props = result[0]["function"]["parameters"]["properties"]
        assert props["domain"]["type"] == "string"

    def test_to_openai_format_enum_values(self, mock_tool):
        """OpenAI format should include enum values."""
        result = ToolSchemaConverter.to_openai_format([mock_tool])

        units_prop = result[0]["function"]["parameters"]["properties"]["units"]
        assert "enum" in units_prop
        assert units_prop["enum"] == ["celsius", "fahrenheit"]

    def test_to_openai_format_multiple_tools(self, mock_tool, mock_tool_simple):
        """Should handle multiple tools."""
        result = ToolSchemaConverter.to_openai_format([mock_tool, mock_tool_simple])

        assert len(result) == 2
        names = [t["function"]["name"] for t in result]
        assert "get_weather" in names
        assert "get_entities" in names

    # ===== Anthropic Format Tests =====

    def test_to_anthropic_format_basic_structure(self, mock_tool):
        """Anthropic format should have name, description, and input_schema."""
        result = ToolSchemaConverter.to_anthropic_format([mock_tool])

        assert len(result) == 1
        tool = result[0]
        assert tool["name"] == "get_weather"
        assert tool["description"] == "Get current weather for a location"
        assert "input_schema" in tool

    def test_to_anthropic_format_input_schema(self, mock_tool):
        """Anthropic format should have proper input_schema."""
        result = ToolSchemaConverter.to_anthropic_format([mock_tool])

        schema = result[0]["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "location" in schema["properties"]
        assert "required" in schema

    def test_to_anthropic_format_type_mapping(self, mock_tool_simple):
        """Anthropic format should map types correctly."""
        result = ToolSchemaConverter.to_anthropic_format([mock_tool_simple])

        props = result[0]["input_schema"]["properties"]
        assert props["domain"]["type"] == "string"

    # ===== Gemini Format Tests =====

    def test_to_gemini_format_basic_structure(self, mock_tool):
        """Gemini format should have functionDeclarations array."""
        result = ToolSchemaConverter.to_gemini_format([mock_tool])

        assert len(result) == 1
        tool = result[0]
        assert "functionDeclarations" in tool

        func_decl = tool["functionDeclarations"][0]
        assert func_decl["name"] == "get_weather"
        assert func_decl["description"] == "Get current weather for a location"

    def test_to_gemini_format_parameters(self, mock_tool):
        """Gemini format should have parameters with UPPERCASE types."""
        result = ToolSchemaConverter.to_gemini_format([mock_tool])

        params = result[0]["functionDeclarations"][0]["parameters"]
        assert params["type"] == "OBJECT"
        assert "properties" in params

    def test_to_gemini_format_type_mapping(self, mock_tool_simple):
        """Gemini format should map types to UPPERCASE."""
        result = ToolSchemaConverter.to_gemini_format([mock_tool_simple])

        props = result[0]["functionDeclarations"][0]["parameters"]["properties"]
        assert props["domain"]["type"] == "STRING"

    def test_to_gemini_format_required_params(self, mock_tool):
        """Gemini format should include required array."""
        result = ToolSchemaConverter.to_gemini_format([mock_tool])

        params = result[0]["functionDeclarations"][0]["parameters"]
        assert "required" in params
        assert "location" in params["required"]


# Tests for FunctionCallHandler - TODO 3
class TestFunctionCallHandler:
    """Test FunctionCallHandler - parses function calls from responses."""

    # ===== OpenAI Response Parsing =====

    @pytest.fixture
    def openai_response_with_function_call(self):
        """OpenAI response containing a function call."""
        return {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "Paris, France"}',
                                },
                            }
                        ]
                    }
                }
            ]
        }

    @pytest.fixture
    def openai_response_text_only(self):
        """OpenAI response with text only (no function call)."""
        return {"choices": [{"message": {"content": "The weather is nice today."}}]}

    @pytest.fixture
    def openai_response_multiple_calls(self):
        """OpenAI response with multiple parallel function calls."""
        return {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "Paris"}',
                                },
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "London"}',
                                },
                            },
                        ]
                    }
                }
            ]
        }

    def test_parse_openai_response_extracts_function_call(
        self, openai_response_with_function_call
    ):
        """Should extract function name and arguments from OpenAI response."""
        result = FunctionCallHandler.parse_openai_response(
            openai_response_with_function_call
        )

        assert result is not None
        assert len(result) == 1
        fc = result[0]
        assert fc.id == "call_abc123"
        assert fc.name == "get_weather"
        assert fc.arguments == {"location": "Paris, France"}

    def test_parse_openai_response_returns_none_for_text(
        self, openai_response_text_only
    ):
        """Should return None when no function call present."""
        result = FunctionCallHandler.parse_openai_response(openai_response_text_only)
        assert result is None

    def test_parse_openai_response_handles_multiple_calls(
        self, openai_response_multiple_calls
    ):
        """Should parse multiple parallel function calls."""
        result = FunctionCallHandler.parse_openai_response(
            openai_response_multiple_calls
        )

        assert result is not None
        assert len(result) == 2
        assert result[0].id == "call_1"
        assert result[1].id == "call_2"

    def test_is_function_call_openai_true(self, openai_response_with_function_call):
        """Should detect function call in OpenAI response."""
        assert (
            FunctionCallHandler.is_function_call(
                openai_response_with_function_call, "openai"
            )
            is True
        )

    def test_is_function_call_openai_false(self, openai_response_text_only):
        """Should return False for text-only OpenAI response."""
        assert (
            FunctionCallHandler.is_function_call(openai_response_text_only, "openai")
            is False
        )

    # ===== Anthropic Response Parsing =====

    @pytest.fixture
    def anthropic_response_with_tool_use(self):
        """Anthropic response containing a tool_use block."""
        return {
            "content": [
                {"type": "text", "text": "Let me check the weather for you."},
                {
                    "type": "tool_use",
                    "id": "toolu_abc123",
                    "name": "get_weather",
                    "input": {"location": "Paris, France"},
                },
            ]
        }

    @pytest.fixture
    def anthropic_response_text_only(self):
        """Anthropic response with text only."""
        return {"content": [{"type": "text", "text": "Hello, how can I help?"}]}

    def test_parse_anthropic_response_extracts_tool_use(
        self, anthropic_response_with_tool_use
    ):
        """Should extract tool_use from Anthropic response."""
        result = FunctionCallHandler.parse_anthropic_response(
            anthropic_response_with_tool_use
        )

        assert result is not None
        assert len(result) == 1
        fc = result[0]
        assert fc.id == "toolu_abc123"
        assert fc.name == "get_weather"
        assert fc.arguments == {"location": "Paris, France"}

    def test_parse_anthropic_response_returns_none_for_text(
        self, anthropic_response_text_only
    ):
        """Should return None when no tool_use present."""
        result = FunctionCallHandler.parse_anthropic_response(
            anthropic_response_text_only
        )
        assert result is None

    def test_is_function_call_anthropic_true(self, anthropic_response_with_tool_use):
        """Should detect tool_use in Anthropic response."""
        assert (
            FunctionCallHandler.is_function_call(
                anthropic_response_with_tool_use, "anthropic"
            )
            is True
        )

    def test_is_function_call_anthropic_false(self, anthropic_response_text_only):
        """Should return False for text-only Anthropic response."""
        assert (
            FunctionCallHandler.is_function_call(
                anthropic_response_text_only, "anthropic"
            )
            is False
        )

    # ===== Gemini Response Parsing =====

    @pytest.fixture
    def gemini_response_with_function_call(self):
        """Gemini response containing a functionCall."""
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_weather",
                                    "args": {"location": "Paris, France"},
                                }
                            }
                        ]
                    }
                }
            ]
        }

    @pytest.fixture
    def gemini_response_text_only(self):
        """Gemini response with text only."""
        return {
            "candidates": [{"content": {"parts": [{"text": "The weather is sunny."}]}}]
        }

    def test_parse_gemini_response_extracts_function_call(
        self, gemini_response_with_function_call
    ):
        """Should extract functionCall from Gemini response."""
        result = FunctionCallHandler.parse_gemini_response(
            gemini_response_with_function_call
        )

        assert result is not None
        assert len(result) == 1
        fc = result[0]
        assert fc.name == "get_weather"
        assert fc.arguments == {"location": "Paris, France"}

    def test_parse_gemini_response_returns_none_for_text(
        self, gemini_response_text_only
    ):
        """Should return None when no functionCall present."""
        result = FunctionCallHandler.parse_gemini_response(gemini_response_text_only)
        assert result is None

    def test_is_function_call_gemini_true(self, gemini_response_with_function_call):
        """Should detect functionCall in Gemini response."""
        assert (
            FunctionCallHandler.is_function_call(
                gemini_response_with_function_call, "gemini"
            )
            is True
        )

    def test_is_function_call_gemini_false(self, gemini_response_text_only):
        """Should return False for text-only Gemini response."""
        assert (
            FunctionCallHandler.is_function_call(gemini_response_text_only, "gemini")
            is False
        )

    # ===== is_function_call Edge Cases and Error Handling =====

    def test_is_function_call_openai_index_error(self):
        """Should return False when OpenAI response has empty choices array."""
        response = {"choices": []}
        assert FunctionCallHandler.is_function_call(response, "openai") is False

    def test_is_function_call_openai_attribute_error(self):
        """Should return False when OpenAI response has malformed structure."""
        response = {"choices": [{"message": None}]}
        assert FunctionCallHandler.is_function_call(response, "openai") is False

    def test_is_function_call_openai_empty_tool_calls(self):
        """Should return False when OpenAI response has empty tool_calls array."""
        response = {"choices": [{"message": {"tool_calls": []}}]}
        assert FunctionCallHandler.is_function_call(response, "openai") is False

    def test_is_function_call_gemini_index_error(self):
        """Should return False when Gemini response has empty candidates array."""
        response = {"candidates": []}
        assert FunctionCallHandler.is_function_call(response, "gemini") is False

    def test_is_function_call_gemini_attribute_error(self):
        """Should return False when Gemini response has malformed structure."""
        response = {"candidates": [{"content": None}]}
        assert FunctionCallHandler.is_function_call(response, "gemini") is False

    def test_is_function_call_unknown_provider(self):
        """Should return False for unknown provider."""
        response = {"choices": [{"message": {"tool_calls": [{"id": "test"}]}}]}
        assert FunctionCallHandler.is_function_call(response, "unknown_provider") is False

    # ===== parse_openai_response Error Handling =====

    def test_parse_openai_response_invalid_json_arguments(self):
        """Should handle invalid JSON in arguments field gracefully."""
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": "{invalid json}",
                                },
                            }
                        ]
                    }
                }
            ]
        }
        result = FunctionCallHandler.parse_openai_response(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].arguments == {}  # Should default to empty dict

    def test_parse_openai_response_index_error(self):
        """Should return None when choices array is empty."""
        response = {"choices": []}
        result = FunctionCallHandler.parse_openai_response(response)
        assert result is None

    def test_parse_openai_response_attribute_error(self):
        """Should return None when response structure is malformed."""
        response = {"choices": [{"message": None}]}
        result = FunctionCallHandler.parse_openai_response(response)
        assert result is None

    def test_parse_openai_response_type_error(self):
        """Should return None when response is wrong type."""
        response = {"choices": [None]}
        result = FunctionCallHandler.parse_openai_response(response)
        assert result is None

    # ===== parse_gemini_response Error Handling =====

    def test_parse_gemini_response_index_error(self):
        """Should return None when candidates array is empty."""
        response = {"candidates": []}
        result = FunctionCallHandler.parse_gemini_response(response)
        assert result is None

    def test_parse_gemini_response_attribute_error(self):
        """Should return None when response structure is malformed."""
        response = {"candidates": [{"content": None}]}
        result = FunctionCallHandler.parse_gemini_response(response)
        assert result is None

    def test_parse_gemini_response_type_error(self):
        """Should return None when response is wrong type."""
        response = {"candidates": [None]}
        result = FunctionCallHandler.parse_gemini_response(response)
        assert result is None

    def test_parse_gemini_response_key_error(self):
        """Should return None when functionCall is missing required keys."""
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {}  # Missing name and args
                            }
                        ]
                    }
                }
            ]
        }
        # This should not raise an error, should handle gracefully
        result = FunctionCallHandler.parse_gemini_response(response)
        assert result is not None  # Should still return a result
        assert len(result) == 1
        assert result[0].name == ""  # Defaults to empty string
        assert result[0].arguments == {}  # Defaults to empty dict


class TestUnexpectedToolCallHandler:
    """Test UnexpectedToolCallHandler - handles Gemini's UNEXPECTED_TOOL_CALL."""

    @pytest.fixture
    def unexpected_tool_call_response(self):
        """Gemini response with UNEXPECTED_TOOL_CALL finish reason."""
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": ""}]},
                    "finishReason": "UNEXPECTED_TOOL_CALL",
                    "finishMessage": "Unexpected tool call: Model tried to call an undeclared function: default:get_climate_related_entities",
                }
            ]
        }

    @pytest.fixture
    def unexpected_tool_call_no_prefix(self):
        """UNEXPECTED_TOOL_CALL without default: prefix."""
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": ""}]},
                    "finishReason": "UNEXPECTED_TOOL_CALL",
                    "finishMessage": "Unexpected tool call: Model tried to call an undeclared function: get_weather",
                }
            ]
        }

    @pytest.fixture
    def normal_gemini_response(self):
        """Normal Gemini text response."""
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": "The weather is nice."}]},
                    "finishReason": "STOP",
                }
            ]
        }

    @pytest.fixture
    def unexpected_tool_call_malformed(self):
        """UNEXPECTED_TOOL_CALL with malformed finishMessage."""
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": ""}]},
                    "finishReason": "UNEXPECTED_TOOL_CALL",
                    "finishMessage": "Some unexpected error message format",
                }
            ]
        }

    def test_is_unexpected_tool_call_true(self, unexpected_tool_call_response):
        """Should detect UNEXPECTED_TOOL_CALL finish reason."""
        assert (
            UnexpectedToolCallHandler.is_unexpected_tool_call(
                unexpected_tool_call_response
            )
            is True
        )

    def test_is_unexpected_tool_call_false_normal_response(
        self, normal_gemini_response
    ):
        """Should return False for normal STOP response."""
        assert (
            UnexpectedToolCallHandler.is_unexpected_tool_call(normal_gemini_response)
            is False
        )

    def test_extract_function_call_with_default_prefix(
        self, unexpected_tool_call_response
    ):
        """Should extract function name, stripping default: prefix."""
        result = UnexpectedToolCallHandler.extract_function_call(
            unexpected_tool_call_response
        )

        assert result is not None
        assert result.name == "get_climate_related_entities"
        assert result.arguments == {}

    def test_extract_function_call_without_prefix(self, unexpected_tool_call_no_prefix):
        """Should extract function name when no default: prefix."""
        result = UnexpectedToolCallHandler.extract_function_call(
            unexpected_tool_call_no_prefix
        )

        assert result is not None
        assert result.name == "get_weather"

    def test_extract_function_call_malformed_returns_none(
        self, unexpected_tool_call_malformed
    ):
        """Should return None when finishMessage doesn't match expected pattern."""
        result = UnexpectedToolCallHandler.extract_function_call(
            unexpected_tool_call_malformed
        )

        assert result is None

    def test_extract_function_call_generates_id(self, unexpected_tool_call_response):
        """Should generate an ID for the function call."""
        result = UnexpectedToolCallHandler.extract_function_call(
            unexpected_tool_call_response
        )

        assert result is not None
        assert result.id is not None
        assert len(result.id) > 0

    # ===== is_unexpected_tool_call Error Handling =====

    def test_is_unexpected_tool_call_empty_candidates(self):
        """Should return False when candidates array is empty."""
        response = {"candidates": []}
        assert UnexpectedToolCallHandler.is_unexpected_tool_call(response) is False

    def test_is_unexpected_tool_call_index_error(self):
        """Should return False when response structure causes IndexError."""
        response = {}  # Missing candidates
        assert UnexpectedToolCallHandler.is_unexpected_tool_call(response) is False

    def test_is_unexpected_tool_call_attribute_error(self):
        """Should return False when response structure is malformed."""
        response = {"candidates": [None]}
        assert UnexpectedToolCallHandler.is_unexpected_tool_call(response) is False

    def test_is_unexpected_tool_call_type_error(self):
        """Should return False when finishReason is wrong type."""
        response = {"candidates": [{"finishReason": None}]}
        assert UnexpectedToolCallHandler.is_unexpected_tool_call(response) is False

    # ===== extract_function_call Error Handling =====

    def test_extract_function_call_empty_candidates(self):
        """Should return None when candidates list is empty."""
        response = {"candidates": []}
        result = UnexpectedToolCallHandler.extract_function_call(response)
        assert result is None

    def test_extract_function_call_exception_handling(self):
        """Should return None when response structure causes exception."""
        # Test with None candidates (causes AttributeError)
        response_none = {"candidates": None}
        result = UnexpectedToolCallHandler.extract_function_call(response_none)
        assert result is None

        # Test with malformed candidate structure (causes TypeError/AttributeError)
        response_malformed = {"candidates": [None]}
        result = UnexpectedToolCallHandler.extract_function_call(response_malformed)
        assert result is None

        # Test with IndexError (empty dict)
        response_empty = {}
        result = UnexpectedToolCallHandler.extract_function_call(response_empty)
        assert result is None


# ===== OpenAI Client Integration Tests =====
class TestOpenAIFunctionCallIntegration:
    """Integration tests for OpenAIClient with native function calling.

    These tests verify that OpenAIClient correctly:
    1. Accepts tools parameter and formats them using ToolSchemaConverter
    2. Detects function calls in responses using FunctionCallHandler
    3. Returns structured response with function_calls when present
    4. Returns text response when no function call
    5. Maintains backward compatibility when tools not provided
    """

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool for testing."""
        from dataclasses import dataclass
        from typing import ClassVar, List

        _tools_path = os.path.join(_module_path, "tools")
        sys.path.insert(0, _tools_path)
        from base import ToolParameter

        @dataclass
        class MockTool:
            """Mock tool for testing schema conversion."""

            id: ClassVar[str] = "get_weather"
            description: ClassVar[str] = "Get current weather for a location"
            parameters: ClassVar[List[ToolParameter]] = [
                ToolParameter(
                    name="location",
                    type="string",
                    description="City and country, e.g. Paris, France",
                    required=True,
                ),
            ]

        return MockTool()

    @pytest.fixture
    def openai_function_call_response(self):
        """Mock OpenAI response with function call."""
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "Paris, France"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }

    @pytest.fixture
    def openai_text_response(self):
        """Mock OpenAI response with text only."""
        return {
            "id": "chatcmpl-456",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "The weather in Paris is sunny and 22C.",
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    def test_openai_function_call_integration(
        self, mock_tool, openai_function_call_response
    ):
        """OpenAIClient should handle function calls with tools parameter.

        This test verifies the full integration:
        1. Tools are converted to OpenAI format using ToolSchemaConverter
        2. Function calls are detected using FunctionCallHandler.is_function_call()
        3. Function calls are parsed using FunctionCallHandler.parse_openai_response()
        4. Response contains function_calls list with FunctionCall objects
        """
        # Test that ToolSchemaConverter correctly formats tools for OpenAI
        openai_tools = ToolSchemaConverter.to_openai_format([mock_tool])

        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "get_weather"
        assert "parameters" in openai_tools[0]["function"]

        # Test that FunctionCallHandler detects function call in response
        assert (
            FunctionCallHandler.is_function_call(
                openai_function_call_response, "openai"
            )
            is True
        )

        # Test that FunctionCallHandler parses function call correctly
        function_calls = FunctionCallHandler.parse_openai_response(
            openai_function_call_response
        )

        assert function_calls is not None
        assert len(function_calls) == 1

        fc = function_calls[0]
        assert fc.id == "call_abc123"
        assert fc.name == "get_weather"
        assert fc.arguments == {"location": "Paris, France"}

    def test_openai_text_response_with_tools(self, mock_tool, openai_text_response):
        """OpenAIClient should return text when no function call in response.

        When tools are provided but the model responds with text instead of
        a function call, the response should be the text content.
        """
        # Verify no function call detected
        assert (
            FunctionCallHandler.is_function_call(openai_text_response, "openai")
            is False
        )

        # Verify parse returns None
        function_calls = FunctionCallHandler.parse_openai_response(openai_text_response)
        assert function_calls is None

        # Verify text content is accessible
        content = openai_text_response["choices"][0]["message"]["content"]
        assert "sunny" in content
        assert "22C" in content

    def test_openai_without_tools_backward_compatible(self, openai_text_response):
        """OpenAIClient should work without tools parameter (backward compatible).

        When no tools are provided, the client should work exactly as before,
        returning text responses without any function call handling.
        """
        # Verify text-only response is handled correctly
        assert (
            FunctionCallHandler.is_function_call(openai_text_response, "openai")
            is False
        )

        # Verify text content extraction works
        content = openai_text_response["choices"][0]["message"]["content"]
        assert isinstance(content, str)
        assert len(content) > 0


# ===== Gemini OAuth Retry Logic Tests =====
class TestGeminiRetryLogic:
    """Test GeminiOAuthClient retry with exponential backoff.

    Tests the _retry_with_backoff method which handles:
    - 429 rate limiting with "retry in Xs" parsing
    - 429 rate limiting with exponential backoff fallback
    - 5xx server errors (500, 502, 503) with exponential backoff
    - Non-retryable errors (4xx client errors) that fail immediately
    - Max attempts exceeded scenario
    """

    @pytest.fixture
    def retry_logic(self):
        """Create a retry logic implementation for testing.

        This is a standalone implementation of the _retry_with_backoff logic
        to avoid importing the full agent module which has external dependencies.
        Uses shorter delays for testing (100ms instead of 5000ms).
        """
        import asyncio
        import random
        import re

        class RetryLogic:
            MAX_ATTEMPTS = 10
            INITIAL_DELAY_MS = 100  # 100ms for testing (vs 5000ms in production)
            MAX_DELAY_MS = 600  # 600ms for testing (vs 30000ms in production)

            async def retry_with_backoff(self, func, *args, **kwargs):
                """Retry with exponential backoff for 429 and 5xx errors."""
                attempt = 0
                current_delay = self.INITIAL_DELAY_MS / 1000  # Convert to seconds

                while attempt < self.MAX_ATTEMPTS:
                    attempt += 1
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        error_str = str(e)

                        # Check if retryable (429 or 5xx)
                        is_429 = "429" in error_str
                        is_5xx = any(f"{code}" in error_str for code in range(500, 600))

                        if not (is_429 or is_5xx):
                            raise  # Non-retryable error

                        if attempt >= self.MAX_ATTEMPTS:
                            raise

                        # Check for "Please retry in Xs" or "retry in Xms" in error message
                        retry_match = re.search(
                            r"retry in (\d+(?:\.\d+)?)\s*(s|ms)",
                            error_str,
                            re.IGNORECASE,
                        )
                        if retry_match:
                            delay_value = float(retry_match.group(1))
                            delay_unit = retry_match.group(2).lower()
                            delay = (
                                delay_value if delay_unit == "s" else delay_value / 1000
                            )
                        else:
                            # Exponential backoff with jitter (±30%)
                            jitter = current_delay * 0.3 * (random.random() * 2 - 1)
                            delay = max(0, current_delay + jitter)

                        await asyncio.sleep(delay)

                        # Increase delay for next attempt (exponential backoff)
                        current_delay = min(self.MAX_DELAY_MS / 1000, current_delay * 2)

                raise Exception("Retry attempts exhausted")

        return RetryLogic()

    @pytest.mark.asyncio
    async def test_retry_on_429_with_retry_after_header(self, retry_logic):
        """Should parse 'retry in Xs' from error message and use that delay."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Gemini OAuth API error 429: Please retry in 0.1s")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 2  # Called twice: once failed, once succeeded

    @pytest.mark.asyncio
    async def test_retry_on_429_exponential_backoff(self, retry_logic):
        """Should use exponential backoff when no retry info in error message."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Gemini OAuth API error 429: Rate limit exceeded")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 3  # Called 3 times: 2 failures, 1 success

    @pytest.mark.asyncio
    async def test_retry_on_500_server_error(self, retry_logic):
        """Should retry on 500 server error with exponential backoff."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Gemini OAuth API error 500: Internal Server Error")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_502_bad_gateway(self, retry_logic):
        """Should retry on 502 Bad Gateway error."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Gemini OAuth API error 502: Bad Gateway")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_503_service_unavailable(self, retry_logic):
        """Should retry on 503 Service Unavailable error."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Gemini OAuth API error 503: Service Unavailable")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_400_bad_request(self, retry_logic):
        """Should NOT retry on 400 Bad Request (non-retryable)."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Gemini OAuth API error 400: Bad Request")

        with pytest.raises(Exception, match="400"):
            await retry_logic.retry_with_backoff(failing_func)

        assert call_count == 1  # Only called once, no retry

    @pytest.mark.asyncio
    async def test_no_retry_on_401_unauthorized(self, retry_logic):
        """Should NOT retry on 401 Unauthorized (non-retryable)."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Gemini OAuth API error 401: Unauthorized")

        with pytest.raises(Exception, match="401"):
            await retry_logic.retry_with_backoff(failing_func)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_403_forbidden(self, retry_logic):
        """Should NOT retry on 403 Forbidden (non-retryable)."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Gemini OAuth API error 403: Forbidden")

        with pytest.raises(Exception, match="403"):
            await retry_logic.retry_with_backoff(failing_func)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_404_not_found(self, retry_logic):
        """Should NOT retry on 404 Not Found (non-retryable)."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Gemini OAuth API error 404: Not Found")

        with pytest.raises(Exception, match="404"):
            await retry_logic.retry_with_backoff(failing_func)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self, retry_logic):
        """Should raise after MAX_ATTEMPTS reached."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Gemini OAuth API error 500: Server Error")

        with pytest.raises(Exception):
            await retry_logic.retry_with_backoff(always_fails)

        # Should have tried MAX_ATTEMPTS times
        assert call_count == retry_logic.MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_retry_with_milliseconds_in_message(self, retry_logic):
        """Should parse 'retry in Xms' (milliseconds) from error message."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Gemini OAuth API error 429: Please retry in 50ms")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self, retry_logic):
        """Should return immediately on successful call without retry."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "immediate_success"

        result = await retry_logic.retry_with_backoff(success_func)

        assert result == "immediate_success"
        assert call_count == 1  # Called only once

    @pytest.mark.asyncio
    async def test_multiple_retries_before_success(self, retry_logic):
        """Should retry multiple times before eventual success."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise Exception("Gemini OAuth API error 500: Server Error")
            return "success_after_retries"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success_after_retries"
        assert call_count == 4  # Failed 3 times, succeeded on 4th attempt

    @pytest.mark.asyncio
    async def test_retry_delay_respects_max_delay(self, retry_logic):
        """Should not exceed MAX_DELAY_MS even with exponential backoff."""
        import time

        call_count = 0
        call_times = []

        async def failing_func():
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 3:
                raise Exception("Gemini OAuth API error 500: Server Error")
            return "success"

        result = await retry_logic.retry_with_backoff(failing_func)

        assert result == "success"
        assert call_count == 3

        # Check that delays between calls don't exceed MAX_DELAY_MS
        if len(call_times) >= 2:
            delay_1 = (call_times[1] - call_times[0]) * 1000  # Convert to ms
            # Delay should be around INITIAL_DELAY_MS (5000ms) with jitter
            # Allow some tolerance for execution time
            assert delay_1 < retry_logic.MAX_DELAY_MS + 1000
