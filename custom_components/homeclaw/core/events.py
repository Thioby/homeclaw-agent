"""Event definitions for the AI agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


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
    tool_args: dict[str, Any]
    tool_call_id: str
    raw_function_call: dict[str, Any] | None = None
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
class ReasoningEvent(AgentEvent):
    """Event emitted when a reasoning model streams chain-of-thought.

    Distinct from TextEvent because reasoning is ephemeral — shown live in the
    loading UI, never persisted to message history, never sent back to the LLM.
    """

    content: str
    type: Literal["reasoning"] = "reasoning"


@dataclass
class ReasoningDetailsEvent(AgentEvent):
    """Event carrying the opaque reasoning_details payload from the provider.

    Unlike ReasoningEvent (human-readable chain-of-thought, ephemeral), this
    is the structured payload that must be persisted on the assistant message
    and sent back verbatim on the next turn so the model can continue its
    chain-of-thought (OpenRouter multi-turn reasoning continuity).
    """

    details: list[dict[str, Any]]
    type: Literal["reasoning_details"] = "reasoning_details"


@dataclass
class ErrorEvent(AgentEvent):
    """Event emitted when a generic error occurs."""

    message: str
    type: Literal["error"] = "error"


@dataclass
class CompletionEvent(AgentEvent):
    """Event emitted when the interaction is complete."""

    messages: list[dict[str, Any]]
    type: Literal["complete"] = "complete"


@dataclass
class CompactionEvent(AgentEvent):
    """Event emitted when context compaction occurred."""

    messages: list[dict[str, Any]]
    type: Literal["compaction"] = "compaction"
