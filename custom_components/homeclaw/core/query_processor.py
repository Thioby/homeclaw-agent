"""Query processor for AI agent interactions.

Orchestrates query sanitization, message building, and AI provider
coordination.  Delegates to ``context_builder``, ``tool_loop``, and
``stream_loop``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator

from ..function_calling import FunctionCall
from .context_builder import build_messages, recompact_if_needed, repair_tool_history
from .function_call_parser import FunctionCallParser
from .response_parser import ResponseParser
from .stream_loop import run_tool_loop_stream
from .token_estimator import DEFAULT_CONTEXT_WINDOW
from .tool_loop import expand_loaded_tools, run_tool_loop_nonstream

if TYPE_CHECKING:
    from ..providers.registry import AIProvider

_LOGGER = logging.getLogger(__name__)
EMPTY_QUERY_ERROR = "Query is empty or contains only whitespace"

INVISIBLE_CHARS = [
    "\ufeff",  # BOM (Byte Order Mark)
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u2060",  # Word joiner
]


class QueryProcessor:
    """Processes user queries for AI providers."""

    def __init__(
        self,
        provider: AIProvider,
        max_iterations: int = 20,
        max_query_length: int = 1000,
    ) -> None:
        """Initialize the query processor."""
        self.provider = provider
        self.max_iterations = max_iterations
        self.max_query_length = max_query_length
        self.response_parser = ResponseParser()
        self.function_call_parser = FunctionCallParser(self.response_parser)

    def _sanitize_query(self, query: str, max_length: int | None = None) -> str:
        """Sanitize a user query by removing invisible characters."""
        sanitized = query
        for char in INVISIBLE_CHARS:
            sanitized = sanitized.replace(char, "")
        sanitized = sanitized.strip()
        effective_max = max_length if max_length is not None else self.max_query_length
        if len(sanitized) > effective_max:
            sanitized = sanitized[:effective_max]
        return sanitized

    @staticmethod
    def _normalize_query_with_attachments(
        sanitized_query: str, attachments: list[Any] | None
    ) -> str:
        """Apply image-only fallback prompt when text is empty but attachments exist."""
        if not sanitized_query and attachments:
            return "Describe what you see in the attached image(s)."
        return sanitized_query

    @staticmethod
    def _extract_runtime_context(kwargs: dict[str, Any]) -> dict[str, Any]:
        """Pop shared runtime context keys consumed by QueryProcessor."""
        return {
            "rag_context": kwargs.pop("rag_context", None),
            "denied_tools": kwargs.pop("denied_tools", None),
            "config": kwargs.pop("config", None),
            "context_window": kwargs.pop("context_window", DEFAULT_CONTEXT_WINDOW),
            "memory_flush_fn": kwargs.pop("memory_flush_fn", None),
            "user_id": kwargs.get("user_id", ""),
            "session_id": kwargs.get("session_id", ""),
        }

    @staticmethod
    def _filter_denied_tools(
        tools: list[dict[str, Any]] | None,
        denied_tools: frozenset[str] | None,
        *,
        non_stream: bool = False,
    ) -> list[dict[str, Any]] | None:
        """Filter denied tools from the list passed to the LLM."""
        if not denied_tools or not tools:
            return tools
        effective_tools = [
            t for t in tools if t.get("function", {}).get("name") not in denied_tools
        ]
        filtered_count = len(tools) - len(effective_tools)
        if filtered_count:
            suffix = " (non-stream)" if non_stream else ""
            _LOGGER.debug(
                "Filtered %d denied tools from LLM tool list%s", filtered_count, suffix
            )
        return effective_tools

    @staticmethod
    def _build_provider_kwargs(
        kwargs: dict[str, Any], effective_tools: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """Build provider kwargs and attach effective tools when present."""
        provider_kwargs: dict[str, Any] = {**kwargs}
        if effective_tools is not None:
            provider_kwargs["tools"] = effective_tools
        return provider_kwargs

    @staticmethod
    def _build_updated_messages(
        built_messages: list[dict[str, Any]],
        response_text: str,
        system_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build returned messages list with assistant response appended."""
        updated_messages = list(built_messages)
        if (
            system_prompt
            and updated_messages
            and updated_messages[0].get("role") == "system"
        ):
            updated_messages = updated_messages[1:]
        updated_messages.append({"role": "assistant", "content": response_text})
        return updated_messages

    def _detect_function_call(
        self, response_text: str, allowed_tool_names: set[str] | None = None
    ) -> list[FunctionCall] | None:
        """Detect and parse function calls from response text."""
        return self.function_call_parser.detect(
            response_text, allowed_tool_names=allowed_tool_names
        )

    # --- Delegated methods (backward compatibility) ---

    async def _build_messages(
        self,
        query: str,
        history: list[dict[str, Any]],
        system_prompt: str | None = None,
        rag_context: str | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Build the message list. Delegates to ``context_builder.build_messages``."""
        return await build_messages(
            query,
            history,
            self.provider,
            self._detect_function_call,
            system_prompt=system_prompt,
            rag_context=rag_context,
            **kwargs,
        )

    def _repair_tool_history(
        self, messages: list[dict[str, Any]], allowed_tool_names: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """Repair tool/function call history. Delegates to ``context_builder``."""
        return repair_tool_history(
            messages, self._detect_function_call, allowed_tool_names=allowed_tool_names
        )

    async def _recompact_if_needed(
        self,
        messages: list[dict[str, Any]],
        *,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
    ) -> list[dict[str, Any]]:
        """Trim messages if over budget. Delegates to ``context_builder``."""
        return await recompact_if_needed(messages, context_window=context_window)

    @staticmethod
    def _expand_loaded_tools(
        function_calls: list[FunctionCall],
        effective_tools: list[dict[str, Any]] | None,
        hass: Any,
        denied_tools: frozenset[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        """Expand effective_tools when load_tool was called. Delegates to ``tool_loop``."""
        return expand_loaded_tools(
            function_calls,
            effective_tools,
            hass,
            denied_tools=denied_tools,
            config=config,
        )

    # --- Main orchestration ---

    def _build_loop_kwargs(
        self,
        runtime: dict[str, Any],
        built_messages: list[dict[str, Any]],
        effective_tools: list[dict[str, Any]] | None,
        effective_max_iterations: int,
        hass: Any,
        system_prompt: str | None,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the common kwargs dict for tool loop functions."""
        from ..tools.base import ToolRegistry

        return {
            "provider": self.provider,
            "built_messages": built_messages,
            "effective_tools": effective_tools,
            "effective_max_iterations": effective_max_iterations,
            "detect_function_call_fn": self._detect_function_call,
            "allowed_names": {
                t.id for t in ToolRegistry.get_all_tools(hass=None, enabled_only=True)
            },
            "hass": hass,
            "denied_tools": runtime["denied_tools"],
            "config": runtime["config"],
            "context_window": runtime["context_window"],
            "user_id": runtime["user_id"],
            "system_prompt": system_prompt,
            "build_provider_kwargs_fn": self._build_provider_kwargs,
            "build_updated_messages_fn": self._build_updated_messages,
            "kwargs": kwargs,
        }

    async def _prepare_query(
        self,
        query: str,
        messages: list[dict[str, Any]],
        system_prompt: str | None,
        tools: list[dict[str, Any]] | None,
        kwargs: dict[str, Any],
        *,
        non_stream: bool = False,
    ) -> (
        tuple[
            str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]] | None, bool
        ]
        | None
    ):
        """Common preparation: sanitize, extract runtime, build messages. Returns None if invalid."""
        attachments = kwargs.pop("attachments", None)
        sanitized_query = self._normalize_query_with_attachments(
            self._sanitize_query(query), attachments
        )
        if not sanitized_query and not attachments:
            return None
        runtime = self._extract_runtime_context(kwargs)
        effective_tools = self._filter_denied_tools(
            tools, runtime["denied_tools"], non_stream=non_stream
        )
        built_messages, was_compacted = await self._build_messages(
            sanitized_query,
            messages,
            system_prompt=system_prompt,
            rag_context=runtime["rag_context"],
            context_window=runtime["context_window"],
            memory_flush_fn=runtime["memory_flush_fn"],
            user_id=runtime["user_id"],
            session_id=runtime["session_id"],
            model=kwargs.get("model"),
            attachments=attachments,
        )
        return sanitized_query, runtime, built_messages, effective_tools, was_compacted

    async def process_stream(
        self,
        query: str,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        """Process a user query and stream the AI response. Yields AgentEvent objects."""
        from .events import CompactionEvent, ErrorEvent

        effective_max_iterations: int = kwargs.pop(
            "max_iterations", self.max_iterations
        )
        prepared = await self._prepare_query(
            query, messages, system_prompt, tools, kwargs
        )
        if prepared is None:
            yield ErrorEvent(message=EMPTY_QUERY_ERROR)
            return

        _, runtime, built_messages, effective_tools, was_compacted = prepared
        if was_compacted:
            yield CompactionEvent(messages=built_messages)

        loop_kwargs = self._build_loop_kwargs(
            runtime,
            built_messages,
            effective_tools,
            effective_max_iterations,
            kwargs.get("hass"),
            system_prompt,
            kwargs,
        )
        try:
            async for event in run_tool_loop_stream(**loop_kwargs):
                yield event
        except Exception as e:
            _LOGGER.error("Error processing streaming query: %s", str(e))
            yield ErrorEvent(message=str(e))

    async def process(
        self,
        query: str,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Process a user query and return the AI response."""
        effective_max_iterations: int = kwargs.pop(
            "max_iterations", self.max_iterations
        )
        prepared = await self._prepare_query(
            query, messages, system_prompt, tools, kwargs, non_stream=True
        )
        if prepared is None:
            return {"success": False, "error": EMPTY_QUERY_ERROR}

        _, runtime, built_messages, effective_tools, _ = prepared
        loop_kwargs = self._build_loop_kwargs(
            runtime,
            built_messages,
            effective_tools,
            effective_max_iterations,
            kwargs.get("hass"),
            system_prompt,
            kwargs,
        )
        try:
            return await run_tool_loop_nonstream(**loop_kwargs)
        except Exception as e:
            _LOGGER.error("Error processing query: %s", str(e))
            return {"success": False, "error": str(e)}
