"""Base tool infrastructure for Homeclaw.

This module provides the foundation for creating extensible tools that can be
dynamically registered and used by the AI agent. The architecture mirrors
OpenCode's tool system for consistency.

Example usage:
    from tools.base import Tool, ToolRegistry, ToolResult

    @ToolRegistry.register
    class MyTool(Tool):
        id = "my_tool"
        description = "Does something useful"

        async def execute(self, **params) -> ToolResult:
            # Implementation
            return ToolResult(output="Success", metadata={})
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, TypeVar

_LOGGER = logging.getLogger(__name__)


class ToolTier(Enum):
    """Loading tier for progressive tool loading.

    CORE tools are always included in function-calling schemas.
    ON_DEMAND tools have only short descriptions in the system prompt
    and must be activated via the ``load_tool`` meta-tool before use.
    """

    CORE = "core"
    ON_DEMAND = "on_demand"


class ToolCategory(Enum):
    """Categories for organizing tools."""

    WEB = "web"
    DATA = "data"
    HOME_ASSISTANT = "home_assistant"
    UTILITY = "utility"


@dataclass
class ToolParameter:
    """Definition of a tool parameter.

    Attributes:
        name: Parameter name
        type: Parameter type (str, int, float, bool, list, dict)
        description: Human-readable description
        required: Whether the parameter is required
        default: Default value if not provided
        enum: List of allowed values (optional)
    """

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None

    def validate(self, value: Any) -> bool:
        """Validate a value against this parameter definition."""
        if value is None:
            if self.required and self.default is None:
                return False
            return True

        if self.enum and value not in self.enum:
            return False

        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "list": list,
            "array": list,
            "dict": dict,
            "object": dict,
        }

        expected_type = type_map.get(self.type.lower())
        if expected_type and not isinstance(value, expected_type):
            return False

        return True


@dataclass
class ToolResult:
    """Result of a tool execution.

    Attributes:
        output: The main output content (string)
        metadata: Additional metadata about the execution
        title: Optional title for the result
        success: Whether the execution was successful
        error: Error message if execution failed
    """

    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "output": self.output,
            "metadata": self.metadata,
            "title": self.title,
            "success": self.success,
            "error": self.error,
        }


class Tool(ABC):
    """Abstract base class for all tools.

    Subclasses must define:
        - id: Unique tool identifier
        - description: Human-readable description for the AI
        - execute(): Async method to perform the tool's action

    Optional overrides:
        - parameters: List of ToolParameter definitions
        - category: ToolCategory for organization
        - enabled: Whether the tool is active
        - get_system_prompt(): Custom prompt text for the AI
    """

    # Class attributes to be defined by subclasses
    id: ClassVar[str]
    description: ClassVar[str]
    short_description: ClassVar[str] = ""
    parameters: ClassVar[List[ToolParameter]] = []
    category: ClassVar[ToolCategory] = ToolCategory.UTILITY
    tier: ClassVar[ToolTier] = ToolTier.ON_DEMAND
    enabled: ClassVar[bool] = True

    def __init__(self, hass: Any = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the tool.

        Args:
            hass: Home Assistant instance (optional)
            config: Tool configuration dictionary (optional)
        """
        self.hass = hass
        self.config = config or {}
        self._logger = logging.getLogger(f"{__name__}.{self.id}")

    @abstractmethod
    async def execute(self, **params: Any) -> ToolResult:
        """Execute the tool with the given parameters.

        Args:
            **params: Tool-specific parameters

        Returns:
            ToolResult with the execution output and metadata

        Raises:
            ToolExecutionError: If execution fails
        """
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against the tool's parameter definitions.

        Args:
            params: Dictionary of parameters to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for param_def in self.parameters:
            value = params.get(param_def.name)

            # Check required parameters
            if param_def.required and value is None and param_def.default is None:
                errors.append(f"Missing required parameter: {param_def.name}")
                continue

            # Use default if not provided
            if value is None:
                continue

            # Validate type and enum
            if not param_def.validate(value):
                if param_def.enum:
                    errors.append(
                        f"Invalid value for {param_def.name}: "
                        f"must be one of {param_def.enum}"
                    )
                else:
                    errors.append(
                        f"Invalid type for {param_def.name}: expected {param_def.type}"
                    )

        return errors

    def get_system_prompt(self) -> str:
        """Generate the system prompt text for this tool.

        Returns:
            Formatted string describing the tool for the AI
        """
        params_str = ""
        if self.parameters:
            param_parts = []
            for p in self.parameters:
                if p.required:
                    param_parts.append(p.name)
                else:
                    default_str = (
                        f"={repr(p.default)}" if p.default is not None else "?"
                    )
                    param_parts.append(f"{p.name}{default_str}")
            params_str = ", ".join(param_parts)

        return f"- {self.id}({params_str}): {self.description}"

    def get_parameter_docs(self) -> str:
        """Generate detailed parameter documentation.

        Returns:
            Formatted string with parameter details
        """
        if not self.parameters:
            return "No parameters."

        lines = []
        for p in self.parameters:
            req = "required" if p.required else "optional"
            default = f", default: {repr(p.default)}" if p.default is not None else ""
            enum = f", options: {p.enum}" if p.enum else ""
            lines.append(
                f"  - {p.name} ({p.type}, {req}{default}{enum}): {p.description}"
            )

        return "\n".join(lines)


