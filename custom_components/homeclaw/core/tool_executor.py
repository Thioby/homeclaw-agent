"""Tool execution handler for AI agent.

This module handles tool/function call execution during AI conversations.
Supports both streaming and non-streaming modes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, cast

from ..function_calling import FunctionCall
from ..tools.base import ToolRegistry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Global safety cap for tool results injected into LLM context.
# If a single tool result exceeds this, it gets truncated with a warning.
# Individual tools should paginate to stay well under this; this is a last resort.
MAX_TOOL_RESULT_CHARS = 30_000

APPROVAL_TIMEOUT_SECONDS = 600


class ToolExecutor:
    """Handles tool execution for AI conversations.

    This class provides a unified interface for executing tools/function calls,
    whether in streaming or non-streaming mode.
    """

    @staticmethod
    async def execute_tool_calls(
        function_calls: list[FunctionCall],
        hass: Any,  # HomeAssistant or None from kwargs.get()
        messages: list[dict[str, Any]],
        yield_mode: str = "none",
        denied_tools: frozenset[str] | None = None,
        user_id: str = "",
        call_history_hashes: dict[str, int] | None = None,
        approval_enabled: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a list of tool calls and add results to messages.

        Args:
            function_calls: List of FunctionCall objects to execute.
            hass: Home Assistant instance for tool execution.
            messages: Message history list to append tool results to.
            yield_mode: How to yield updates:
                - "none": No yields (for non-streaming process())
                - "status": Yield status messages (for streaming with internal tool execution)
                - "result": Yield tool_result messages (for non-streaming fallback in process_stream)
            denied_tools: Optional frozenset of tool IDs that are blocked from execution.
                If a function call matches, a rejection error is returned instead of executing.
            user_id: User ID for the current request. Passed to tools as
                ``_user_id`` so they can scope per-user actions (memory, identity)
                without relying on a shared global.
            call_history_hashes: Optional dictionary to track repeated tool calls 
                (hash -> count) and break infinite loops.

        Yields:
            Dict with type="status" or type="tool_result" depending on yield_mode.
        """
        import hashlib

        for fc in function_calls:
            # Circuit Breaker: prevent repeated identical tool calls
            if call_history_hashes is not None:
                normalized_args = {
                    k: v.strip() if isinstance(v, str) else v
                    for k, v in sorted(fc.arguments.items())
                }
                args_str = json.dumps(normalized_args, sort_keys=True)
                tc_hash = hashlib.md5(f"{fc.name}:{args_str}".encode()).hexdigest()
                call_history_hashes[tc_hash] = call_history_hashes.get(tc_hash, 0) + 1
                count = call_history_hashes[tc_hash]

                if count >= 2:
                    _LOGGER.error("Circuit breaker triggered for tool '%s' (called %d times with identical args)", fc.name, count)
                    error_msg = json.dumps({
                        "error": f"Circuit breaker activated: You called this tool with identical arguments {count} times in a row. Stop repeating yourself and try a different approach or inform the user."
                    })
                    messages.append({
                        "role": "function",
                        "name": fc.name,
                        "tool_use_id": fc.id,
                        "content": error_msg,
                    })
                    if yield_mode == "status":
                        yield {
                            "type": "status",
                            "message": f"✗ Circuit breaker: {fc.name} repeated too many times",
                        }
                    elif yield_mode == "result":
                        yield {
                            "type": "tool_result",
                            "name": fc.name,
                            "result": error_msg,
                            "id": fc.id,
                        }
                    continue

            # Enforce tool restrictions
            if denied_tools and fc.name in denied_tools:
                _LOGGER.warning(
                    "Tool '%s' blocked by denied_tools restriction", fc.name
                )
                error_msg = json.dumps(
                    {
                        "error": f"Tool '{fc.name}' is not available in this context.",
                        "tool": fc.name,
                    }
                )
                messages.append(
                    {
                        "role": "function",
                        "name": fc.name,
                        "tool_use_id": fc.id,
                        "content": error_msg,
                    }
                )
                if yield_mode == "status":
                    yield {
                        "type": "status",
                        "message": f"Tool {fc.name} blocked (restricted context)",
                    }
                elif yield_mode == "result":
                    yield {
                        "type": "tool_result",
                        "name": fc.name,
                        "result": error_msg,
                        "id": fc.id,
                    }
                continue

            validation_error = ToolExecutor._build_validation_error(fc, hass)
            if validation_error is not None:
                _LOGGER.warning(
                    "Tool call validation failed before execution: %s args=%s",
                    fc.name,
                    fc.arguments,
                )
                error_msg = json.dumps(validation_error)
                messages.append(
                    {
                        "role": "function",
                        "name": fc.name,
                        "tool_use_id": fc.id,
                        "content": error_msg,
                    }
                )
                if yield_mode == "status":
                    yield {
                        "type": "status",
                        "message": f"✗ {fc.name} invalid arguments",
                    }
                elif yield_mode == "result":
                    yield {
                        "type": "tool_result",
                        "name": fc.name,
                        "result": error_msg,
                        "id": fc.id,
                    }
                continue

            try:
                _LOGGER.debug("Executing tool: %s with args: %s", fc.name, fc.arguments)

                if yield_mode == "status":
                    yield {
                        "type": "status",
                        "message": f"Executing {fc.name}...",
                    }
                elif yield_mode == "result":
                    yield {
                        "type": "tool_call",
                        "name": fc.name,
                        "args": fc.arguments,
                        "id": fc.id,
                    }

                # Execute the tool — inject _user_id into params so tools
                # can scope per-user actions without a shared global.
                exec_params = dict(fc.arguments)
                if user_id:
                    exec_params["_user_id"] = user_id

                tool_class = (
                    ToolRegistry.get_tool_class(fc.name) if approval_enabled else None
                )
                if tool_class is not None and getattr(
                    tool_class, "requires_confirmation", False
                ):
                    from .pending_actions import discard_approval, register_approval

                    has_dry_run = any(
                        getattr(p, "name", None) == "dry_run"
                        for p in getattr(tool_class, "parameters", [])
                    )
                    preview = await ToolExecutor._build_confirmation_preview(
                        fc.name, exec_params, hass, has_dry_run
                    )
                    approval_future = register_approval(fc.id)
                    yield {
                        "type": "approval_request",
                        "name": fc.name,
                        "args": fc.arguments,
                        "id": fc.id,
                        "preview": preview,
                    }
                    try:
                        approved = await asyncio.wait_for(
                            approval_future, timeout=APPROVAL_TIMEOUT_SECONDS
                        )
                    except asyncio.TimeoutError:
                        approved = False
                    finally:
                        discard_approval(fc.id)

                    if not approved:
                        rejection = json.dumps(
                            {
                                "status": "cancelled_by_user",
                                "rejected": True,
                                "message": (
                                    "The user reviewed this action and chose to "
                                    "CANCEL it — nothing was applied. This is a "
                                    "deliberate user choice, NOT an error or "
                                    "failure. Do not retry the same action and do "
                                    "not apologize for a failure. Briefly confirm "
                                    "you cancelled it and, if useful, ask what "
                                    "they would like to change."
                                ),
                            }
                        )
                        messages.append(
                            {
                                "role": "function",
                                "name": fc.name,
                                "tool_use_id": fc.id,
                                "content": rejection,
                            }
                        )
                        if yield_mode == "status":
                            yield {
                                "type": "status",
                                "message": f"✗ {fc.name} rejected by user",
                            }
                        elif yield_mode == "result":
                            yield {
                                "type": "tool_result",
                                "name": fc.name,
                                "result": rejection,
                                "id": fc.id,
                            }
                        continue

                    if has_dry_run:
                        exec_params["dry_run"] = False

                result = await ToolRegistry.execute_tool(
                    tool_id=fc.name, params=exec_params, hass=hass
                )
                result_str = json.dumps(result.to_dict())

                # Safety cap: truncate oversized tool results to prevent context overflow
                if len(result_str) > MAX_TOOL_RESULT_CHARS:
                    _LOGGER.warning(
                        "Tool %s result truncated: %d -> %d chars",
                        fc.name,
                        len(result_str),
                        MAX_TOOL_RESULT_CHARS,
                    )
                    result_str = (
                        result_str[:MAX_TOOL_RESULT_CHARS]
                        + f"\n... [TRUNCATED — result was {len(result_str)} chars. "
                        + "Use pagination (limit/offset) or get_entity_state for details.]"
                    )

                _LOGGER.debug("Tool %s executed successfully", fc.name)

                # Add result to messages list
                messages.append(
                    {
                        "role": "function",
                        "name": fc.name,
                        "tool_use_id": fc.id,
                        "content": result_str,
                    }
                )

                if yield_mode == "status":
                    yield {
                        "type": "status",
                        "message": f"Tool {fc.name} completed",
                    }
                elif yield_mode == "result":
                    yield {
                        "type": "tool_result",
                        "name": fc.name,
                        "result": result_str,
                        "id": fc.id,
                    }

            except Exception as e:
                _LOGGER.error("Tool execution failed: %s - %s", fc.name, e)
                error_msg = json.dumps({"error": str(e), "tool": fc.name})

                # Add error to messages list
                messages.append(
                    {
                        "role": "function",
                        "name": fc.name,
                        "tool_use_id": fc.id,
                        "content": error_msg,
                    }
                )

                if yield_mode == "status":
                    yield {
                        "type": "status",
                        "message": f"✗ {fc.name} failed: {str(e)}",
                    }
                elif yield_mode == "result":
                    yield {
                        "type": "tool_result",
                        "name": fc.name,
                        "result": error_msg,
                        "id": fc.id,
                    }

    @staticmethod
    async def _build_confirmation_preview(
        tool_name: str,
        exec_params: dict[str, Any],
        hass: Any,
        has_dry_run: bool,
    ) -> dict[str, Any]:
        """Build the preview shown in the approval card.

        Tools with a ``dry_run`` parameter render a real preview; everything
        else falls back to showing the arguments that would be applied.
        """
        visible_args = {k: v for k, v in exec_params.items() if k != "_user_id"}
        if not has_dry_run:
            return {"args": visible_args}
        preview_params = dict(exec_params)
        preview_params["dry_run"] = True
        try:
            preview_result = await ToolRegistry.execute_tool(
                tool_id=tool_name, params=preview_params, hass=hass
            )
            try:
                return json.loads(preview_result.output)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return {"output": getattr(preview_result, "output", "")}
        except Exception as exc:
            _LOGGER.warning(
                "Failed to build approval preview for %s: %s", tool_name, exc
            )
            return {"args": visible_args}

    @staticmethod
    def _build_validation_error(
        function_call: FunctionCall,
        hass: Any,
    ) -> dict[str, Any] | None:
        """Build a structured validation error before tool execution.

        Returns None if the call is valid (or tool metadata is unavailable).
        """
        tool = ToolRegistry.get_tool(function_call.name, hass=hass)
        if tool is None:
            return None

        validation_errors = tool.validate_parameters(function_call.arguments)
        if not validation_errors:
            return None

        required_parameters = [
            p.name for p in tool.parameters if p.required and p.default is None
        ]
        return {
            "error": "Invalid tool arguments",
            "tool": function_call.name,
            "validation_errors": validation_errors,
            "required_parameters": required_parameters,
            "received_args": function_call.arguments,
            "hint": "Retry this tool call with all required parameters.",
        }

    @staticmethod
    def convert_tool_calls_to_function_calls(
        tool_calls: list[dict[str, Any]],
    ) -> list[FunctionCall]:
        """Convert tool call dicts to FunctionCall objects.

        Args:
            tool_calls: List of dicts with 'name' and 'args' keys.

        Returns:
            List of FunctionCall objects.
        """
        return [
            FunctionCall(
                id=tc.get("id") or tc.get("name", "unknown"),
                name=tc["name"],
                arguments=tc.get("args", {}),
            )
            for tc in tool_calls
        ]
