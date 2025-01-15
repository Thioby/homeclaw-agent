"""Function calling module for native LLM tool integration.

This module provides converters and handlers for native function calling
across multiple LLM providers (OpenAI, Anthropic, Gemini).

Classes:
    FunctionCall: Dataclass representing a parsed function call
    ToolSchemaConverter: Converts Tool metadata to provider-specific formats
    FunctionCallHandler: Parses function calls from provider responses
    UnexpectedToolCallHandler: Handles Gemini's UNEXPECTED_TOOL_CALL errors
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .tools.base import Tool

_LOGGER = logging.getLogger(__name__)


@dataclass
class FunctionCall:
    """Represents a parsed function call from an LLM response.

    Attributes:
        id: Unique identifier for the function call (provider-specific)
        name: Name of the function to call
        arguments: Dictionary of arguments for the function
    """

    id: str
    name: str
    arguments: Dict[str, Any]


class ToolSchemaConverter:
    """Converts Tool metadata to provider-specific schema formats.

    Supports:
        - OpenAI: tools[].function.{name,description,parameters}
        - Anthropic: tools[].{name,description,input_schema}
        - Gemini: tools[].functionDeclarations[].{name,description,parameters}
    """

    # Type mapping from ToolParameter types to provider-specific types
    OPENAI_TYPE_MAP = {
        "str": "string",
        "string": "string",
        "int": "integer",
        "integer": "integer",
        "float": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "list": "array",
        "array": "array",
        "dict": "object",
        "object": "object",
    }

    ANTHROPIC_TYPE_MAP = OPENAI_TYPE_MAP.copy()  # Same as OpenAI

    GEMINI_TYPE_MAP = {
        "str": "STRING",
        "string": "STRING",
        "int": "INTEGER",
        "integer": "INTEGER",
        "float": "NUMBER",
        "number": "NUMBER",
        "bool": "BOOLEAN",
        "boolean": "BOOLEAN",
        "list": "ARRAY",
        "array": "ARRAY",
        "dict": "OBJECT",
        "object": "OBJECT",
    }

    @classmethod
    def _build_parameter_schema(
        cls, tool: "Tool", type_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build parameter schema from tool's parameters.

        Args:
            tool: Tool instance with parameters attribute
            type_map: Type mapping dictionary for the target provider

        Returns:
            Parameter schema dictionary with properties and required fields
        """
        properties = {}
        required = []

        for param in tool.parameters:
            param_type = type_map.get(param.type.lower(), "string")
            prop = {
                "type": param_type,
                "description": param.description,
            }

            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        schema = {
            "type": type_map.get("object", "object"),
            "properties": properties,
        }

        if required:
            schema["required"] = required

        return schema

    @classmethod
    def to_openai_format(cls, tools: List["Tool"]) -> List[Dict[str, Any]]:
        """Convert tools to OpenAI function calling format.

        Args:
            tools: List of Tool instances

        Returns:
            List of OpenAI-formatted tool definitions

        Format:
            {
                "type": "function",
                "function": {
                    "name": "tool_id",
                    "description": "tool description",
                    "parameters": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            }
        """
        result = []
        for tool in tools:
            schema = cls._build_parameter_schema(tool, cls.OPENAI_TYPE_MAP)
            result.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.id,
                        "description": tool.description,
                        "parameters": schema,
                    },
                }
            )
        return result

    @classmethod
    def to_anthropic_format(cls, tools: List["Tool"]) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic tool use format.

        Args:
            tools: List of Tool instances

        Returns:
            List of Anthropic-formatted tool definitions

        Format:
            {
                "name": "tool_id",
                "description": "tool description",
                "input_schema": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        """
        result = []
        for tool in tools:
            schema = cls._build_parameter_schema(tool, cls.ANTHROPIC_TYPE_MAP)
            result.append(
                {
                    "name": tool.id,
                    "description": tool.description,
                    "input_schema": schema,
                }
            )
        return result

    @classmethod
    def to_gemini_format(cls, tools: List["Tool"]) -> List[Dict[str, Any]]:
        """Convert tools to Gemini function calling format.

        Args:
            tools: List of Tool instances

        Returns:
            List of Gemini-formatted tool definitions (wrapped in functionDeclarations)

        Format:
            {
                "functionDeclarations": [
                    {
                        "name": "tool_id",
                        "description": "tool description",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {...},
                            "required": [...]
                        }
                    }
                ]
            }
        """
        function_declarations = []
        for tool in tools:
            schema = cls._build_parameter_schema(tool, cls.GEMINI_TYPE_MAP)
            function_declarations.append(
                {
                    "name": tool.id,
                    "description": tool.description,
                    "parameters": schema,
                }
            )

        return [{"functionDeclarations": function_declarations}]


class FunctionCallHandler:
    """Parses function calls from different LLM provider responses.

    Supports:
        - OpenAI: choices[0].message.tool_calls
        - Anthropic: content[].type == "tool_use"
        - Gemini: candidates[0].content.parts[0].functionCall
    """

    @classmethod
    def is_function_call(cls, response: Dict[str, Any], provider: str) -> bool:
        """Check if a response contains a function call.

        Args:
            response: Raw API response dictionary
            provider: Provider name ("openai", "anthropic", "gemini")

        Returns:
            True if response contains a function call
        """
        provider_lower = provider.lower()

        if provider_lower == "openai":
            try:
                tool_calls = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("tool_calls")
                )
                return tool_calls is not None and len(tool_calls) > 0
            except (IndexError, AttributeError):
                return False

        elif provider_lower == "anthropic":
            content = response.get("content", [])
            return any(block.get("type") == "tool_use" for block in content)

        elif provider_lower == "gemini":
            try:
                parts = (
                    response.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                return any("functionCall" in part for part in parts)
            except (IndexError, AttributeError):
                return False

        return False

    @classmethod
    def parse_openai_response(
        cls, response: Dict[str, Any]
    ) -> Optional[List[FunctionCall]]:
        """Parse function calls from OpenAI response.

        Args:
            response: OpenAI API response dictionary

        Returns:
            List of FunctionCall objects, or None if no function calls
        """
        try:
            tool_calls = (
                response.get("choices", [{}])[0].get("message", {}).get("tool_calls")
            )
            if not tool_calls:
                return None

            result = []
            for tc in tool_calls:
                func_data = tc.get("function", {})
                arguments_str = func_data.get("arguments", "{}")
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError:
                    arguments = {}

                result.append(
                    FunctionCall(
                        id=tc.get("id", ""),
                        name=func_data.get("name", ""),
                        arguments=arguments,
                    )
                )
            return result
        except (IndexError, AttributeError, TypeError):
            return None

    @classmethod
    def parse_anthropic_response(
        cls, response: Dict[str, Any]
    ) -> Optional[List[FunctionCall]]:
        """Parse function calls from Anthropic response.

        Args:
            response: Anthropic API response dictionary

        Returns:
            List of FunctionCall objects, or None if no function calls
        """
        content = response.get("content", [])
        tool_use_blocks = [
            block for block in content if block.get("type") == "tool_use"
        ]

        if not tool_use_blocks:
            return None

        result = []
        for block in tool_use_blocks:
            result.append(
                FunctionCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}),
                )
            )
        return result

    @classmethod
    def parse_gemini_response(
        cls, response: Dict[str, Any]
    ) -> Optional[List[FunctionCall]]:
        """Parse function calls from Gemini response.

        Args:
            response: Gemini API response dictionary

        Returns:
            List of FunctionCall objects, or None if no function calls
        """
        try:
            parts = (
                response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            )
            function_call_parts = [p for p in parts if "functionCall" in p]

            if not function_call_parts:
                return None

            result = []
            for part in function_call_parts:
                fc = part["functionCall"]
                result.append(
                    FunctionCall(
                        id=f"gemini_{fc.get('name', '')}",
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {}),
                    )
                )
            return result
        except (IndexError, AttributeError, TypeError, KeyError):
            return None


class UnexpectedToolCallHandler:
    """Handles Gemini's UNEXPECTED_TOOL_CALL finish reason.

    When Gemini attempts to call a function that wasn't declared in the
    tools parameter, it returns finishReason='UNEXPECTED_TOOL_CALL' with
    an error message containing the function name (prefixed with 'default:').

    This handler extracts the function call information so it can be
    routed to the appropriate handler.
    """

    # Regex pattern to extract function name from error message
    # Example: "Model tried to call an undeclared function: default:get_climate_related_entities"
    FUNCTION_NAME_PATTERN = re.compile(r"undeclared function:\s*(?:default:)?(\w+)")

    @classmethod
    def is_unexpected_tool_call(cls, response: Dict[str, Any]) -> bool:
        """Check if response is an UNEXPECTED_TOOL_CALL error.

        Args:
            response: Gemini API response dictionary

        Returns:
            True if finishReason is UNEXPECTED_TOOL_CALL
        """
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                return False
            finish_reason = candidates[0].get("finishReason", "")
            return finish_reason == "UNEXPECTED_TOOL_CALL"
        except (IndexError, AttributeError, TypeError):
            return False

    @classmethod
    def extract_function_call(cls, response: Dict[str, Any]) -> Optional[FunctionCall]:
        """Extract function call info from UNEXPECTED_TOOL_CALL response.

        Args:
            response: Gemini API response with UNEXPECTED_TOOL_CALL

        Returns:
            FunctionCall with extracted name, or None if extraction fails
        """
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                return None

            finish_message = candidates[0].get("finishMessage", "")
            match = cls.FUNCTION_NAME_PATTERN.search(finish_message)

            if not match:
                return None

            function_name = match.group(1)
            return FunctionCall(
                id=f"unexpected_{function_name}",
                name=function_name,
                arguments={},
            )
        except (IndexError, AttributeError, TypeError):
            return None