class ToolExecutionError(Exception):
    """Exception raised when a tool execution fails."""

    def __init__(
        self, message: str, tool_id: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.tool_id = tool_id
        self.details = details or {}


T = TypeVar("T", bound=Tool)


class ToolRegistry:
    """Registry for managing and discovering tools.

    This registry provides:
        - Automatic tool registration via decorator
        - Tool discovery and instantiation
        - System prompt generation for all registered tools
        - Tool execution dispatching
    """

    _tools: ClassVar[Dict[str, Type[Tool]]] = {}
    _instances: ClassVar[Dict[str, Tool]] = {}

    @classmethod
    def register(cls, tool_class: Type[T]) -> Type[T]:
        """Register a tool class with the registry.

        Can be used as a decorator:
            @ToolRegistry.register
            class MyTool(Tool):
                ...

        Args:
            tool_class: The Tool subclass to register

        Returns:
            The same tool class (for decorator use)
        """
        if not hasattr(tool_class, "id"):
            raise ValueError(f"Tool class {tool_class.__name__} must define 'id'")

        tool_id = tool_class.id
        if tool_id in cls._tools:
            _LOGGER.warning(f"Overwriting existing tool registration: {tool_id}")

        cls._tools[tool_id] = tool_class
        _LOGGER.debug(f"Registered tool: {tool_id}")
        return tool_class

    @classmethod
    def get_tool_class(cls, tool_id: str) -> Optional[Type[Tool]]:
        """Get a tool class by its ID.

        Args:
            tool_id: The tool's unique identifier

        Returns:
            The Tool subclass, or None if not found
        """
        return cls._tools.get(tool_id)

    @classmethod
    def get_tool(
        cls,
        tool_id: str,
        hass: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tool]:
        """Get or create a tool instance by its ID.

        Args:
            tool_id: The tool's unique identifier
            hass: Home Assistant instance
            config: Tool configuration

        Returns:
            Tool instance, or None if not found
        """
        # Check for cached instance
        cache_key = f"{tool_id}_{id(hass)}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Create new instance
        tool_class = cls._tools.get(tool_id)
        if tool_class is None:
            return None

        instance = tool_class(hass=hass, config=config)
        cls._instances[cache_key] = instance
        return instance

    @classmethod
    def get_all_tools(
        cls,
        hass: Any = None,
        config: Optional[Dict[str, Any]] = None,
        enabled_only: bool = True,
    ) -> List[Tool]:
        """Get instances of all registered tools.

        Args:
            hass: Home Assistant instance
            config: Tool configuration
            enabled_only: Only return enabled tools

        Returns:
            List of Tool instances
        """
        tools = []
        for tool_id, tool_class in cls._tools.items():
            if enabled_only and not tool_class.enabled:
                continue
            tool = cls.get_tool(tool_id, hass=hass, config=config)
            if tool:
                tools.append(tool)
        return tools

    @classmethod
    def get_core_tools(
        cls,
        hass: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Tool]:
        """Get instances of CORE-tier tools only.

        These tools are always included in function-calling schemas.

        Args:
            hass: Home Assistant instance
            config: Tool configuration

        Returns:
            List of CORE Tool instances
        """
        tools = []
        for tool_id, tool_class in cls._tools.items():
            if not tool_class.enabled:
                continue
            if tool_class.tier != ToolTier.CORE:
                continue
            tool = cls.get_tool(tool_id, hass=hass, config=config)
            if tool:
                tools.append(tool)
        return tools

    @classmethod
    def list_on_demand_ids(cls) -> List[str]:
        """Return IDs of enabled ON_DEMAND tools.

        Provides a public API for listing available on-demand tools
        without exposing the internal ``_tools`` dict.

        Returns:
            Sorted list of tool IDs with tier ON_DEMAND and enabled=True.
        """
        return sorted(
            tid
            for tid, tc in cls._tools.items()
            if tc.tier == ToolTier.ON_DEMAND and tc.enabled
        )

    @classmethod
    def get_on_demand_descriptions(cls) -> str:
        """Generate short descriptions of ON_DEMAND tools for the system prompt.

        Returns a compact block listing each ON_DEMAND tool's id and
        short_description so the LLM knows what is available to load.

        Returns:
            Formatted string with on-demand tool descriptions.
        """
        lines: List[str] = []
        for tool_id, tool_class in cls._tools.items():
            if not tool_class.enabled:
                continue
            if tool_class.tier != ToolTier.ON_DEMAND:
                continue
            desc = tool_class.short_description or tool_class.description
            lines.append(f"- {tool_id}: {desc}")

        if not lines:
            return ""

        header = "Additional tools available (use load_tool to activate before use):"
        return header + "\n" + "\n".join(lines)

    @classmethod
    def get_system_prompt(
        cls,
        hass: Any = None,
        config: Optional[Dict[str, Any]] = None,
        enabled_only: bool = True,
    ) -> str:
        """Generate system prompt text for all registered tools.

        Args:
            hass: Home Assistant instance
            config: Tool configuration
            enabled_only: Only include enabled tools

        Returns:
            Formatted string with all tool descriptions
        """
        tools = cls.get_all_tools(hass=hass, config=config, enabled_only=enabled_only)

        if not tools:
            return ""

        lines = ["WEB TOOLS (for fetching web content and searching):"]
        for tool in tools:
            lines.append(tool.get_system_prompt())

        return "\n".join(lines)

    @classmethod
    async def execute_tool(
        cls,
        tool_id: str,
        params: Dict[str, Any],
        hass: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """Execute a tool by its ID with the given parameters.

        Args:
            tool_id: The tool's unique identifier
            params: Parameters to pass to the tool
            hass: Home Assistant instance
            config: Tool configuration

        Returns:
            ToolResult from the tool execution

        Raises:
            ToolExecutionError: If the tool is not found or execution fails
        """
        tool = cls.get_tool(tool_id, hass=hass, config=config)

        if tool is None:
            raise ToolExecutionError(
                f"Tool not found: {tool_id}",
                tool_id=tool_id,
            )

        # Separate internal context keys (prefixed with _) from tool params.
        # _user_id is injected by ToolExecutor for per-request context passing.
        context_keys = {k: v for k, v in params.items() if k.startswith("_")}
        public_params = {k: v for k, v in params.items() if not k.startswith("_")}

        # Validate only public parameters (context keys are internal)
        errors = tool.validate_parameters(public_params)
        if errors:
            raise ToolExecutionError(
                f"Invalid parameters: {'; '.join(errors)}",
                tool_id=tool_id,
                details={"validation_errors": errors},
            )

        # Execute the tool — pass both public params and context keys
        try:
            result = await tool.execute(**public_params, **context_keys)
            _LOGGER.debug(f"Tool {tool_id} executed successfully")
            return result
        except ToolExecutionError:
            raise
        except Exception as e:
            _LOGGER.exception(f"Tool {tool_id} execution failed: {e}")
            raise ToolExecutionError(
                str(e),
                tool_id=tool_id,
                details={"exception_type": type(e).__name__},
            )

    @classmethod
    def list_tools(cls, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """List all registered tools with their metadata.

        Args:
            enabled_only: Only list enabled tools

        Returns:
            List of dictionaries with tool information
        """
        result = []
        for tool_id, tool_class in cls._tools.items():
            if enabled_only and not tool_class.enabled:
                continue
            result.append(
                {
                    "id": tool_id,
                    "description": tool_class.description,
                    "category": tool_class.category.value,
                    "enabled": tool_class.enabled,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                            "default": p.default,
                            "enum": p.enum,
                        }
                        for p in tool_class.parameters
                    ],
                }
            )
        return result

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools and instances.

        Primarily used for testing.
        """
        cls._tools.clear()
        cls._instances.clear()
