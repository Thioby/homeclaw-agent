"""Tests for QueryProcessor."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeclaw.core.query_processor import (
    INVISIBLE_CHARS,
    QueryProcessor,
)


class MockProvider:
    """Mock AI provider for testing."""

    def __init__(self, response: str = "Test response") -> None:
        """Initialize with a canned response."""
        self._response = response
        self.get_response = AsyncMock(return_value=response)
        self.supports_tools = True

    async def get_response_async(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> str:
        """Get a mock response."""
        return await self.get_response(messages, **kwargs)


class TestSanitizeQuery:
    """Tests for _sanitize_query method."""

    def test_sanitize_query_removes_invisible_chars(self) -> None:
        """Test that invisible characters (BOM, zero-width) are removed."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        # Build query with various invisible characters
        query_with_invisibles = (
            "\ufeffHello\u200bWorld\u200c!\u200d\u2060"  # BOM, ZW-space, ZWNJ, ZWJ, WJ
        )
        result = processor._sanitize_query(query_with_invisibles)

        assert result == "HelloWorld!"
        # Verify no invisible chars remain
        for char in INVISIBLE_CHARS:
            assert char not in result

    def test_sanitize_query_truncates_long_query(self) -> None:
        """Test that long queries are truncated to max_length."""
        provider = MockProvider()
        processor = QueryProcessor(provider, max_query_length=50)

        long_query = "a" * 100
        result = processor._sanitize_query(long_query)

        assert len(result) == 50
        assert result == "a" * 50

    def test_sanitize_query_truncates_with_custom_max_length(self) -> None:
        """Test truncation with explicit max_length parameter."""
        provider = MockProvider()
        processor = QueryProcessor(provider, max_query_length=1000)

        long_query = "b" * 200
        result = processor._sanitize_query(long_query, max_length=30)

        assert len(result) == 30
        assert result == "b" * 30

    def test_sanitize_query_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        query_with_whitespace = "   Hello World   \n\t"
        result = processor._sanitize_query(query_with_whitespace)

        assert result == "Hello World"

    def test_sanitize_query_handles_empty_string(self) -> None:
        """Test that empty strings are handled gracefully."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        result = processor._sanitize_query("")
        assert result == ""

        result = processor._sanitize_query("   ")
        assert result == ""


class TestBuildMessages:
    """Tests for _build_messages method."""

    @pytest.mark.asyncio
    async def test_build_messages_with_history(self) -> None:
        """Test that history is combined with new query."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]
        query = "New question"

        result = await processor._build_messages(query, history)

        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "Previous question"}
        assert result[1] == {"role": "assistant", "content": "Previous answer"}
        assert result[2] == {"role": "user", "content": "New question"}

    @pytest.mark.asyncio
    async def test_build_messages_with_system_prompt(self) -> None:
        """Test that system prompt is added first."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        history = [{"role": "user", "content": "Previous question"}]
        query = "New question"
        system_prompt = "You are a helpful assistant."

        result = await processor._build_messages(
            query, history, system_prompt=system_prompt
        )

        assert len(result) == 3
        assert result[0] == {
            "role": "system",
            "content": "You are a helpful assistant.",
        }
        assert result[1] == {"role": "user", "content": "Previous question"}
        assert result[2] == {"role": "user", "content": "New question"}

    @pytest.mark.asyncio
    async def test_build_messages_without_history(self) -> None:
        """Test building messages with no history."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        query = "Hello"
        result = await processor._build_messages(query, [])

        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Hello"}

    @pytest.mark.asyncio
    async def test_build_messages_with_system_prompt_no_history(self) -> None:
        """Test system prompt with empty history."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        query = "Hello"
        result = await processor._build_messages(query, [], system_prompt="Be concise.")

        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "Be concise."}
        assert result[1] == {"role": "user", "content": "Hello"}


class TestProcess:
    """Tests for the process method."""

    @pytest.mark.asyncio
    async def test_process_simple_query(self) -> None:
        """Test processing a simple query returns success with response."""
        provider = MockProvider(response="Hello! How can I help?")
        processor = QueryProcessor(provider)

        result = await processor.process(query="Hi there", messages=[])

        assert result["success"] is True
        assert result["response"] == "Hello! How can I help?"
        assert "messages" in result
        provider.get_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_empty_query_fails(self) -> None:
        """Test that empty query returns an error."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        result = await processor.process(query="", messages=[])

        assert result["success"] is False
        assert "error" in result
        provider.get_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_whitespace_only_query_fails(self) -> None:
        """Test that whitespace-only query returns an error."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        result = await processor.process(query="   \n\t  ", messages=[])

        assert result["success"] is False
        assert "error" in result
        provider.get_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_with_tools(self) -> None:
        """Test that tools are passed to provider."""
        provider = MockProvider(response="Using a tool")
        processor = QueryProcessor(provider)

        tools = [
            {"name": "get_weather", "description": "Get weather info"},
            {"name": "search", "description": "Search the web"},
        ]

        result = await processor.process(
            query="What's the weather?", messages=[], tools=tools
        )

        assert result["success"] is True
        provider.get_response.assert_called_once()
        # Verify tools were passed to get_response
        call_kwargs = provider.get_response.call_args.kwargs
        assert call_kwargs.get("tools") == tools

    @pytest.mark.asyncio
    async def test_process_with_system_prompt(self) -> None:
        """Test that system prompt is included in messages."""
        provider = MockProvider(response="I am helpful.")
        processor = QueryProcessor(provider)

        result = await processor.process(
            query="Hello",
            messages=[],
            system_prompt="You are a helpful assistant.",
        )

        assert result["success"] is True
        # Verify the messages passed to provider include system prompt
        call_args = provider.get_response.call_args.args[0]
        assert call_args[0]["role"] == "system"
        assert call_args[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_process_with_history(self) -> None:
        """Test that conversation history is preserved."""
        provider = MockProvider(response="Continuing conversation")
        processor = QueryProcessor(provider)

        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
        ]

        result = await processor.process(query="Second message", messages=history)

        assert result["success"] is True
        # Verify the messages passed include history
        call_args = provider.get_response.call_args.args[0]
        assert len(call_args) == 3
        assert call_args[0]["content"] == "First message"
        assert call_args[1]["content"] == "First response"
        assert call_args[2]["content"] == "Second message"

    @pytest.mark.asyncio
    async def test_process_returns_updated_messages(self) -> None:
        """Test that process returns the updated message list."""
        provider = MockProvider(response="Response text")
        processor = QueryProcessor(provider)

        result = await processor.process(query="Hello", messages=[])

        assert "messages" in result
        messages = result["messages"]
        # Should have user message + assistant response
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Response text"}

    @pytest.mark.asyncio
    async def test_process_handles_provider_error(self) -> None:
        """Test that provider exceptions are handled gracefully."""
        provider = MockProvider()
        provider.get_response = AsyncMock(side_effect=Exception("API Error"))
        processor = QueryProcessor(provider)

        result = await processor.process(query="Hello", messages=[])

        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]


class TestBuildMessagesWithRagContext:
    """Tests for _build_messages with RAG context."""

    @pytest.mark.asyncio
    async def test_build_messages_with_rag_context(self) -> None:
        """Test that RAG context is added to system prompt."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        rag_context = "Entity: sensor.temp, State: 22°C, Area: Living Room"
        result = await processor._build_messages(
            "What's the temperature?",
            [],
            system_prompt="You are a helpful assistant.",
            rag_context=rag_context,
        )

        assert len(result) == 2  # system + user
        assert result[0]["role"] == "system"
        assert "SUGGESTED ENTITIES" in result[0]["content"]
        assert rag_context in result[0]["content"]
        assert "You are a helpful assistant." in result[0]["content"]

    @pytest.mark.asyncio
    async def test_build_messages_with_rag_context_no_system_prompt(self) -> None:
        """Test RAG context when no system prompt is provided."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        rag_context = "Entity: light.kitchen, State: on"
        result = await processor._build_messages(
            "Turn off the kitchen light", [], rag_context=rag_context
        )

        assert len(result) == 2  # system (from RAG) + user
        assert result[0]["role"] == "system"
        assert rag_context in result[0]["content"]

    @pytest.mark.asyncio
    async def test_build_messages_without_rag_context(self) -> None:
        """Test that messages work without RAG context."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        result = await processor._build_messages(
            "Hello", [], system_prompt="Be helpful."
        )

        assert len(result) == 2
        assert "RELEVANT CONTEXT" not in result[0]["content"]


