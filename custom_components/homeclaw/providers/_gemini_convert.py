"""Gemini message/tool format converters and chunk processor.

Pure, stateless functions for converting between OpenAI and Gemini API formats.
"""

from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def convert_messages(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    """Convert OpenAI-style messages to Gemini format.

    Handles:
    - System messages -> systemInstruction
    - User messages -> user role
    - Assistant messages -> model role (including function calls)
    - Function results -> user role with functionResponse

    Returns:
        Tuple of (contents list, system instruction text or None).
    """
    contents = []
    system_instruction = None

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        if role == "system":
            if system_instruction is None:
                system_instruction = content
            else:
                system_instruction += "\n\n" + content
        elif role == "user" and content:
            parts: list[dict[str, Any]] = [{"text": content}]
            # Add inline image data for multimodal messages
            images = message.get("_images", [])
            for img in images:
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": img["mime_type"],
                            "data": img["data"],
                        }
                    }
                )
            contents.append({"role": "user", "parts": parts})
        elif role == "assistant" and content:
            # Check if this is a function call response (JSON with functionCall)
            try:
                parsed = json.loads(content)
                if "functionCall" in parsed:
                    # Already in Gemini format - use as is but remove any 'type' field
                    func_call = {k: v for k, v in parsed.items() if k != "type"}
                    contents.append({"role": "model", "parts": [func_call]})
                    continue
                elif "function_call" in parsed:
                    # OpenAI format - convert to Gemini format
                    openai_call = parsed["function_call"]
                    gemini_call = {
                        "functionCall": {
                            "name": openai_call.get("name", ""),
                            "args": openai_call.get("arguments", {}),
                        }
                    }
                    contents.append({"role": "model", "parts": [gemini_call]})
                    continue
            except (ValueError, TypeError):
                pass
            contents.append({"role": "model", "parts": [{"text": content}]})
        elif role == "function":
            # Tool result - Gemini uses functionResponse in user role
            func_name = message.get("name", "unknown")
            try:
                result_data = json.loads(content)
            except (ValueError, TypeError):
                result_data = {"result": content}
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": func_name,
                                "response": result_data,
                            }
                        }
                    ],
                }
            )

    return contents, system_instruction


def convert_tools(
    openai_tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert OpenAI tool format to Gemini functionDeclarations format."""
    if not openai_tools:
        return []

    function_declarations = []
    for tool in openai_tools:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            function_declarations.append(
                {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {}),
                }
            )

    return (
        [{"functionDeclarations": function_declarations}]
        if function_declarations
        else []
    )


def process_gemini_chunk(chunk: Any, label: str = "") -> list[dict[str, Any]]:
    """Process a parsed Gemini JSON chunk and extract text/tool_call results.

    Handles both single objects and arrays of objects from streamGenerateContent.
    Unwraps the Gemini response envelope (response -> candidates -> content -> parts).

    Args:
        chunk: Parsed JSON - either a dict or a list of dicts from Gemini API.
        label: Optional prefix for log messages (e.g. "[Final flush]").

    Returns:
        List of dicts with 'type' key ('text' or 'tool_call').
    """
    results: list[dict[str, Any]] = []

    # Normalize to list of items
    if isinstance(chunk, list):
        if not chunk:
            return results
        items = chunk
    else:
        items = [chunk]

    log_prefix = f"{label} " if label else ""

    for item in items:
        # Unwrap response envelope
        if "response" in item:
            item = item["response"]

        candidates = item.get("candidates", [])
        if not candidates:
            continue

        candidate = candidates[0]

        finish_reason = candidate.get("finishReason")
        if finish_reason:
            _LOGGER.info("%s📋 Gemini finishReason: %s", log_prefix, finish_reason)

        # Log usage metadata (typically on last chunk)
        usage = item.get("usageMetadata")
        if usage:
            _LOGGER.debug(
                "%s📊 Gemini usage: promptTokens=%s, candidateTokens=%s, totalTokens=%s",
                log_prefix,
                usage.get("promptTokenCount"),
                usage.get("candidatesTokenCount"),
                usage.get("totalTokenCount"),
            )

        content = candidate.get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            if "text" in part:
                text_content = part["text"]
                _LOGGER.debug(
                    "%s📝 Yielding text chunk: %s",
                    log_prefix,
                    text_content[:80],
                )
                results.append({"type": "text", "content": text_content})
            elif "functionCall" in part:
                func_call = part["functionCall"]
                _LOGGER.info(
                    "%s🔧 Yielding tool_call: %s",
                    log_prefix,
                    func_call.get("name"),
                )
                results.append(
                    {
                        "type": "tool_call",
                        "name": func_call.get("name", "unknown"),
                        "args": func_call.get("args", {}),
                        "thought_signature": func_call.get("thoughtSignature"),
                        "_raw_function_call": part,
                    }
                )
            else:
                _LOGGER.warning(
                    "%s❓ Unknown part type in chunk: %s",
                    log_prefix,
                    list(part.keys()),
                )

    return results
