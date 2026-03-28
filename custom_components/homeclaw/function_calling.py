"""Function calling module for native LLM tool integration.

This module provides converters and handlers for native function calling.

Classes:
    FunctionCall: Dataclass representing a parsed function call
    ToolSchemaConverter: Converts Tool metadata to OpenAI-compatible format
    FunctionCallHandler: Parses function calls from OpenAI-style responses
"""

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
    """Converts Tool metadata to OpenAI-compatible schema format.

    Provider-specific formats (Anthropic, Gemini) are handled by adapters.
    """

    # Type mapping from ToolParameter types to JSON Schema types
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


class FunctionCallHandler:
    """Parses function calls from OpenAI-style responses.

    Provider-specific response parsing (Anthropic, Gemini) is handled by
    adapters.  Only ``parse_openai_response`` is kept here because
    ``FunctionCallParser._try_openai()`` still relies on it.
    """

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
