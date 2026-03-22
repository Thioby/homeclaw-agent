"""Gemini message/tool format converters and chunk processor.

Pure, stateless functions for converting between OpenAI and Gemini API formats.
"""

from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

SYNTHETIC_THOUGHT_SIGNATURE = "skip_thought_signature_validator"


def ensure_thought_signatures(contents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure function calls in the active loop have thoughtSignature.

    The Gemini API requires that functionCall parts in model turns have a
    thoughtSignature when using thinking models. If missing, a synthetic
    signature is injected to pass validation.

    Only applies to the "active loop" — content after the last user turn
    with a text part (not functionResponse-only turns).
    """
    # Find the start of the active loop
    active_loop_start = -1
    for i in range(len(contents) - 1, -1, -1):
        content = contents[i]
        if content.get("role") == "user" and any(
            "text" in p for p in content.get("parts", [])
        ):
            active_loop_start = i
            break

    if active_loop_start == -1:
        return contents

    new_contents: list[dict[str, Any]] | None = None
    for i in range(active_loop_start, len(contents)):
        content = contents[i]
        if content.get("role") != "model" or not content.get("parts"):
            continue
        for j, part in enumerate(content["parts"]):
            if "functionCall" not in part:
                continue
            if part.get("thoughtSignature"):
                break  # Already has signature — skip this turn
            # Need to mutate: lazily copy the list on first mutation
            if new_contents is None:
                new_contents = list(contents)
            new_parts = list(content["parts"])
            new_parts[j] = {
                **part,
                "thoughtSignature": SYNTHETIC_THOUGHT_SIGNATURE,
            }
            new_contents[i] = {**content, "parts": new_parts}
            break  # Only first functionCall per model turn

    return new_contents if new_contents is not None else contents


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
            # Check if this is a function call response (JSON with functionCall or canonical tool_calls)
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    from ..core.tool_call_codec import (
                        extract_tool_calls_from_assistant_content,
                    )

                    calls = extract_tool_calls_from_assistant_content(parsed)
                    if calls:
                        parts = []
                        # Preserve any prepended text if it exists
                        if (
                            "text" in parsed
                            and isinstance(parsed["text"], str)
                            and parsed["text"]
                        ):
                            parts.append({"text": parsed["text"]})
                        for call in calls:
                            fc_part: dict[str, Any] = {
                                "name": call.get("name", ""),
                                "args": call.get("args", {}),
                            }
                            # Place thoughtSignature at part level (sibling of functionCall)
                            thought_sig = call.get("thought_signature")
                            part_obj: dict[str, Any] = {"functionCall": fc_part}
                            if thought_sig is not None:
                                part_obj["thoughtSignature"] = thought_sig
                            parts.append(part_obj)
                        contents.append({"role": "model", "parts": parts})
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

    contents = ensure_thought_signatures(contents)
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
            # Skip thinking parts from Gemini thinking models
            if part.get("thought"):
                _LOGGER.debug("%sSkipping thought part", log_prefix)
                continue
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
                        "thought_signature": part.get("thoughtSignature"),
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