class TestProcessWithRagContext:
    """Tests for process method with RAG context."""

    @pytest.mark.asyncio
    async def test_process_includes_rag_context(self) -> None:
        """Test that RAG context is passed through to messages."""
        provider = MockProvider(response="The temperature is 22°C.")
        processor = QueryProcessor(provider)

        rag_context = "sensor.living_room_temp: 22°C"

        result = await processor.process(
            query="What's the temperature?", messages=[], rag_context=rag_context
        )

        assert result["success"] is True
        # Verify provider received messages with RAG context
        call_args = provider.get_response.call_args.args[0]
        system_message = call_args[0]
        assert system_message["role"] == "system"
        assert rag_context in system_message["content"]


class TestDetectFunctionCall:
    """Tests for _detect_function_call method."""

    def test_detect_gemini_function_call(self) -> None:
        """Test detection of Gemini-style function call."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        response = (
            '{"functionCall": {"name": "get_weather", "args": {"location": "NYC"}}}'
        )
        result = processor._detect_function_call(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "get_weather"
        assert result[0].arguments == {"location": "NYC"}

    def test_detect_anthropic_function_call(self) -> None:
        """Test detection of Anthropic-style tool_use."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        response = '{"tool_use": {"id": "tool_123", "name": "search", "input": {"query": "weather"}}}'
        result = processor._detect_function_call(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "search"
        assert result[0].id == "tool_123"
        assert result[0].arguments == {"query": "weather"}

    def test_detect_simple_function_format(self) -> None:
        """Test detection of simple function format."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        response = '{"function": "get_entities", "parameters": {"domain": "light"}}'
        result = processor._detect_function_call(response)

        assert result is not None
        assert len(result) == 1
        assert result[0].name == "get_entities"
        assert result[0].arguments == {"domain": "light"}

    def test_detect_no_function_call_plain_text(self) -> None:
        """Test that plain text doesn't trigger function call detection."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        response = "Hello, how can I help you today?"
        result = processor._detect_function_call(response)

        assert result is None

    def test_detect_no_function_call_regular_json(self) -> None:
        """Test that regular JSON without function markers is not detected."""
        provider = MockProvider()
        processor = QueryProcessor(provider)

        response = '{"temperature": 72, "humidity": 45}'
        result = processor._detect_function_call(response)

        assert result is None


class TestAgenticLoop:
    """Tests for the agentic loop behavior in process method."""

    @pytest.mark.asyncio
    async def test_single_tool_call_and_response(self) -> None:
        """Test that a single tool call is executed and result fed back."""
        from unittest.mock import patch
        from custom_components.homeclaw.tools.base import ToolResult

        # First call returns function call, second returns final response
        provider = MockProvider()
        provider.get_response = AsyncMock(
            side_effect=[
                '{"functionCall": {"name": "get_weather", "args": {"location": "NYC"}}}',
                "The weather in NYC is sunny and 72°F.",
            ]
        )
        processor = QueryProcessor(provider)

        # Mock tool execution
        mock_result = ToolResult(
            output="Temperature: 72°F, Condition: Sunny", success=True
        )

        with patch.object(
            processor,
            "_detect_function_call",
            side_effect=[
                [
                    MagicMock(
                        id="fc1", name="get_weather", arguments={"location": "NYC"}
                    )
                ],
                None,  # No function call in final response
            ],
        ):
            with patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await processor.process(
                    query="What's the weather in NYC?", messages=[]
                )

        assert result["success"] is True
        assert result["response"] == "The weather in NYC is sunny and 72°F."
        assert provider.get_response.call_count == 2

    @pytest.mark.asyncio
    async def test_max_iterations_limit(self) -> None:
        """Test that max_iterations prevents infinite loops."""
        from unittest.mock import patch
        from custom_components.homeclaw.tools.base import ToolResult

        # Provider always returns function call
        provider = MockProvider()
        provider.get_response = AsyncMock(
            return_value='{"functionCall": {"name": "endless", "args": {}}}'
        )
        processor = QueryProcessor(provider, max_iterations=3)

        mock_result = ToolResult(output="Done", success=True)

        with patch(
            "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await processor.process(query="Loop forever", messages=[])

        assert result["success"] is False
        assert "Maximum iterations" in result["error"]
        # Should have called exactly max_iterations times
        assert provider.get_response.call_count == 3

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self) -> None:
        """Test that tool execution errors are handled gracefully."""
        from unittest.mock import patch
        from custom_components.homeclaw.tools.base import ToolExecutionError

        # First call returns function call, second returns final response
        provider = MockProvider()
        provider.get_response = AsyncMock(
            side_effect=[
                '{"functionCall": {"name": "broken_tool", "args": {}}}',
                "I encountered an error but I'll help differently.",
            ]
        )
        processor = QueryProcessor(provider)

        with patch(
            "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
            new_callable=AsyncMock,
            side_effect=ToolExecutionError("Tool failed", tool_id="broken_tool"),
        ):
            result = await processor.process(query="Use broken tool", messages=[])

        # Should still succeed with final response
        assert result["success"] is True
        assert "error" not in result or result.get("error") is None
        assert provider.get_response.call_count == 2

    @pytest.mark.asyncio
    async def test_no_tool_call_returns_immediately(self) -> None:
        """Test that simple text responses return without iteration."""
        provider = MockProvider(response="Just a simple answer.")
        processor = QueryProcessor(provider)

        result = await processor.process(query="Hello", messages=[])

        assert result["success"] is True
        assert result["response"] == "Just a simple answer."
        # Only one call to provider
        provider.get_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_sequence(self) -> None:
        """Test multiple sequential tool calls."""
        from unittest.mock import patch
        from custom_components.homeclaw.tools.base import ToolResult

        provider = MockProvider()
        provider.get_response = AsyncMock(
            side_effect=[
                '{"functionCall": {"name": "tool_a", "args": {}}}',
                '{"functionCall": {"name": "tool_b", "args": {}}}',
                "Final result after two tools.",
            ]
        )
        processor = QueryProcessor(provider)

        mock_result = ToolResult(output="Tool output", success=True)

        with patch(
            "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await processor.process(query="Use multiple tools", messages=[])

        assert result["success"] is True
        assert result["response"] == "Final result after two tools."
        assert provider.get_response.call_count == 3
