"""Tests for OpenAICompatAdapter."""

from __future__ import annotations

import json

import pytest

from custom_components.homeclaw.providers.adapters.openai_compat import OpenAICompatAdapter
from custom_components.homeclaw.providers.adapters.stream_utils import ToolAccumulator


@pytest.fixture()
def adapter() -> OpenAICompatAdapter:
    return OpenAICompatAdapter()


# ---------------------------------------------------------------------------
# transform_tools
# ---------------------------------------------------------------------------


class TestTransformTools:
    """transform_tools is a passthrough — tools are already in OpenAI format."""

    def test_passthrough_single_tool(self, adapter: OpenAICompatAdapter) -> None:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "turn_on_light",
                    "description": "Turn on a light",
                    "parameters": {
                        "type": "object",
                        "properties": {"entity_id": {"type": "string"}},
                        "required": ["entity_id"],
                    },
                },
            }
        ]
        result = adapter.transform_tools(tools)
        assert result is tools

    def test_passthrough_empty_list(self, adapter: OpenAICompatAdapter) -> None:
        result = adapter.transform_tools([])
        assert result == []

    def test_passthrough_multiple_tools(self, adapter: OpenAICompatAdapter) -> None:
        tools = [
            {"type": "function", "function": {"name": "tool_a", "parameters": {}}},
            {"type": "function", "function": {"name": "tool_b", "parameters": {}}},
        ]
        result = adapter.transform_tools(tools)
        assert result is tools


# ---------------------------------------------------------------------------
# transform_messages
# ---------------------------------------------------------------------------


