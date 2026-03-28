"""Tests for AnthropicAdapter."""

from __future__ import annotations

import json

import pytest

from custom_components.homeclaw.providers.adapters.anthropic_adapter import AnthropicAdapter
from custom_components.homeclaw.providers.adapters.stream_utils import ToolAccumulator
from custom_components.homeclaw.core.tool_call_codec import build_assistant_tool_message


# ---------------------------------------------------------------------------
# transform_tools
# ---------------------------------------------------------------------------


class TestTransformTools:
    """AnthropicAdapter.transform_tools converts OpenAI → Anthropic format."""

    def test_converts_single_tool(self) -> None:
        adapter = AnthropicAdapter()
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }
        ]
        result = adapter.transform_tools(openai_tools)
        assert len(result) == 1
        tool = result[0]
        assert tool["name"] == "get_weather"
        assert tool["description"] == "Get weather for a location"
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "location" in tool["input_schema"]["properties"]

    def test_converts_multiple_tools(self) -> None:
        adapter = AnthropicAdapter()
        openai_tools = [
            {
                "type": "function",
                "function": {"name": "tool_a", "description": "A", "parameters": {}},
            },
            {
                "type": "function",
                "function": {"name": "tool_b", "description": "B", "parameters": {}},
            },
        ]
        result = adapter.transform_tools(openai_tools)
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"

    def test_empty_list_returns_empty(self) -> None:
        adapter = AnthropicAdapter()
        assert adapter.transform_tools([]) == []

    def test_no_type_key_skipped(self) -> None:
        """Tools without 'type':'function' should be skipped."""
        adapter = AnthropicAdapter()
        result = adapter.transform_tools([{"name": "bare_tool"}])  # type: ignore[list-item]
        assert result == []

    def test_no_description_defaults_to_empty(self) -> None:
        adapter = AnthropicAdapter()
        result = adapter.transform_tools(
            [{"type": "function", "function": {"name": "no_desc", "parameters": {}}}]
        )
        assert result[0]["description"] == ""


# ---------------------------------------------------------------------------
# transform_messages
# ---------------------------------------------------------------------------


class TestTransformMessagesSystem:
    """System message is extracted from the list."""

    def test_system_extracted(self) -> None:
        adapter = AnthropicAdapter()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        converted, system = adapter.transform_messages(messages)
        assert system == "You are helpful."
        assert len(converted) == 1
        assert converted[0]["role"] == "user"

    def test_no_system_returns_none(self) -> None:
        adapter = AnthropicAdapter()
        messages = [{"role": "user", "content": "Hi"}]
        converted, system = adapter.transform_messages(messages)
        assert system is None
        assert len(converted) == 1


class TestTransformMessagesFunctionRole:
    """function role → user with tool_result block."""

    def test_function_becomes_tool_result(self) -> None:
        adapter = AnthropicAdapter()
        messages = [
            {
                "role": "function",
                "tool_use_id": "toolu_abc",
                "content": "sunny",
            }
        ]
        converted, _ = adapter.transform_messages(messages)
        assert len(converted) == 1
        msg = converted[0]
        assert msg["role"] == "user"
        block = msg["content"][0]
        assert block["type"] == "tool_result"
        assert block["tool_use_id"] == "toolu_abc"
        assert block["content"] == "sunny"

    def test_function_without_tool_use_id_skipped(self) -> None:
        adapter = AnthropicAdapter()
        messages = [
            {"role": "function", "name": "my_tool", "content": "result"},
        ]
        converted, _ = adapter.transform_messages(messages)
        assert converted == []

    def test_function_empty_content_included(self) -> None:
        """function messages may have empty content (e.g. void tools)."""
        adapter = AnthropicAdapter()
        messages = [
            {"role": "function", "tool_use_id": "toolu_x", "content": ""},
        ]
        converted, _ = adapter.transform_messages(messages)
        assert len(converted) == 1
        assert converted[0]["content"][0]["content"] == ""


