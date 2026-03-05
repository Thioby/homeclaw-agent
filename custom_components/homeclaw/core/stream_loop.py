"""Streaming tool call loop for AI agent interactions."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator

from ..function_calling import FunctionCall
from .context_builder import recompact_if_needed
from .events import (
    CompletionEvent,
    ErrorEvent,
    StatusEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from .tool_call_codec import build_assistant_tool_message, normalize_tool_calls
from .tool_executor import ToolExecutor
from .tool_loop import expand_loaded_tools

if TYPE_CHECKING:
    from ..providers.registry import AIProvider

_LOGGER = logging.getLogger(__name__)


async def run_tool_loop_stream(
    *,
    provider: AIProvider,
    built_messages: list[dict[str, Any]],
    effective_tools: list[dict[str, Any]] | None,
    effective_max_iterations: int,
    detect_function_call_fn: Any,
    allowed_names: set[str],
    hass: Any,
    denied_tools: frozenset[str] | None,
    config: dict[str, Any] | None,
    context_window: int,
    user_id: str,
    system_prompt: str | None,
    build_provider_kwargs_fn: Any,
    build_updated_messages_fn: Any,
    kwargs: dict[str, Any],
) -> AsyncGenerator[Any, None]:
    """Execute the streaming multi-turn tool call loop. Yields AgentEvent objects."""
    current_iteration = 0
    call_history_hashes: dict[str, int] = {}

    while current_iteration < effective_max_iterations:
        # Check if provider supports streaming
        if not hasattr(provider, "get_response_stream"):
            async for event in _nonstream_fallback_iteration(
                provider=provider,
                built_messages=built_messages,
                effective_tools=effective_tools,
                detect_function_call_fn=detect_function_call_fn,
                allowed_names=allowed_names,
                hass=hass,
                denied_tools=denied_tools,
                config=config,
                context_window=context_window,
                user_id=user_id,
                system_prompt=system_prompt,
                build_provider_kwargs_fn=build_provider_kwargs_fn,
                build_updated_messages_fn=build_updated_messages_fn,
                kwargs=kwargs,
                call_history_hashes=call_history_hashes,
            ):
                if isinstance(event, CompletionEvent):
                    yield event
                    return
                yield event
            current_iteration += 1
            continue

        # Provider supports streaming
        provider_kwargs = build_provider_kwargs_fn(kwargs, effective_tools)
        accumulated_text = ""
        accumulated_tool_calls: list[dict[str, Any]] = []

        _LOGGER.debug(
            "Streaming iteration %d: sending %d messages to provider",
            current_iteration,
            len(built_messages),
        )

        async for chunk in provider.get_response_stream(
            built_messages, **provider_kwargs
        ):
            if chunk.get("type") == "text":
                content = chunk.get("content", "")
                if not content:
                    continue
                accumulated_text += content
                yield TextEvent(content=content)
            elif chunk.get("type") == "tool_call":
                accumulated_tool_calls.append(chunk)
                _LOGGER.debug("Tool call detected in stream: %s", chunk.get("name"))
            elif chunk.get("type") == "error":
                yield ErrorEvent(message=chunk.get("message", "Unknown error"))
                return

        if accumulated_tool_calls:
            async for event in _handle_stream_tool_calls(
                accumulated_tool_calls=accumulated_tool_calls,
                built_messages=built_messages,
                hass=hass,
                denied_tools=denied_tools,
                user_id=user_id,
                call_history_hashes=call_history_hashes,
            ):
                yield event

            # Expand effective_tools if load_tool was called
            effective_tools = expand_loaded_tools(
                [
                    FunctionCall(
                        id=tc.get("id", tc.get("name", "")),
                        name=tc["name"],
                        arguments=tc.get("args", {}),
                    )
                    for tc in normalize_tool_calls(accumulated_tool_calls)
                ],
                effective_tools,
                hass,
                denied_tools=denied_tools,
                config=config,
            )
            built_messages = await recompact_if_needed(
                built_messages, context_window=context_window
            )

            current_iteration += 1
            _LOGGER.info(
                "Tool execution complete, starting iteration %d/%d. Text accumulated so far: %d chars",
                current_iteration,
                effective_max_iterations,
                len(accumulated_text),
            )
            continue

        # No function calls, complete
        _LOGGER.info(
            "Stream complete (iteration %d). Total accumulated text: %d chars",
            current_iteration,
            len(accumulated_text),
        )
        updated_messages = build_updated_messages_fn(
            built_messages, accumulated_text, system_prompt=system_prompt
        )
        yield CompletionEvent(messages=updated_messages)
        return

    # Max iterations reached
    _LOGGER.warning(
        "Max iterations (%d) reached. Forcing final text response (no tools).",
        effective_max_iterations,
    )
    provider_kwargs_final = {**kwargs}
    provider_kwargs_final.pop("tools", None)

    if hasattr(provider, "get_response_stream"):
        async for chunk in provider.get_response_stream(
            built_messages, **provider_kwargs_final
        ):
            if chunk.get("type") == "text":
                yield TextEvent(content=chunk.get("content", ""))
    else:
        final_text = await provider.get_response(
            built_messages, **provider_kwargs_final
        )
        if final_text:
            yield TextEvent(content=final_text)

    yield CompletionEvent(messages=list(built_messages))


async def _nonstream_fallback_iteration(
    *,
    provider: AIProvider,
    built_messages: list[dict[str, Any]],
    effective_tools: list[dict[str, Any]] | None,
    detect_function_call_fn: Any,
    allowed_names: set[str],
    hass: Any,
    denied_tools: frozenset[str] | None,
    config: dict[str, Any] | None,
    context_window: int,
    user_id: str,
    system_prompt: str | None,
    build_provider_kwargs_fn: Any,
    build_updated_messages_fn: Any,
    kwargs: dict[str, Any],
    call_history_hashes: dict[str, int],
) -> AsyncGenerator[Any, None]:
    """Single non-streaming fallback iteration within the streaming loop."""
    _LOGGER.debug("Provider doesn't support streaming, using fallback")
    provider_kwargs = build_provider_kwargs_fn(kwargs, effective_tools)
    response_text = await provider.get_response(built_messages, **provider_kwargs)

    function_calls = detect_function_call_fn(
        response_text, allowed_tool_names=allowed_names
    )

    if function_calls:
        try:
            parsed = json.loads(response_text)
            prefixed_text = parsed.get("text", "") if isinstance(parsed, dict) else ""
        except (json.JSONDecodeError, ValueError):
            prefixed_text = ""
        if prefixed_text:
            yield TextEvent(content=prefixed_text)
    else:
        yield TextEvent(content=response_text)

    if not function_calls:
        updated_messages = build_updated_messages_fn(
            built_messages, response_text, system_prompt=system_prompt
        )
        yield CompletionEvent(messages=updated_messages)
        return

    built_messages.append({"role": "assistant", "content": response_text})

    async for tool_event in ToolExecutor.execute_tool_calls(
        function_calls,
        hass,
        built_messages,
        yield_mode="result",
        denied_tools=denied_tools,
        user_id=user_id,
        call_history_hashes=call_history_hashes,
    ):
        if tool_event.get("type") == "tool_call":
            yield ToolCallEvent(
                tool_name=tool_event["name"],
                tool_args=tool_event.get("args", {}),
                tool_call_id=tool_event.get("id", "unknown"),
            )
        elif tool_event.get("type") == "tool_result":
            yield ToolResultEvent(
                tool_name=tool_event["name"],
                tool_result=tool_event["result"],
                tool_call_id=tool_event.get("id", "unknown"),
            )

    # Expand effective_tools if load_tool was called (parity with streaming path)
    expand_loaded_tools(
        function_calls,
        effective_tools,
        hass,
        denied_tools=denied_tools,
        config=config,
    )
    # Recompact messages after tool results
    built_messages[:] = await recompact_if_needed(
        built_messages, context_window=context_window
    )


async def _handle_stream_tool_calls(
    *,
    accumulated_tool_calls: list[dict[str, Any]],
    built_messages: list[dict[str, Any]],
    hass: Any,
    denied_tools: frozenset[str] | None,
    user_id: str,
    call_history_hashes: dict[str, int],
) -> AsyncGenerator[Any, None]:
    """Handle tool calls accumulated during a streaming iteration."""
    _LOGGER.info("Processing %d tool call(s) from stream", len(accumulated_tool_calls))

    tool_names = ", ".join(tc.get("name", "unknown") for tc in accumulated_tool_calls)
    yield StatusEvent(message=f"Calling tools: {tool_names}...")

    normalized_tool_calls = normalize_tool_calls(accumulated_tool_calls)

    function_calls = [
        FunctionCall(
            id=tc.get("id") or tc.get("name", "unknown"),
            name=tc["name"],
            arguments=tc.get("args", {}),
        )
        for tc in normalized_tool_calls
    ]

    for i, fc in enumerate(function_calls):
        raw_fc = None
        if i < len(accumulated_tool_calls):
            raw_fc = accumulated_tool_calls[i].get("_raw_function_call")
        yield ToolCallEvent(
            tool_name=fc.name,
            tool_args=fc.arguments,
            tool_call_id=fc.id,
            raw_function_call=raw_fc,
        )

    # Append assistant's message preserving Gemini thought_signature
    tool_call_obj = accumulated_tool_calls[0].get("_raw_function_call")
    if not tool_call_obj:
        assistant_tool_json = build_assistant_tool_message(normalized_tool_calls)
        built_messages.append({"role": "assistant", "content": assistant_tool_json})
    else:
        built_messages.append(
            {"role": "assistant", "content": json.dumps(tool_call_obj)}
        )

    async for tool_event in ToolExecutor.execute_tool_calls(
        function_calls,
        hass,
        built_messages,
        yield_mode="result",
        denied_tools=denied_tools,
        user_id=user_id,
        call_history_hashes=call_history_hashes,
    ):
        if tool_event.get("type") == "tool_result":
            yield ToolResultEvent(
                tool_name=tool_event["name"],
                tool_result=tool_event["result"],
                tool_call_id=tool_event.get("id", "unknown"),
            )
