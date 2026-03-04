"""Function call detection and parsing from raw AI response text.

Extracts provider-specific function call formats (OpenAI, Gemini, Anthropic)
from raw text responses using a strategy-per-provider approach.

Separated from QueryProcessor to isolate format-specific parsing logic
from orchestration logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..function_calling import FunctionCall, FunctionCallHandler

_LOGGER = logging.getLogger(__name__)


class FunctionCallParser:
    """Parses function calls from raw AI response text.

    Detects and extracts function calls from various provider formats:
    - OpenAI: ``{"tool_calls": [...]}``
    - Gemini: ``{"functionCall": {"name": ..., "args": ...}}``
    - Anthropic: ``{"tool_use": {"id": ..., "name": ..., "input": ...}}``
    - Simple/custom: ``{"function": ..., "parameters": ...}``

    Uses ResponseParser for initial JSON extraction, then applies
    format-specific strategies in priority order.
    """

    def __init__(self, response_parser: Any) -> None:
        """Initialize the function call parser.

        Args:
            response_parser: ResponseParser instance for JSON extraction.
        """
        self._response_parser = response_parser

    def detect(
        self,
        response_text: str,
        allowed_tool_names: set[str] | None = None,
    ) -> list[FunctionCall] | None:
        """Detect and parse function calls from response text.

        Tries multiple provider formats in order:
        1. OpenAI tool_calls
        2. Gemini functionCall
        3. Anthropic tool_use
        4. Simple/custom format
        5. Raw tool_calls list

        Args:
            response_text: The text response from the AI provider.
            allowed_tool_names: Optional set of valid tool names. When provided,
                calls referencing unknown tools are rejected.

        Returns:
            List of FunctionCall objects if found, None otherwise.
        """
        parsed_result = self._response_parser.parse(response_text)

        if parsed_result["type"] == "text":
            return None

        content = parsed_result["content"]
        if not isinstance(content, dict):
            return None

        function_calls = (
            self._try_openai(content)
            or self._try_gemini(content)
            or self._try_anthropic(content)
            or self._try_simple(content)
            or self._try_tool_calls_list(content)
        )

        if not function_calls:
            return None

        if allowed_tool_names is None:
            return function_calls

        validated = []
        for fc in function_calls:
            if fc.name in allowed_tool_names:
                validated.append(fc)
            else:
                _LOGGER.warning("Rejected hallucinated tool call: %s", fc.name)
        return validated if validated else None

    # ------------------------------------------------------------------
    # Provider-specific strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _try_openai(content: dict[str, Any]) -> list[FunctionCall] | None:
        """Try OpenAI tool_calls format.

        Args:
            content: Parsed JSON dict.

        Returns:
            List of FunctionCall if detected, None otherwise.
        """
        if "tool_calls" not in content:
            return None

        return FunctionCallHandler.parse_openai_response(
            {"choices": [{"message": {"tool_calls": content["tool_calls"]}}]}
        )

    @staticmethod
    def _try_gemini(content: dict[str, Any]) -> list[FunctionCall] | None:
        """Try Gemini functionCall format.

        Args:
            content: Parsed JSON dict.

        Returns:
            List of FunctionCall if detected, None otherwise.
        """
        if "functionCall" not in content:
            return None

        fc = content["functionCall"]
        return [
            FunctionCall(
                id=f"gemini_{fc.get('name', '')}",
                name=fc.get("name", ""),
                arguments=fc.get("args", {}),
            )
        ]

    @staticmethod
    def _try_anthropic(content: dict[str, Any]) -> list[FunctionCall] | None:
        """Try Anthropic tool_use format.

        Supports ``additional_tool_calls`` for parallel tool use.

        Args:
            content: Parsed JSON dict.

        Returns:
            List of FunctionCall if detected, None otherwise.
        """
        if "tool_use" not in content:
            return None

        tool_use = content["tool_use"]
        calls = [
            FunctionCall(
                id=tool_use.get("id", ""),
                name=tool_use.get("name", ""),
                arguments=tool_use.get("input", {}),
            )
        ]
        for extra in content.get("additional_tool_calls", []):
            calls.append(
                FunctionCall(
                    id=extra.get("id", ""),
                    name=extra.get("name", ""),
                    arguments=extra.get("input", {}),
                )
            )
        return calls

    @staticmethod
    def _try_simple(content: dict[str, Any]) -> list[FunctionCall] | None:
        """Try simple/custom function call format.

        Matches patterns like:
        - ``{"function": "name", "parameters": {...}}``
        - ``{"name": "name", "arguments": {...}}``
        - ``{"tool": "name", "args": {...}}``

        Args:
            content: Parsed JSON dict.

        Returns:
            List of FunctionCall if detected, None otherwise.
        """
        name = content.get("function") or content.get("name") or content.get("tool")
        args = (
            content.get("parameters") or content.get("arguments") or content.get("args")
        )

        if name and isinstance(name, str) and isinstance(args, dict):
            return [FunctionCall(id=name, name=name, arguments=args)]

        return None

    @staticmethod
    def _try_tool_calls_list(content: dict[str, Any]) -> list[FunctionCall] | None:
        """Try raw tool_calls list format (OpenAI-style inside a list).

        Args:
            content: Parsed JSON dict.

        Returns:
            List of FunctionCall if detected, None otherwise.
        """
        tool_calls_list = content.get("tool_calls")
        if not isinstance(tool_calls_list, list):
            return None

        result = []
        for tc in tool_calls_list:
            func = tc.get("function", {})
            if func:
                arguments = func.get("arguments", {})
                if not isinstance(arguments, dict):
                    try:
                        arguments = json.loads(arguments)
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}
                result.append(
                    FunctionCall(
                        id=tc.get("id", ""),
                        name=func.get("name", ""),
                        arguments=arguments,
                    )
                )
        return result if result else None
