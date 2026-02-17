"""Load tool meta-tool for progressive tool loading.

This meta-tool allows the LLM to dynamically activate ON_DEMAND tools
during a conversation. Instead of eagerly loading all tool schemas into
every request (~5K tokens), only CORE tools are loaded by default.
The LLM sees short descriptions of ON_DEMAND tools in the system prompt
and calls ``load_tool`` to activate the ones it needs.

The actual schema injection happens in QueryProcessor, which detects
``load_tool`` results and extends ``effective_tools`` for subsequent
iterations.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, List

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier

_LOGGER = logging.getLogger(__name__)


@ToolRegistry.register
class LoadToolTool(Tool):
    """Activate an on-demand tool for use in the current conversation.

    Call this tool when you need a capability listed in the system prompt
    under 'Additional tools available'. After activation, the tool becomes
    available for function calling in subsequent turns.
    """

    id: ClassVar[str] = "load_tool"
    description: ClassVar[str] = (
        "Activate an on-demand tool so it becomes available for function calling. "
        "Use this when you need a tool listed under 'Additional tools available'. "
        "After calling load_tool, the activated tool can be used in the next step."
    )
    category: ClassVar[ToolCategory] = ToolCategory.UTILITY
    tier: ClassVar[ToolTier] = ToolTier.CORE
    parameters: ClassVar[List[ToolParameter]] = [
        ToolParameter(
            name="tool_name",
            type="string",
            description=(
                "The ID of the tool to activate "
                "(e.g. 'web_search', 'web_fetch', 'context7_resolve')"
            ),
            required=True,
        ),
    ]

    async def execute(self, **params: Any) -> ToolResult:
        """Activate an on-demand tool.

        Args:
            **params: Must include ``tool_name`` (str).

        Returns:
            ToolResult confirming activation with the tool's description.
        """
        tool_name = params.get("tool_name", "")
        if not tool_name:
            return ToolResult(
                output="Error: tool_name is required",
                success=False,
                error="missing_tool_name",
            )

        # Check if tool exists in registry
        tool_class = ToolRegistry.get_tool_class(tool_name)
        if tool_class is None:
            available = ToolRegistry.list_on_demand_ids()
            return ToolResult(
                output=(
                    f"Error: Tool '{tool_name}' not found. "
                    f"Available on-demand tools: {', '.join(available)}"
                ),
                success=False,
                error="tool_not_found",
            )

        # Check if it's an ON_DEMAND tool (CORE tools are already loaded)
        if tool_class.tier == ToolTier.CORE:
            return ToolResult(
                output=(
                    f"Tool '{tool_name}' is already available (CORE tier). "
                    "You can use it directly without loading."
                ),
                success=True,
                metadata={"tool_name": tool_name, "already_loaded": True},
            )

        # Refuse to load disabled tools
        if not tool_class.enabled:
            return ToolResult(
                output=f"Error: Tool '{tool_name}' is currently disabled.",
                success=False,
                error="tool_disabled",
            )

        # Return confirmation — QueryProcessor will handle the actual
        # schema injection into effective_tools
        _LOGGER.info("load_tool activated: %s", tool_name)
        return ToolResult(
            output=(
                f"Tool '{tool_name}' activated. "
                f"Description: {tool_class.description}. "
                "You can now use it in your next function call."
            ),
            success=True,
            metadata={"tool_name": tool_name, "loaded": True},
        )