class TestTransformMessages:
    """transform_messages handles multimodal images and assistant tool-call JSON."""

    def test_simple_user_message_unchanged(self, adapter: OpenAICompatAdapter) -> None:
        messages = [{"role": "user", "content": "Hello"}]
        converted, system = adapter.transform_messages(messages)
        assert converted == [{"role": "user", "content": "Hello"}]
        assert system is None

    def test_returns_none_system(self, adapter: OpenAICompatAdapter) -> None:
        """OpenAI keeps system inline, so system_content is always None."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        _converted, system = adapter.transform_messages(messages)
        assert system is None

    def test_system_message_passes_through(self, adapter: OpenAICompatAdapter) -> None:
        messages = [{"role": "system", "content": "Be concise."}]
        converted, _ = adapter.transform_messages(messages)
        assert converted == [{"role": "system", "content": "Be concise."}]

    def test_images_converted_to_multimodal(self, adapter: OpenAICompatAdapter) -> None:
        messages = [
            {
                "role": "user",
                "content": "What is this?",
                "_images": [{"mime_type": "image/jpeg", "data": "abc123"}],
            }
        ]
        converted, _ = adapter.transform_messages(messages)
        assert len(converted) == 1
        msg = converted[0]
        assert msg["role"] == "user"
        assert isinstance(msg["content"], list)
        assert {"type": "text", "text": "What is this?"} in msg["content"]
        image_block = next(b for b in msg["content"] if b["type"] == "image_url")
        assert image_block["image_url"]["url"] == "data:image/jpeg;base64,abc123"
        assert image_block["image_url"]["detail"] == "auto"

    def test_images_multiple(self, adapter: OpenAICompatAdapter) -> None:
        messages = [
            {
                "role": "user",
                "content": "Compare these",
                "_images": [
                    {"mime_type": "image/png", "data": "img1"},
                    {"mime_type": "image/webp", "data": "img2"},
                ],
            }
        ]
        converted, _ = adapter.transform_messages(messages)
        content = converted[0]["content"]
        image_blocks = [b for b in content if b["type"] == "image_url"]
        assert len(image_blocks) == 2
        assert image_blocks[0]["image_url"]["url"] == "data:image/png;base64,img1"
        assert image_blocks[1]["image_url"]["url"] == "data:image/webp;base64,img2"

    def test_images_key_stripped(self, adapter: OpenAICompatAdapter) -> None:
        messages = [
            {
                "role": "user",
                "content": "Hi",
                "_images": [{"mime_type": "image/jpeg", "data": "x"}],
            }
        ]
        converted, _ = adapter.transform_messages(messages)
        assert "_images" not in converted[0]

    def test_images_key_stripped_when_no_images(self, adapter: OpenAICompatAdapter) -> None:
        """_images key should be stripped even from messages without images."""
        messages = [{"role": "user", "content": "Hi", "_images": []}]
        converted, _ = adapter.transform_messages(messages)
        assert "_images" not in converted[0]

    def test_assistant_tool_call_json_converted(self, adapter: OpenAICompatAdapter) -> None:
        tool_call_content = json.dumps(
            {
                "tool_calls": [
                    {"id": "call_1", "name": "get_state", "args": {"entity_id": "light.kitchen"}}
                ]
            }
        )
        messages = [{"role": "assistant", "content": tool_call_content}]
        converted, _ = adapter.transform_messages(messages)
        msg = converted[0]
        assert msg["role"] == "assistant"
        assert "tool_calls" in msg
        assert len(msg["tool_calls"]) == 1
        tc = msg["tool_calls"][0]
        assert tc["id"] == "call_1"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "get_state"
        assert json.loads(tc["function"]["arguments"]) == {"entity_id": "light.kitchen"}

    def test_assistant_tool_call_text_preserved(self, adapter: OpenAICompatAdapter) -> None:
        """Assistant content text is preserved alongside tool_calls."""
        tool_call_content = json.dumps(
            {
                "tool_calls": [
                    {"id": "call_2", "name": "do_thing", "args": {}}
                ]
            }
        )
        messages = [{"role": "assistant", "content": tool_call_content}]
        converted, _ = adapter.transform_messages(messages)
        # Content may be None or empty string (no text in the JSON payload itself)
        msg = converted[0]
        assert "tool_calls" in msg

    def test_assistant_multiple_tool_calls(self, adapter: OpenAICompatAdapter) -> None:
        tool_call_content = json.dumps(
            {
                "tool_calls": [
                    {"id": "c1", "name": "tool_a", "args": {"x": 1}},
                    {"id": "c2", "name": "tool_b", "args": {"y": 2}},
                ]
            }
        )
        messages = [{"role": "assistant", "content": tool_call_content}]
        converted, _ = adapter.transform_messages(messages)
        msg = converted[0]
        assert len(msg["tool_calls"]) == 2
        names = {tc["function"]["name"] for tc in msg["tool_calls"]}
        assert names == {"tool_a", "tool_b"}

    def test_assistant_plain_text_not_converted(self, adapter: OpenAICompatAdapter) -> None:
        messages = [{"role": "assistant", "content": "Sure, let me help."}]
        converted, _ = adapter.transform_messages(messages)
        assert converted == [{"role": "assistant", "content": "Sure, let me help."}]

    def test_assistant_non_json_content_not_converted(self, adapter: OpenAICompatAdapter) -> None:
        messages = [{"role": "assistant", "content": "{invalid json}"}]
        converted, _ = adapter.transform_messages(messages)
        assert converted == [{"role": "assistant", "content": "{invalid json}"}]

    def test_mixed_messages(self, adapter: OpenAICompatAdapter) -> None:
        tool_call_content = json.dumps(
            {"tool_calls": [{"id": "c1", "name": "act", "args": {}}]}
        )
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello", "_images": [{"mime_type": "image/jpeg", "data": "d1"}]},
            {"role": "assistant", "content": tool_call_content},
            {"role": "user", "content": "Done"},
        ]
        converted, system = adapter.transform_messages(messages)
        assert system is None
        assert len(converted) == 4
        # system passes through
        assert converted[0] == {"role": "system", "content": "System prompt"}
        # user with image → multimodal, _images stripped
        assert isinstance(converted[1]["content"], list)
        assert "_images" not in converted[1]
        # assistant → tool_calls
        assert "tool_calls" in converted[2]
        # plain user unchanged
        assert converted[3] == {"role": "user", "content": "Done"}


# ---------------------------------------------------------------------------
# extract_response
# ---------------------------------------------------------------------------


class TestExtractResponse:
    """extract_response parses raw OpenAI API response."""

    def test_text_response(self, adapter: OpenAICompatAdapter) -> None:
        raw = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello there!"},
                    "finish_reason": "stop",
                }
            ]
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "Hello there!"
        assert result["finish_reason"] == "stop"

    def test_text_response_null_content(self, adapter: OpenAICompatAdapter) -> None:
        raw = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": None},
                    "finish_reason": "stop",
                }
            ]
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == ""

    def test_tool_call_response(self, adapter: OpenAICompatAdapter) -> None:
        raw = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "turn_on_light",
                                    "arguments": '{"entity_id": "light.living_room"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["finish_reason"] == "tool_calls"
        assert len(result["tool_calls"]) == 1
        tc = result["tool_calls"][0]
        assert tc["id"] == "call_abc"
        assert tc["name"] == "turn_on_light"
        assert tc["args"] == {"entity_id": "light.living_room"}

    def test_tool_call_arguments_parsed_from_string(self, adapter: OpenAICompatAdapter) -> None:
        """function.arguments is a JSON string — it must be parsed to dict."""
        raw = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_x",
                                "type": "function",
                                "function": {
                                    "name": "set_temp",
                                    "arguments": '{"temperature": 22, "unit": "celsius"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
        result = adapter.extract_response(raw)
        assert result["tool_calls"][0]["args"] == {"temperature": 22, "unit": "celsius"}

    def test_tool_call_text_alongside(self, adapter: OpenAICompatAdapter) -> None:
        """text field carries any content alongside tool calls."""
        raw = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Let me check that.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "check", "arguments": "{}"},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["text"] == "Let me check that."

    def test_multiple_tool_calls(self, adapter: OpenAICompatAdapter) -> None:
        raw = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {"name": "tool_a", "arguments": '{"a": 1}'},
                            },
                            {
                                "id": "c2",
                                "type": "function",
                                "function": {"name": "tool_b", "arguments": '{"b": 2}'},
                            },
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
        result = adapter.extract_response(raw)
        assert len(result["tool_calls"]) == 2
        assert result["tool_calls"][0]["name"] == "tool_a"
        assert result["tool_calls"][1]["name"] == "tool_b"

    def test_empty_choices_raises_or_returns_error(self, adapter: OpenAICompatAdapter) -> None:
        """Empty choices should not crash — return a graceful text response."""
        raw = {"choices": []}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == ""


# ---------------------------------------------------------------------------
# extract_stream_events
# ---------------------------------------------------------------------------


class TestExtractStreamEvents:
    """extract_stream_events normalizes SSE event data."""

    def test_text_delta(self, adapter: OpenAICompatAdapter) -> None:
        event = {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]}
        acc = ToolAccumulator()
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == [{"type": "text", "content": "Hello"}]

    def test_empty_text_delta_skipped(self, adapter: OpenAICompatAdapter) -> None:
        event = {"choices": [{"delta": {"content": ""}, "finish_reason": None}]}
        acc = ToolAccumulator()
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == []

    def test_null_content_skipped(self, adapter: OpenAICompatAdapter) -> None:
        event = {"choices": [{"delta": {"content": None}, "finish_reason": None}]}
        acc = ToolAccumulator()
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == []

    def test_tool_call_fragment_accumulates(self, adapter: OpenAICompatAdapter) -> None:
        event = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {"name": "lights_on", "arguments": ""},
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        }
        acc = ToolAccumulator()
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == []
        assert acc.has_pending is True

    def test_finish_reason_flushes_tool_acc(self, adapter: OpenAICompatAdapter) -> None:
        acc = ToolAccumulator()

        # Feed start fragment
        ev1 = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {"name": "turn_on", "arguments": ""},
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        }
        adapter.extract_stream_events(ev1, acc)

        # Feed args fragment
        ev2 = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {"arguments": '{"room": "kitchen"}'},
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        }
        adapter.extract_stream_events(ev2, acc)

        # Finish
        ev3 = {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        chunks = adapter.extract_stream_events(ev3, acc)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "tool_call"
        assert chunks[0]["id"] == "call_1"
        assert chunks[0]["name"] == "turn_on"
        assert chunks[0]["args"] == {"room": "kitchen"}
        assert acc.has_pending is False

    def test_incremental_args_concatenated(self, adapter: OpenAICompatAdapter) -> None:
        acc = ToolAccumulator()

        events = [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {"index": 0, "id": "c1", "function": {"name": "f", "arguments": '{"k'}}
                            ]
                        },
                        "finish_reason": None,
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {"index": 0, "function": {"arguments": 'ey": 42}'}}
                            ]
                        },
                        "finish_reason": None,
                    }
                ]
            },
            {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        ]

        chunks = []
        for ev in events:
            chunks.extend(adapter.extract_stream_events(ev, acc))

        assert len(chunks) == 1
        assert chunks[0]["args"] == {"key": 42}

    def test_parallel_tool_calls(self, adapter: OpenAICompatAdapter) -> None:
        acc = ToolAccumulator()

        ev1 = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {"index": 0, "id": "c0", "function": {"name": "tool_a", "arguments": '{"x":1}'}},
                            {"index": 1, "id": "c1", "function": {"name": "tool_b", "arguments": '{"y":2}'}},
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        }
        adapter.extract_stream_events(ev1, acc)

        ev2 = {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        chunks = adapter.extract_stream_events(ev2, acc)

        assert len(chunks) == 2
        names = {c["name"] for c in chunks}
        assert names == {"tool_a", "tool_b"}

    def test_empty_choices_no_crash(self, adapter: OpenAICompatAdapter) -> None:
        acc = ToolAccumulator()
        chunks = adapter.extract_stream_events({"choices": []}, acc)
        assert chunks == []

    def test_finish_reason_stop_no_pending(self, adapter: OpenAICompatAdapter) -> None:
        """finish_reason=stop with no pending tools emits no extra chunks."""
        acc = ToolAccumulator()
        ev = {"choices": [{"delta": {}, "finish_reason": "stop"}]}
        chunks = adapter.extract_stream_events(ev, acc)
        assert chunks == []

    def test_finish_reason_stop_with_pending_flushes(self, adapter: OpenAICompatAdapter) -> None:
        """Any non-None finish_reason with pending tools flushes them."""
        acc = ToolAccumulator()
        acc.add_fragment(0, "c1", "act", '{"z": 9}')

        ev = {"choices": [{"delta": {}, "finish_reason": "stop"}]}
        chunks = adapter.extract_stream_events(ev, acc)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "tool_call"
        assert chunks[0]["name"] == "act"
