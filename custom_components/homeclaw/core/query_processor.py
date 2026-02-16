"""Query processor for AI agent interactions."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator

from ..function_calling import FunctionCallHandler, FunctionCall
from .compaction import compact_messages, truncation_fallback
from .function_call_parser import FunctionCallParser
from .response_parser import ResponseParser
from .tool_call_codec import build_assistant_tool_message, normalize_tool_calls
from .token_estimator import (
    DEFAULT_CONTEXT_WINDOW,
    compute_context_budget,
    estimate_messages_tokens,
)
from .tool_executor import ToolExecutor

if TYPE_CHECKING:
    from ..providers.registry import AIProvider

_LOGGER = logging.getLogger(__name__)

# Invisible characters that should be stripped from queries
INVISIBLE_CHARS = [
    "\ufeff",  # BOM (Byte Order Mark)
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u2060",  # Word joiner
]


class QueryProcessor:
    """Processes user queries for AI providers.

    This class handles query sanitization, message building, and
    coordinating with AI providers to generate responses.
    """

    def __init__(
        self,
        provider: AIProvider,
        max_iterations: int = 20,
        max_query_length: int = 1000,
    ) -> None:
        """Initialize the query processor.

        Args:
            provider: The AI provider to use for generating responses.
            max_iterations: Maximum tool call iterations (for future use).
            max_query_length: Maximum allowed query length after sanitization.
        """
        self.provider = provider
        self.max_iterations = max_iterations
        self.max_query_length = max_query_length
        self.response_parser = ResponseParser()
        self.function_call_parser = FunctionCallParser(self.response_parser)

    def _sanitize_query(self, query: str, max_length: int | None = None) -> str:
        """Sanitize a user query by removing invisible characters.

        Args:
            query: The raw user query.
            max_length: Optional maximum length override. If not provided,
                uses self.max_query_length.

        Returns:
            The sanitized query string.
        """
        # Remove invisible characters
        sanitized = query
        for char in INVISIBLE_CHARS:
            sanitized = sanitized.replace(char, "")

        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()

        # Truncate to max length
        effective_max = max_length if max_length is not None else self.max_query_length
        if len(sanitized) > effective_max:
            sanitized = sanitized[:effective_max]

        return sanitized

    async def _build_messages(
        self,
        query: str,
        history: list[dict[str, Any]],
        system_prompt: str | None = None,
        rag_context: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Build the message list for the AI provider.

        Assembles system prompt, conversation history, and the current query
        into a flat list.  When the result exceeds the model's context budget,
        automatically triggers compaction (AI summarization of old messages).

        Supports multimodal content: when attachments are present, image
        attachments produce provider-specific content blocks, and text/PDF
        attachments have their extracted content appended to the query.

        Args:
            query: The current user query.
            history: Previous conversation messages.
            system_prompt: Optional system message to prepend.
            rag_context: Optional RAG context to include.
            **kwargs: Extra context forwarded to compaction, including:
                - context_window (int): Model's context window in tokens.
                - memory_flush_fn: Async callable for pre-compaction memory capture.
                - user_id (str): For memory flush scoping.
                - session_id (str): For memory flush context.
                - attachments: List of ProcessedAttachment objects.

        Returns:
            List of message dictionaries ready for the provider.
        """
        messages: list[dict[str, Any]] = []

        # Build system prompt with RAG context if available
        final_system_prompt = system_prompt or ""

        if rag_context:
            rag_section = (
                "\n\n--- SUGGESTED ENTITIES ---\n"
                f"{rag_context}\n"
                "--- END SUGGESTIONS ---\n\n"
                "These are suggestions based on your query. Use available tools "
                "(get_entities_by_domain, get_state, etc.) to find other entities if needed."
            )
            final_system_prompt = (
                final_system_prompt + rag_section
                if final_system_prompt
                else rag_section
            )
            _LOGGER.info(
                "RAG context added to system prompt (%d chars)", len(rag_context)
            )
            _LOGGER.debug("RAG context FULL: %s", rag_context)
            _LOGGER.debug(
                "Final system prompt length: %d chars", len(final_system_prompt)
            )

        # Add system prompt first if we have one
        if final_system_prompt:
            messages.append({"role": "system", "content": final_system_prompt})

        # Add conversation history
        messages.extend(history)

        # --- Process attachments into the user message ---
        attachments = kwargs.pop("attachments", None)
        enriched_query = query
        image_attachments = []

        if attachments:
            from ..file_processor import get_image_base64

            text_parts: list[str] = []
            for att in attachments:
                if att.is_image:
                    b64 = get_image_base64(att)
                    if b64:
                        image_attachments.append(
                            {
                                "mime_type": att.mime_type,
                                "data": b64,
                                "filename": att.filename,
                            }
                        )
                elif att.content_text:
                    text_parts.append(
                        f"--- Attached file: {att.filename} ---\n"
                        f"{att.content_text}\n"
                        f"--- End of {att.filename} ---"
                    )

            # Append extracted text to the query
            if text_parts:
                enriched_query = query + "\n\n" + "\n\n".join(text_parts)
                _LOGGER.info(
                    "Enriched query with %d text attachment(s), total %d chars",
                    len(text_parts),
                    len(enriched_query),
                )

        # Build the user message (multimodal or plain text)
        if image_attachments:
            # Multimodal message: uses provider-agnostic format with _images key.
            # Provider converters (gemini_convert, openai, anthropic) will handle
            # the conversion to their specific format.
            messages.append(
                {
                    "role": "user",
                    "content": enriched_query,
                    "_images": image_attachments,
                }
            )
            _LOGGER.info(
                "Built multimodal user message with %d image(s)",
                len(image_attachments),
            )
        else:
            messages.append({"role": "user", "content": enriched_query})

        # --- Context window compaction ---
        context_window = kwargs.get("context_window", DEFAULT_CONTEXT_WINDOW)
        memory_flush_fn = kwargs.get("memory_flush_fn")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id", "")

        # Filter provider_kwargs for the compaction summarization call
        provider_kwargs = {}
        if kwargs.get("model"):
            provider_kwargs["model"] = kwargs["model"]

        messages = await compact_messages(
            messages,
            context_window=context_window,
            provider=self.provider,
            memory_flush_fn=memory_flush_fn,
            user_id=user_id,
            session_id=session_id,
            **provider_kwargs,
        )

        return messages

    async def _recompact_if_needed(
        self,
        messages: list[dict[str, Any]],
        *,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
    ) -> list[dict[str, Any]]:
        """Trim messages if tool results pushed us over the context budget.

        Called inside the tool call loop after tool results are appended.
        Unlike full compaction (which summarises old messages via AI), this
        method only **truncates long tool result contents** to avoid
        discarding tool call/result pairs that the model needs to remember
        what it has already done.  This prevents the "Gemini loop" bug
        where summarisation removes earlier tool results, causing the model
        to re-issue the same tool calls.

        Args:
            messages: Current message list (may include tool results).
            context_window: Model's context window in tokens.

        Returns:
            Possibly trimmed message list.
        """
        budget = compute_context_budget(context_window)
        available = budget["available_for_input"]
        estimated = estimate_messages_tokens(messages)

        if estimated <= available:
            return messages

        _LOGGER.warning(
            "Tool loop re-compaction: %d tokens > %d budget, truncating tool results",
            estimated,
            available,
        )

        # Strategy: truncate the longest tool/function result messages first.
        # We never remove messages — only shorten their content.
        MAX_TOOL_RESULT_CHARS = 2000
        MIN_TOOL_RESULT_CHARS = 200

        result = list(messages)
        limit = MAX_TOOL_RESULT_CHARS

        while limit >= MIN_TOOL_RESULT_CHARS:
            for msg in result:
                role = msg.get("role", "")
                if role in ("tool", "function"):
                    content = msg.get("content", "")
                    if len(content) > limit:
                        msg["content"] = content[:limit] + "\n... [truncated]"
            estimated = estimate_messages_tokens(result)
            if estimated <= available:
                _LOGGER.info(
                    "Tool result truncation brought tokens to %d (budget %d, limit %d chars)",
                    estimated,
                    available,
                    limit,
                )
                return result
            limit //= 2

        # Last resort: drop oldest non-system, non-user messages from the beginning
        _LOGGER.warning(
            "Tool result truncation insufficient (%d > %d), falling back to message trimming",
            estimated,
            available,
        )
        return truncation_fallback(result, available)

    def _detect_function_call(self, response_text: str) -> list[FunctionCall] | None:
        """Detect and parse function calls from response text.

        Delegates to FunctionCallParser which handles all provider-specific
        formats (OpenAI, Gemini, Anthropic, simple/custom).

        Args:
            response_text: The text response from the AI provider.

        Returns:
            List of FunctionCall objects if found, None otherwise.
        """
        return self.function_call_parser.detect(response_text)

    async def process_stream(
        self,
        query: str,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:  # Typed as Any to support AgentEvent
        """Process a user query and stream the AI response.

        Args:
            query: The user's query text.
            messages: Conversation history (previous messages).
            system_prompt: Optional system message for context.
            tools: Optional list of tools available to the AI.
            **kwargs: Additional arguments passed to the provider.
                max_iterations (int): Override the instance default for this call.

        Yields:
            AgentEvent objects (TextEvent, ToolCallEvent, etc.)
        """
        # Per-call iteration limit (avoids mutating shared state)
        effective_max_iterations: int = kwargs.pop(
            "max_iterations", self.max_iterations
        )
        from .events import (
            TextEvent,
            ToolCallEvent,
            ToolResultEvent,
            StatusEvent,
            ErrorEvent,
            CompletionEvent,
        )

        # Sanitize the query
        sanitized_query = self._sanitize_query(query)

        # Check for empty query (allow empty text if attachments are present)
        attachments = kwargs.get("attachments")
        if not sanitized_query and not attachments:
            yield ErrorEvent(message="Query is empty or contains only whitespace")
            return

        # Default to a generic prompt for image-only messages
        if not sanitized_query and attachments:
            sanitized_query = "Describe what you see in the attached image(s)."

        # Extract RAG context from kwargs
        rag_context = kwargs.pop("rag_context", None)

        # Extract denied tools (for subagent/heartbeat security restrictions)
        denied_tools: frozenset[str] | None = kwargs.pop("denied_tools", None)

        # Extract compaction-related kwargs (don't pass to provider)
        context_window = kwargs.pop("context_window", DEFAULT_CONTEXT_WINDOW)
        memory_flush_fn = kwargs.pop("memory_flush_fn", None)
        user_id = kwargs.get("user_id", "")
        session_id = kwargs.get("session_id", "")

        # Extract file attachments (consumed by _build_messages, not passed to provider)
        attachments = kwargs.pop("attachments", None)

        # Filter denied tools from the tools list sent to the LLM (two-layer defense)
        effective_tools = tools
        if denied_tools and tools:
            effective_tools = [
                t
                for t in tools
                if t.get("function", {}).get("name") not in denied_tools
            ]
            filtered_count = len(tools) - len(effective_tools)
            if filtered_count:
                _LOGGER.debug(
                    "Filtered %d denied tools from LLM tool list", filtered_count
                )

        # Build the message list with RAG context and compaction
        built_messages = await self._build_messages(
            sanitized_query,
            messages,
            system_prompt=system_prompt,
            rag_context=rag_context,
            context_window=context_window,
            memory_flush_fn=memory_flush_fn,
            user_id=user_id,
            session_id=session_id,
            model=kwargs.get("model"),
            attachments=attachments,
        )

        hass = kwargs.get("hass")
        current_iteration = 0

        try:
            while current_iteration < effective_max_iterations:
                # Check if provider supports streaming
                if not hasattr(self.provider, "get_response_stream"):
                    # Fall back to non-streaming
                    _LOGGER.debug("Provider doesn't support streaming, using fallback")
                    provider_kwargs: dict[str, Any] = {**kwargs}
                    if effective_tools is not None:
                        provider_kwargs["tools"] = effective_tools

                    response_text = await self.provider.get_response(
                        built_messages, **provider_kwargs
                    )

                    # Detect function call BEFORE yielding text
                    function_calls = self._detect_function_call(response_text)

                    if function_calls:
                        # Extract any text the model produced before the tool call
                        # (Anthropic embeds it as "text" key alongside "tool_use")
                        try:
                            parsed = json.loads(response_text)
                            prefixed_text = (
                                parsed.get("text", "")
                                if isinstance(parsed, dict)
                                else ""
                            )
                        except (json.JSONDecodeError, ValueError):
                            prefixed_text = ""
                        if prefixed_text:
                            yield TextEvent(content=prefixed_text)
                    else:
                        # No tool call — yield the full response as text
                        yield TextEvent(content=response_text)

                    if not function_calls:
                        # No function call, return the response
                        updated_messages = list(built_messages)
                        if (
                            system_prompt
                            and updated_messages
                            and updated_messages[0].get("role") == "system"
                        ):
                            updated_messages = updated_messages[1:]

                        updated_messages.append(
                            {"role": "assistant", "content": response_text}
                        )

                        yield CompletionEvent(messages=updated_messages)
                        return

                    # Handle function calls (same as non-streaming)
                    built_messages.append(
                        {"role": "assistant", "content": response_text}
                    )

                    # Use ToolExecutor to execute tools and yield results
                    # Note: We use "result" mode which yields dicts, so we must map them.
                    async for tool_event in ToolExecutor.execute_tool_calls(
                        function_calls,
                        hass,
                        built_messages,
                        yield_mode="result",
                        denied_tools=denied_tools,
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

                    # Re-check context budget after tool results were appended
                    built_messages = await self._recompact_if_needed(
                        built_messages, context_window=context_window
                    )

                    current_iteration += 1
                    continue

                # Provider supports streaming
                provider_kwargs = {**kwargs}
                if effective_tools is not None:
                    provider_kwargs["tools"] = effective_tools

                accumulated_text = ""
                accumulated_tool_calls = []

                _LOGGER.debug(
                    "Streaming iteration %d: sending %d messages to provider",
                    current_iteration,
                    len(built_messages),
                )

                # Stream the response
                async for chunk in self.provider.get_response_stream(
                    built_messages, **provider_kwargs
                ):
                    if chunk.get("type") == "text":
                        # Emit incremental text immediately for Assist Voice
                        # and chat delta streaming.
                        content = chunk.get("content", "")
                        if not content:
                            continue
                        accumulated_text += content
                        yield TextEvent(content=content)
                    elif chunk.get("type") == "tool_call":
                        # Accumulate tool calls but DON'T send to client yet
                        accumulated_tool_calls.append(chunk)
                        _LOGGER.debug(
                            "Tool call detected in stream: %s", chunk.get("name")
                        )
                    elif chunk.get("type") == "error":
                        yield ErrorEvent(message=chunk.get("message", "Unknown error"))
                        return

                # After streaming completes, check for tool calls
                if accumulated_tool_calls:
                    _LOGGER.info(
                        "Processing %d tool call(s) from stream",
                        len(accumulated_tool_calls),
                    )

                    # Send status update to client
                    tool_names = ", ".join(
                        tc.get("name", "unknown") for tc in accumulated_tool_calls
                    )
                    yield StatusEvent(message=f"Calling tools: {tool_names}...")

                    normalized_tool_calls = normalize_tool_calls(accumulated_tool_calls)

                    # Convert to FunctionCall objects
                    function_calls = [
                        FunctionCall(
                            id=tc.get("id") or tc.get("name", "unknown"),
                            name=tc["name"],
                            arguments=tc.get("args", {}),
                        )
                        for tc in normalized_tool_calls
                    ]

                    # Emit ToolCallEvents for each tool
                    for fc in function_calls:
                        yield ToolCallEvent(
                            tool_name=fc.name,
                            tool_args=fc.arguments,
                            tool_call_id=fc.id,
                        )

                    # Append assistant's message (the tool call) to conversation
                    # CRITICAL: Must preserve the EXACT format returned by Gemini, including thought_signature
                    # Per Gemini 3 docs: "include all Parts from all previous messages in the conversation
                    # history when sending a new request, exactly as they were returned by the model"

                    # Store the ORIGINAL tool call dict from Gemini stream
                    # This should contain the complete functionCall object with thought_signature
                    tool_call_obj = accumulated_tool_calls[0].get("_raw_function_call")

                    if not tool_call_obj:
                        assistant_tool_json = build_assistant_tool_message(
                            normalized_tool_calls
                        )
                        built_messages.append(
                            {
                                "role": "assistant",
                                "content": assistant_tool_json,
                            }
                        )
                    else:
                        built_messages.append(
                            {
                                "role": "assistant",
                                "content": json.dumps(tool_call_obj),
                            }
                        )

                    # Execute tools INTERNALLY using ToolExecutor
                    # Use "result" mode to get results, but map to Events.
                    # Note: We rely on "result" mode because "status" mode only yields text statuses.
                    # We want structured results.
                    async for tool_event in ToolExecutor.execute_tool_calls(
                        function_calls,
                        hass,
                        built_messages,
                        yield_mode="result",
                        denied_tools=denied_tools,
                    ):
                        if tool_event.get("type") == "tool_result":
                            yield ToolResultEvent(
                                tool_name=tool_event["name"],
                                tool_result=tool_event["result"],
                                tool_call_id=tool_event.get("id", "unknown"),
                            )
                        # We might want to yield status events here too, but "result" mode doesn't give them.
                        # For now, we just yield the result.

                    # Re-check context budget after tool results were appended
                    built_messages = await self._recompact_if_needed(
                        built_messages, context_window=context_window
                    )

                    # This will trigger a NEW stream with tool results
                    current_iteration += 1
                    _LOGGER.info(
                        "Tool execution complete, starting iteration %d/%d. "
                        "Text accumulated so far: %d chars",
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

                updated_messages = list(built_messages)
                if (
                    system_prompt
                    and updated_messages
                    and updated_messages[0].get("role") == "system"
                ):
                    updated_messages = updated_messages[1:]

                updated_messages.append(
                    {"role": "assistant", "content": accumulated_text}
                )

                yield CompletionEvent(messages=updated_messages)
                return

            # Max iterations reached — force a final response without tools
            _LOGGER.warning(
                "Max iterations (%d) reached. Forcing final text response (no tools).",
                effective_max_iterations,
            )
            try:
                # One last call WITHOUT tools so the model MUST produce text
                provider_kwargs_final = {**kwargs}
                provider_kwargs_final.pop("tools", None)

                if hasattr(self.provider, "get_response_stream"):
                    async for chunk in self.provider.get_response_stream(
                        built_messages, **provider_kwargs_final
                    ):
                        if chunk.get("type") == "text":
                            yield TextEvent(content=chunk.get("content", ""))
                else:
                    final_text = await self.provider.get_response(
                        built_messages, **provider_kwargs_final
                    )
                    if final_text:
                        yield TextEvent(content=final_text)

                yield CompletionEvent(messages=list(built_messages))
            except Exception as final_err:
                _LOGGER.error("Final forced response also failed: %s", final_err)
                yield ErrorEvent(
                    message="Maximum iterations reached without final response"
                )

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
        """Process a user query and return the AI response.

        Args:
            query: The user's query text.
            messages: Conversation history (previous messages).
            system_prompt: Optional system message for context.
            tools: Optional list of tools available to the AI.
            **kwargs: Additional arguments passed to the provider.
                max_iterations (int): Override the instance default for this call.

        Returns:
            Dict with:
                - success: True if successful, False otherwise.
                - response: The AI response text (on success).
                - messages: Updated message list including response (on success).
                - error: Error message (on failure).
        """
        # Per-call iteration limit (avoids mutating shared state)
        effective_max_iterations: int = kwargs.pop(
            "max_iterations", self.max_iterations
        )
        # Sanitize the query
        sanitized_query = self._sanitize_query(query)

        # Check for empty query (allow empty text if attachments are present)
        attachments_p = kwargs.get("attachments")
        if not sanitized_query and not attachments_p:
            return {
                "success": False,
                "error": "Query is empty or contains only whitespace",
            }

        # Default to a generic prompt for image-only messages
        if not sanitized_query and attachments_p:
            sanitized_query = "Describe what you see in the attached image(s)."

        # Extract RAG context from kwargs
        rag_context = kwargs.pop("rag_context", None)

        # Extract denied tools (for subagent/heartbeat security restrictions)
        denied_tools_p: frozenset[str] | None = kwargs.pop("denied_tools", None)

        # Extract compaction-related kwargs (don't pass to provider)
        context_window_p = kwargs.pop("context_window", DEFAULT_CONTEXT_WINDOW)
        memory_flush_fn_p = kwargs.pop("memory_flush_fn", None)
        user_id_p = kwargs.get("user_id", "")
        session_id_p = kwargs.get("session_id", "")

        # Filter denied tools from the tools list sent to the LLM (two-layer defense)
        effective_tools_p = tools
        if denied_tools_p and tools:
            effective_tools_p = [
                t
                for t in tools
                if t.get("function", {}).get("name") not in denied_tools_p
            ]
            filtered_count = len(tools) - len(effective_tools_p)
            if filtered_count:
                _LOGGER.debug(
                    "Filtered %d denied tools from LLM tool list (non-stream)",
                    filtered_count,
                )

        # Build the message list with RAG context and compaction
        built_messages = await self._build_messages(
            sanitized_query,
            messages,
            system_prompt=system_prompt,
            rag_context=rag_context,
            attachments=kwargs.pop("attachments", None),
            context_window=context_window_p,
            memory_flush_fn=memory_flush_fn_p,
            user_id=user_id_p,
            session_id=session_id_p,
            model=kwargs.get("model"),
        )

        hass = kwargs.get("hass")
        current_iteration = 0

        try:
            while current_iteration < effective_max_iterations:
                # Call the provider
                provider_kwargs: dict[str, Any] = {**kwargs}
                if effective_tools_p is not None:
                    provider_kwargs["tools"] = effective_tools_p

                response_text = await self.provider.get_response(
                    built_messages, **provider_kwargs
                )

                # Detect function call
                function_calls = self._detect_function_call(response_text)

                if not function_calls:
                    # No function call, return the response
                    # Build the updated message list with the response
                    updated_messages = list(built_messages)
                    # Remove system prompt from returned messages if present
                    if (
                        system_prompt
                        and updated_messages
                        and updated_messages[0].get("role") == "system"
                    ):
                        updated_messages = updated_messages[1:]

                    updated_messages.append(
                        {"role": "assistant", "content": response_text}
                    )

                    return {
                        "success": True,
                        "response": response_text,
                        "messages": updated_messages,
                    }

                # Handle function calls
                _LOGGER.info("Detected function calls: %s", function_calls)

                # Append assistant's message (the tool call)
                built_messages.append({"role": "assistant", "content": response_text})

                # Execute tools using ToolExecutor (no yields in non-streaming mode)
                async for _ in ToolExecutor.execute_tool_calls(
                    function_calls,
                    hass,
                    built_messages,
                    yield_mode="none",
                    denied_tools=denied_tools_p,
                ):
                    pass  # ToolExecutor with yield_mode="none" shouldn't yield anything

                # Re-check context budget after tool results were appended
                built_messages = await self._recompact_if_needed(
                    built_messages, context_window=context_window_p
                )

                current_iteration += 1

            # Max iterations reached
            return {
                "success": False,
                "error": "Maximum iterations reached without final response",
            }

        except Exception as e:
            _LOGGER.error("Error processing query: %s", str(e))
            return {
                "success": False,
                "error": str(e),
            }