class TestTransformMessagesAssistant:
    """Assistant messages with tool-call JSON → tool_use blocks."""

    def test_canonical_tool_calls_become_tool_use_blocks(self) -> None:
        adapter = AnthropicAdapter()
        content = build_assistant_tool_message(
            [{"id": "toolu_1", "name": "get_entity_state", "args": {"entity_id": "light.kitchen"}}]
        )
        messages = [{"role": "assistant", "content": content}]
        converted, _ = adapter.transform_messages(messages)
        assert len(converted) == 1
        blocks = converted[0]["content"]
        assert len(blocks) == 1
        assert blocks[0]["type"] == "tool_use"
        assert blocks[0]["id"] == "toolu_1"
        assert blocks[0]["name"] == "get_entity_state"
        assert blocks[0]["input"] == {"entity_id": "light.kitchen"}

    def test_multiple_canonical_tool_calls(self) -> None:
        adapter = AnthropicAdapter()
        content = build_assistant_tool_message(
            [
                {"id": "toolu_1", "name": "tool_a", "args": {"x": 1}},
                {"id": "toolu_2", "name": "tool_b", "args": {"y": 2}},
            ]
        )
        messages = [{"role": "assistant", "content": content}]
        converted, _ = adapter.transform_messages(messages)
        blocks = converted[0]["content"]
        assert len(blocks) == 2
        assert blocks[0]["id"] == "toolu_1"
        assert blocks[1]["id"] == "toolu_2"

    def test_plain_assistant_text_preserved(self) -> None:
        adapter = AnthropicAdapter()
        messages = [{"role": "assistant", "content": "Hello!"}]
        converted, _ = adapter.transform_messages(messages)
        assert converted[0]["content"] == "Hello!"

    def test_assistant_empty_content_dropped(self) -> None:
        adapter = AnthropicAdapter()
        messages = [{"role": "assistant", "content": ""}]
        converted, _ = adapter.transform_messages(messages)
        assert converted == []


class TestTransformMessagesImages:
    """User messages with _images → Anthropic image blocks."""

    def test_images_converted_to_image_blocks(self) -> None:
        adapter = AnthropicAdapter()
        messages = [
            {
                "role": "user",
                "content": "What's this?",
                "_images": [
                    {"mime_type": "image/jpeg", "data": "base64encodeddata"},
                ],
            }
        ]
        converted, _ = adapter.transform_messages(messages)
        assert len(converted) == 1
        blocks = converted[0]["content"]
        assert blocks[0] == {"type": "text", "text": "What's this?"}
        assert blocks[1] == {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": "base64encodeddata",
            },
        }

    def test_multiple_images(self) -> None:
        adapter = AnthropicAdapter()
        messages = [
            {
                "role": "user",
                "content": "Compare these",
                "_images": [
                    {"mime_type": "image/png", "data": "data1"},
                    {"mime_type": "image/png", "data": "data2"},
                ],
            }
        ]
        converted, _ = adapter.transform_messages(messages)
        blocks = converted[0]["content"]
        # text + 2 image blocks
        assert len(blocks) == 3
        assert blocks[0]["type"] == "text"
        assert blocks[1]["type"] == "image"
        assert blocks[2]["type"] == "image"


class TestTransformMessagesEmptyContent:
    """Empty content messages are dropped (except function role)."""

    def test_user_empty_content_dropped(self) -> None:
        adapter = AnthropicAdapter()
        messages = [{"role": "user", "content": ""}]
        converted, _ = adapter.transform_messages(messages)
        assert converted == []

    def test_system_empty_content_not_extracted(self) -> None:
        """Empty system content should produce None system, not empty string."""
        adapter = AnthropicAdapter()
        messages = [
            {"role": "system", "content": ""},
            {"role": "user", "content": "Hi"},
        ]
        converted, system = adapter.transform_messages(messages)
        # Empty system should be treated as absent
        assert system is None or system == ""
        assert len(converted) == 1


# ---------------------------------------------------------------------------
# extract_response
# ---------------------------------------------------------------------------


