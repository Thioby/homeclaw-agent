"""Non-streaming tool call loop and tool expansion helpers.

Provides ``expand_loaded_tools`` for dynamic ON_DEMAND tool activation
and ``run_tool_loop_nonstream`` for the multi-turn non-streaming tool
call loop.  Extracted from QueryProcessor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..function_calling import FunctionCall
from .context_builder import recompact_if_needed
from .tool_executor import ToolExecutor

if TYPE_CHECKING:
    from ..providers.registry import AIProvider

_LOGGER = logging.getLogger(__name__)


def expand_loaded_tools(
    function_calls: list[FunctionCall],
    effective_tools: list[dict[str, Any]] | None,
    hass: Any,
    denied_tools: frozenset[str] | None = None,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """Expand effective_tools when load_tool was called.

    Scans executed function calls for ``load_tool`` invocations and
    dynamically adds the requested tool schemas to ``effective_tools``
    so they are available in the next LLM iteration.

    Security: validates that the tool is ON_DEMAND, enabled, and not
    in the ``denied_tools`` set before adding its schema.

    Args:
        function_calls: List of FunctionCall objects just executed.
        effective_tools: Current tool schemas (OpenAI format) or None.
        hass: Home Assistant instance for tool instantiation.
        denied_tools: Optional frozenset of tool names blocked from use.
        config: Optional tool configuration (for API keys, etc.).

    Returns:
        Updated effective_tools list (may be the same reference if
        no load_tool calls were found).
    """
    if effective_tools is None:
        return None

    # If load_tool itself is denied, skip all expansion to prevent bypass
    if denied_tools and "load_tool" in denied_tools:
        _LOGGER.debug("load_tool is in denied_tools, skipping all expansion")
        return effective_tools

    from ..function_calling import ToolSchemaConverter
    from ..tools.base import ToolRegistry, ToolTier

    for fc in function_calls:
        if fc.name != "load_tool":
            continue

        tool_name = fc.arguments.get("tool_name", "")
        if not tool_name:
            continue

        # Check if already loaded
        already_loaded = any(
            t.get("function", {}).get("name") == tool_name for t in effective_tools
        )
        if already_loaded:
            _LOGGER.debug("Tool %s already in effective_tools, skipping", tool_name)
            continue

        # Respect denied_tools policy
        if denied_tools and tool_name in denied_tools:
            _LOGGER.warning(
                "load_tool: tool '%s' is in denied_tools, refusing to load", tool_name
            )
            continue

        # Validate tool class before instantiation
        tool_class = ToolRegistry.get_tool_class(tool_name)
        if tool_class is None:
            _LOGGER.warning("load_tool: tool %s not found in registry", tool_name)
            continue

        if not tool_class.enabled:
            _LOGGER.warning("load_tool: tool '%s' is disabled, skipping", tool_name)
            continue

        if tool_class.tier != ToolTier.ON_DEMAND:
            _LOGGER.debug(
                "load_tool: tool '%s' is tier %s (not ON_DEMAND), skipping",
                tool_name,
                tool_class.tier.value,
            )
            continue

        # Get the tool instance and convert to schema
        tool_instance = ToolRegistry.get_tool(tool_name, hass=hass, config=config)
        if tool_instance is None:
            _LOGGER.warning("load_tool: tool %s could not be instantiated", tool_name)
            continue

        new_schemas = ToolSchemaConverter.to_openai_format([tool_instance])
        effective_tools.extend(new_schemas)
        _LOGGER.info(
            "load_tool: dynamically added '%s' to effective_tools (%d total)",
            tool_name,
            len(effective_tools),
        )

    return effective_tools


async def run_tool_loop_nonstream(
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
) -> dict[str, Any]:
    """Execute the non-streaming multi-turn tool call loop.

    Iterates: call provider → detect tool calls → execute tools → repeat.
    Stops when the provider returns plain text or max iterations reached.

    Returns:
        Dict with success/response/messages or success=False/error.
    """
    current_iteration = 0
    call_history_hashes: dict[str, int] = {}

    while current_iteration < effective_max_iterations:
        provider_kwargs = build_provider_kwargs_fn(kwargs, effective_tools)
        response_text = await provider.get_response(built_messages, **provider_kwargs)

        function_calls = detect_function_call_fn(
            response_text, allowed_tool_names=allowed_names
        )

        if not function_calls:
            updated_messages = build_updated_messages_fn(
                built_messages, response_text, system_prompt=system_prompt
            )
            return {
                "success": True,
                "response": response_text,
                "messages": updated_messages,
            }

        _LOGGER.info("Detected function calls: %s", function_calls)
        built_messages.append({"role": "assistant", "content": response_text})

        async for _ in ToolExecutor.execute_tool_calls(
            function_calls,
            hass,
            built_messages,
            yield_mode="none",
            denied_tools=denied_tools,
            user_id=user_id,
            call_history_hashes=call_history_hashes,
        ):
            pass

        effective_tools = expand_loaded_tools(
            function_calls,
            effective_tools,
            hass,
            denied_tools=denied_tools,
            config=config,
        )
        built_messages = await recompact_if_needed(
            built_messages, context_window=context_window
        )
        current_iteration += 1

    # Max iterations reached — force a final response without tools
    _LOGGER.warning(
        "Max iterations (%d) reached. Forcing final text response (no tools).",
        effective_max_iterations,
    )
    provider_kwargs_final: dict[str, Any] = {**kwargs}
    provider_kwargs_final.pop("tools", None)

    final_text = await provider.get_response(built_messages, **provider_kwargs_final)
    updated_messages = list(built_messages)
    if (
        system_prompt
        and updated_messages
        and updated_messages[0].get("role") == "system"
    ):
        updated_messages = updated_messages[1:]
    if final_text:
        updated_messages.append({"role": "assistant", "content": final_text})
    return {"success": True, "response": final_text or "", "messages": updated_messages}
