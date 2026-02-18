"""Tools package for Homeclaw.

This package provides an extensible tool system for the AI agent.
Tools are automatically registered when imported.

Available Tools:
    - web_fetch: Fetch and parse content from URLs
    - web_search: Search the web using Exa AI
    - context7_resolve: Resolve library name to Context7 ID
    - context7_docs: Get documentation from Context7

Usage:
    from tools import ToolRegistry

    # Get system prompt for all tools
    prompt = ToolRegistry.get_system_prompt()

    # Execute a tool
    result = await ToolRegistry.execute_tool(
        "web_fetch",
        {"url": "https://example.com", "format": "markdown"}
    )

    # List available tools
    tools = ToolRegistry.list_tools()

Adding New Tools:
    1. Create a new module in this package (e.g., tools/mytool.py)
    2. Subclass Tool and implement required methods
    3. Use @ToolRegistry.register decorator
    4. Import the module in this __init__.py

    Example:
        from .base import Tool, ToolRegistry, ToolResult, ToolParameter

        @ToolRegistry.register
        class MyTool(Tool):
            id = "my_tool"
            description = "Does something useful"
            parameters = [
                ToolParameter(name="param1", type="string", description="...", required=True)
            ]

            async def execute(self, param1: str, **kwargs) -> ToolResult:
                # Implementation
                return ToolResult(output="Success", metadata={})
"""

# Import tools to trigger registration
# Each tool module uses @ToolRegistry.register decorator
from . import (
    channel_status,
    context7,
    ha_native,
    identity,
    integration_manager,
    load_tool,
    memory,
    scheduler,
    subagent,
    webfetch,
    websearch,
)

# Export base classes and utilities
from .base import (
    Tool,
    ToolCategory,
    ToolExecutionError,
    ToolParameter,
    ToolRegistry,
    ToolResult,
    ToolTier,
)

__all__ = [
    # Base classes
    "Tool",
    "ToolCategory",
    "ToolExecutionError",
    "ToolParameter",
    "ToolRegistry",
    "ToolResult",
    "ToolTier",
    # Tool modules (for direct access if needed)
    "webfetch",
    "websearch",
    "context7",
    "ha_native",
    "memory",
    "identity",
    "scheduler",
    "subagent",
    "integration_manager",
    "channel_status",
    "load_tool",
]


def get_tools_system_prompt(hass=None, config=None) -> str:
    """Get the system prompt text for all registered tools.

    This is a convenience function for integration with agent.py.

    Args:
        hass: Home Assistant instance (optional)
        config: Configuration dictionary (optional)

    Returns:
        Formatted string with tool descriptions for the system prompt
    """
    return ToolRegistry.get_system_prompt(hass=hass, config=config)


async def execute_tool(
    tool_id: str, params: dict, hass=None, config=None
) -> ToolResult:
    """Execute a tool by ID with the given parameters.

    This is a convenience function for integration with agent.py.

    Args:
        tool_id: The tool's unique identifier
        params: Parameters to pass to the tool
        hass: Home Assistant instance (optional)
        config: Configuration dictionary (optional)

    Returns:
        ToolResult from the tool execution
    """
    return await ToolRegistry.execute_tool(tool_id, params, hass=hass, config=config)


def list_tools(enabled_only: bool = True) -> list:
    """List all registered tools with their metadata.

    Args:
        enabled_only: Only list enabled tools

    Returns:
        List of tool information dictionaries
    """
    return ToolRegistry.list_tools(enabled_only=enabled_only)
