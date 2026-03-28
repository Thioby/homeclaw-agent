"""Tests for SSEParser and ToolAccumulator stream utilities."""

from __future__ import annotations

import pytest

from custom_components.homeclaw.providers.adapters.stream_utils import SSEParser, ToolAccumulator


class TestSSEParserBasic:
    """Basic SSEParser feed/flush behavior."""

    def test_single_event_in_one_chunk(self) -> None:
        parser = SSEParser()
        result = parser.feed("data: hello\n\n")
        assert result == ["hello"]

    def test_empty_chunk_returns_nothing(self) -> None:
        parser = SSEParser()
        assert parser.feed("") == []

    def test_non_data_lines_ignored(self) -> None:
        parser = SSEParser()
        result = parser.feed("event: message\nid: 1\nretry: 3000\ndata: payload\n\n")
        assert result == ["payload"]

    def test_multiple_events_in_one_chunk(self) -> None:
        parser = SSEParser()
        result = parser.feed("data: first\n\ndata: second\n\n")
        assert result == ["first", "second"]

    def test_done_sentinel_passed_through(self) -> None:
        parser = SSEParser()
        result = parser.feed("data: [DONE]\n\n")
        assert result == ["[DONE]"]

    def test_comment_lines_ignored(self) -> None:
        parser = SSEParser()
        result = parser.feed(": this is a comment\ndata: value\n\n")
        assert result == ["value"]


class TestSSEParserSplitChunks:
    """SSEParser handles events split across multiple chunks."""

    def test_event_split_across_two_chunks(self) -> None:
        parser = SSEParser()
        first = parser.feed("data: hel")
        assert first == []
        second = parser.feed("lo\n\n")
        assert second == ["hello"]

    def test_delimiter_split_across_chunks(self) -> None:
        """Event delimiter \\n\\n split: first chunk ends with \\n, second starts with \\n."""
        parser = SSEParser()
        first = parser.feed("data: msg\n")
        assert first == []
        second = parser.feed("\n")
        assert second == ["msg"]

    def test_multiple_events_split_across_chunks(self) -> None:
        parser = SSEParser()
        r1 = parser.feed("data: one\n\ndata: tw")
        assert r1 == ["one"]
        r2 = parser.feed("o\n\n")
        assert r2 == ["two"]


class TestSSEParserMultilineData:
    """SSEParser handles multiline data fields."""

    def test_multiline_data_concatenated_with_newline(self) -> None:
        parser = SSEParser()
        result = parser.feed("data: line1\ndata: line2\n\n")
        assert result == ["line1\nline2"]

    def test_multiline_data_split_across_chunks(self) -> None:
        parser = SSEParser()
        r1 = parser.feed("data: line1\n")
        assert r1 == []
        r2 = parser.feed("data: line2\n\n")
        assert r2 == ["line1\nline2"]


class TestSSEParserFlush:
    """SSEParser flush behavior."""

    def test_flush_empty_buffer_returns_empty(self) -> None:
        parser = SSEParser()
        assert parser.flush() == []

    def test_flush_incomplete_event_returns_it(self) -> None:
        """Remaining buffer content without trailing double-newline is flushed."""
        parser = SSEParser()
        parser.feed("data: partial")
        result = parser.flush()
        assert result == ["partial"]

    def test_flush_clears_buffer(self) -> None:
        parser = SSEParser()
        parser.feed("data: partial")
        parser.flush()
        assert parser.flush() == []

    def test_flush_after_complete_events_empty(self) -> None:
        parser = SSEParser()
        parser.feed("data: done\n\n")
        assert parser.flush() == []


class TestToolAccumulatorBasic:
    """Basic ToolAccumulator behavior."""

    def test_has_pending_false_initially(self) -> None:
        acc = ToolAccumulator()
        assert acc.has_pending is False

    def test_has_pending_true_after_fragment(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_1", "my_tool", "")
        assert acc.has_pending is True

    def test_flush_all_empty(self) -> None:
        acc = ToolAccumulator()
        assert acc.flush_all() == []

    def test_flush_clears_pending(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_1", "my_tool", "")
        acc.flush_all()
        assert acc.has_pending is False

    def test_single_tool_call_complete_args(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_1", "my_tool", '{"key": "value"}')
        result = acc.flush_all()
        assert result == [{"id": "call_1", "name": "my_tool", "args": {"key": "value"}}]

    def test_single_tool_call_empty_args(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_1", "my_tool", "")
        result = acc.flush_all()
        assert result == [{"id": "call_1", "name": "my_tool", "args": {}}]

    def test_malformed_json_args_returns_empty_dict(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_1", "my_tool", "{bad json")
        result = acc.flush_all()
        assert result == [{"id": "call_1", "name": "my_tool", "args": {}}]


class TestToolAccumulatorIncremental:
    """ToolAccumulator incremental args concatenation."""

    def test_incremental_args_concatenated(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_1", "my_tool", '{"ke')
        acc.add_fragment(0, None, None, 'y": 42}')
        result = acc.flush_all()
        assert result == [{"id": "call_1", "name": "my_tool", "args": {"key": 42}}]

    def test_incremental_multiple_fragments(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "c1", "tool_a", '{"a"')
        acc.add_fragment(0, None, None, ': 1,')
        acc.add_fragment(0, None, None, ' "b": 2}')
        result = acc.flush_all()
        assert result == [{"id": "c1", "name": "tool_a", "args": {"a": 1, "b": 2}}]

    def test_name_set_on_later_fragment(self) -> None:
        """If name arrives in a later fragment (after initial id), it should be used."""
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_x", None, "")
        acc.add_fragment(0, None, "late_name", '{"x": 1}')
        result = acc.flush_all()
        assert result == [{"id": "call_x", "name": "late_name", "args": {"x": 1}}]


class TestToolAccumulatorMultipleTools:
    """ToolAccumulator handles multiple parallel tool calls."""

    def test_two_parallel_tool_calls(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "call_a", "tool_a", '{"x": 1}')
        acc.add_fragment(1, "call_b", "tool_b", '{"y": 2}')
        result = acc.flush_all()
        assert len(result) == 2
        assert {"id": "call_a", "name": "tool_a", "args": {"x": 1}} in result
        assert {"id": "call_b", "name": "tool_b", "args": {"y": 2}} in result

    def test_interleaved_fragments_by_index(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "c0", "tool_0", '{"a"')
        acc.add_fragment(1, "c1", "tool_1", '{"b"')
        acc.add_fragment(0, None, None, ': 1}')
        acc.add_fragment(1, None, None, ': 2}')
        result = acc.flush_all()
        assert {"id": "c0", "name": "tool_0", "args": {"a": 1}} in result
        assert {"id": "c1", "name": "tool_1", "args": {"b": 2}} in result

    def test_flush_returns_in_index_order(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(1, "c1", "tool_1", "{}")
        acc.add_fragment(0, "c0", "tool_0", "{}")
        result = acc.flush_all()
        assert result[0]["id"] == "c0"
        assert result[1]["id"] == "c1"

    def test_second_flush_empty_after_first(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(0, "c0", "tool_0", "{}")
        acc.flush_all()
        assert acc.flush_all() == []
