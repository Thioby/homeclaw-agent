"""Base adapter interface for provider format conversion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProviderAdapter(ABC):
    """Transforms between canonical (OpenAI) format and provider-specific format.

    Each provider implements this to handle its API's quirks without
    polluting the core with format-specific logic.
    """

    @abstractmethod
    def transform_tools(self, openai_tools: list[dict[str, Any]]) -> Any:
        """Convert OpenAI tool schemas to provider format.

        Args:
            openai_tools: Tools in OpenAI format
                [{"type": "function", "function": {"name": ..., "parameters": ...}}]

        Returns:
            Tools in provider-specific format.
        """

    @abstractmethod
    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[Any, str | None]:
        """Convert canonical messages to provider format.

        Args:
            messages: Messages in OpenAI format with optional _images.

        Returns:
            Tuple of (provider_messages, system_content).
            system_content is extracted separately for providers that need it.
        """

    @abstractmethod
    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        """Extract canonical response from raw API response.

        Returns:
            {"type": "text", "content": str, "finish_reason": str}
            or {"type": "tool_calls", "tool_calls": [{"id": str, "name": str, "args": dict}], "text": str | None, "finish_reason": "tool_calls"}
        """

    @abstractmethod
    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: Any
    ) -> list[dict[str, Any]]:
        """Parse a single stream event into normalized chunks.

        Args:
            event_data: Parsed JSON from one stream event.
            tool_acc: ToolAccumulator instance for collecting partial tool calls.

        Returns:
            List of normalized chunks:
            - {"type": "text", "content": str}
            - {"type": "tool_call", "id": str, "name": str, "args": dict}
        """
