"""Tools package for Homeclaw.

This package provides an extensible tool system for the AI agent.
Tools are automatically registered when imported.

Usage:
    from .tools import ToolRegistry

    prompt = ToolRegistry.get_system_prompt()
    result = await ToolRegistry.execute_tool("web_fetch", {"url": "..."})
    tools = ToolRegistry.list_tools()

Adding New Tools:
    1. Create a new module in this package (e.g., tools/mytool.py)
    2. Subclass Tool and implement required methods
    3. Use @ToolRegistry.register decorator
    4. Import the module in this __init__.py
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
    shell_execute,
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
    "shell_execute",
    "subagent",
    "integration_manager",
    "channel_status",
    "load_tool",
]