class TestExtractResponseText:
    """extract_response handles text-only responses."""

    def test_text_response(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [{"type": "text", "text": "Hello!"}],
            "stop_reason": "end_turn",
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "Hello!"
        assert result["finish_reason"] == "stop"

    def test_multiple_text_blocks_concatenated(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": " world"},
            ],
            "stop_reason": "end_turn",
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "Hello world"

    def test_empty_content_returns_text_empty(self) -> None:
        adapter = AnthropicAdapter()
        raw = {"content": [], "stop_reason": "end_turn"}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == ""


class TestExtractResponseToolCalls:
    """extract_response handles tool_use responses."""

    def test_single_tool_use(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "get_weather",
                    "input": {"location": "Warsaw"},
                }
            ],
            "stop_reason": "tool_use",
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["finish_reason"] == "tool_calls"
        assert len(result["tool_calls"]) == 1
        tc = result["tool_calls"][0]
        assert tc["id"] == "toolu_1"
        assert tc["name"] == "get_weather"
        assert tc["args"] == {"location": "Warsaw"}

    def test_multiple_tool_use_blocks(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "tool_a", "input": {"x": 1}},
                {"type": "tool_use", "id": "toolu_2", "name": "tool_b", "input": {"y": 2}},
            ],
            "stop_reason": "tool_use",
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert len(result["tool_calls"]) == 2

    def test_tool_use_with_text_block(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {"type": "text", "text": "Let me check."},
                {"type": "tool_use", "id": "toolu_1", "name": "check", "input": {}},
            ],
            "stop_reason": "tool_use",
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["text"] == "Let me check."

    def test_tool_use_no_text_gives_none_text(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "check", "input": {}},
            ],
            "stop_reason": "tool_use",
        }
        result = adapter.extract_response(raw)
        assert result["text"] is None


# ---------------------------------------------------------------------------
# extract_stream_events
# ---------------------------------------------------------------------------


class TestExtractStreamEventsText:
    """Text delta events produce text chunks."""

    def test_text_delta_produces_text_chunk(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()
        event = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Hello"},
        }
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == [{"type": "text", "content": "Hello"}]

    def test_empty_text_delta_produces_no_chunk(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()
        event = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": ""},
        }
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == []


class TestExtractStreamEventsToolUse:
    """Tool use flow: content_block_start → input_json_delta → message_stop."""

    def test_tool_use_flow(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()

        start = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {}},
        }
        delta = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "input_json_delta", "partial_json": '{"location":"Warsaw"}'},
        }
        stop = {"type": "message_stop"}

        assert adapter.extract_stream_events(start, acc) == []
        assert adapter.extract_stream_events(delta, acc) == []
        chunks = adapter.extract_stream_events(stop, acc)
        assert len(chunks) == 1
        tc = chunks[0]
        assert tc["type"] == "tool_call"
        assert tc["id"] == "toolu_1"
        assert tc["name"] == "get_weather"
        assert tc["args"] == {"location": "Warsaw"}

    def test_message_delta_also_flushes(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()

        acc.add_fragment(0, "toolu_x", "my_tool", '{"a":1}')
        event = {"type": "message_delta", "delta": {"stop_reason": "tool_use"}}
        chunks = adapter.extract_stream_events(event, acc)
        assert len(chunks) == 1
        assert chunks[0]["name"] == "my_tool"

    def test_incremental_json_fragments(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()

        start = {
            "type": "content_block_start",
            "index": 1,
            "content_block": {"type": "tool_use", "id": "toolu_2", "name": "do_it", "input": {}},
        }
        delta1 = {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '{"key"'},
        }
        delta2 = {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": ':"val"}'},
        }
        stop = {"type": "message_stop"}

        adapter.extract_stream_events(start, acc)
        adapter.extract_stream_events(delta1, acc)
        adapter.extract_stream_events(delta2, acc)
        chunks = adapter.extract_stream_events(stop, acc)
        assert chunks[0]["args"] == {"key": "val"}

    def test_no_flush_when_acc_empty_on_stop(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()
        stop = {"type": "message_stop"}
        chunks = adapter.extract_stream_events(stop, acc)
        assert chunks == []

    def test_non_tool_use_content_block_start_ignored(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()
        event = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text"},
        }
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == []
        assert not acc.has_pending

    def test_empty_start_input_does_not_break_delta_json(self) -> None:
        """Empty {} from content_block_start must not be serialized into args_buf."""
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()

        start = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "tool_use",
                "id": "toolu_3",
                "name": "entity_tool",
                "input": {},
            },
        }
        delta = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "input_json_delta", "partial_json": '{"entity_id":"switch.fan"}'},
        }
        stop = {"type": "message_stop"}

        adapter.extract_stream_events(start, acc)
        adapter.extract_stream_events(delta, acc)
        chunks = adapter.extract_stream_events(stop, acc)
        assert chunks[0]["args"] == {"entity_id": "switch.fan"}
