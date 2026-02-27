"""Event definitions for the AI agent."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union

@dataclass
class AgentEvent:
    """Base class for all agent events."""
    pass

@dataclass
class TextEvent(AgentEvent):
    """Event emitted when the agent generates text."""
    content: str
    type: Literal["text"] = "text"

@dataclass
class ToolCallEvent(AgentEvent):
    """Event emitted when the agent decides to call a tool."""
    tool_name: str
    tool_args: Dict[str, Any]
    tool_call_id: str
    raw_function_call: Optional[Dict[str, Any]] = None
    type: Literal["tool_call"] = "tool_call"

@dataclass
class ToolResultEvent(AgentEvent):
    """Event emitted when a tool execution completes."""
    tool_name: str
    tool_result: Any
    tool_call_id: str
    type: Literal["tool_result"] = "tool_result"

@dataclass
class ToolErrorEvent(AgentEvent):
    """Event emitted when a tool execution fails."""
    tool_name: str
    error_message: str
    tool_call_id: str
    type: Literal["tool_error"] = "tool_error"

@dataclass
class StatusEvent(AgentEvent):
    """Event emitted to update the status (e.g. 'Thinking...')."""
    message: str
    type: Literal["status"] = "status"

@dataclass
class ErrorEvent(AgentEvent):
    """Event emitted when a generic error occurs."""
    message: str
    type: Literal["error"] = "error"

@dataclass
class CompletionEvent(AgentEvent):
    """Event emitted when the interaction is complete."""
    messages: List[Dict[str, Any]]
    type: Literal["complete"] = "complete"
