"""Tests for GeminiAdapter."""

from __future__ import annotations

import json

import pytest

from custom_components.homeclaw.providers.adapters.gemini_adapter import GeminiAdapter


@pytest.fixture()
def adapter() -> GeminiAdapter:
    return GeminiAdapter()


# ---------------------------------------------------------------------------
# transform_tools
# ---------------------------------------------------------------------------


class TestTransformTools:
    def test_converts_to_function_declarations(self, adapter: GeminiAdapter) -> None:
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        result = adapter.transform_tools(openai_tools)
        assert result == [
            {
                "functionDeclarations": [
                    {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    }
                ]
            }
        ]

    def test_empty_list_returns_empty(self, adapter: GeminiAdapter) -> None:
        assert adapter.transform_tools([]) == []

    def test_multiple_tools(self, adapter: GeminiAdapter) -> None:
        openai_tools = [
            {"type": "function", "function": {"name": "tool_a", "description": "A", "parameters": {}}},
            {"type": "function", "function": {"name": "tool_b", "description": "B", "parameters": {}}},
        ]
        result = adapter.transform_tools(openai_tools)
        assert len(result) == 1
        assert len(result[0]["functionDeclarations"]) == 2
        names = [d["name"] for d in result[0]["functionDeclarations"]]
        assert names == ["tool_a", "tool_b"]


# ---------------------------------------------------------------------------
# transform_messages
# ---------------------------------------------------------------------------


class TestTransformMessages:
    def test_system_message_extracted(self, adapter: GeminiAdapter) -> None:
        messages = [{"role": "system", "content": "You are helpful."}]
        contents, system = adapter.transform_messages(messages)
        assert system == "You are helpful."
        assert contents == []

    def test_user_message_to_user_with_parts(self, adapter: GeminiAdapter) -> None:
        messages = [{"role": "user", "content": "Hello"}]
        contents, system = adapter.transform_messages(messages)
        assert system is None
        assert contents == [{"role": "user", "parts": [{"text": "Hello"}]}]

    def test_assistant_text_becomes_model_role(self, adapter: GeminiAdapter) -> None:
        messages = [{"role": "assistant", "content": "Hi there"}]
        contents, system = adapter.transform_messages(messages)
        assert contents == [{"role": "model", "parts": [{"text": "Hi there"}]}]

    def test_function_result_becomes_function_response(self, adapter: GeminiAdapter) -> None:
        messages = [
            {"role": "user", "content": "call a tool"},
            {"role": "function", "name": "my_func", "content": json.dumps({"result": "ok"})},
        ]
        contents, system = adapter.transform_messages(messages)
        func_turn = contents[-1]
        assert func_turn["role"] == "user"
        assert func_turn["parts"] == [
            {"functionResponse": {"name": "my_func", "response": {"result": "ok"}}}
        ]

    def test_images_added_as_inline_data(self, adapter: GeminiAdapter) -> None:
        messages = [
            {
                "role": "user",
                "content": "What is this?",
                "_images": [{"mime_type": "image/png", "data": "base64data"}],
            }
        ]
        contents, _ = adapter.transform_messages(messages)
        parts = contents[0]["parts"]
        assert parts[0] == {"text": "What is this?"}
        assert parts[1] == {"inlineData": {"mimeType": "image/png", "data": "base64data"}}

    def test_assistant_with_tool_call_becomes_function_call_parts(self, adapter: GeminiAdapter) -> None:
        """Assistant message carrying a JSON-encoded tool call is converted to functionCall parts."""
        tool_call_content = json.dumps(
            {
                "tool_calls": [
                    {"id": "gemini_my_tool", "name": "my_tool", "args": {"x": 1}}
                ]
            }
        )
        messages = [
            {"role": "user", "content": "do something"},
            {"role": "assistant", "content": tool_call_content},
        ]
        contents, _ = adapter.transform_messages(messages)
        model_turn = contents[-1]
        assert model_turn["role"] == "model"
        fc_part = model_turn["parts"][0]
        assert "functionCall" in fc_part
        assert fc_part["functionCall"]["name"] == "my_tool"
        assert fc_part["functionCall"]["args"] == {"x": 1}


# ---------------------------------------------------------------------------
# extract_response
# ---------------------------------------------------------------------------


class TestExtractResponse:
    def _make_response(self, parts: list[dict], finish_reason: str = "STOP") -> dict:
        return {
            "candidates": [
                {
                    "content": {"parts": parts, "role": "model"},
                    "finishReason": finish_reason,
                }
            ]
        }

    def test_text_response(self, adapter: GeminiAdapter) -> None:
        raw = self._make_response([{"text": "Hello world"}])
        result = adapter.extract_response(raw)
        assert result == {"type": "text", "content": "Hello world", "finish_reason": "stop"}

    def test_function_call_response(self, adapter: GeminiAdapter) -> None:
        raw = self._make_response(
            [{"functionCall": {"name": "get_weather", "args": {"city": "Paris"}}}],
            finish_reason="FUNCTION_CALL",
        )
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["finish_reason"] == "tool_calls"
        assert result["text"] is None
        tool_calls = result["tool_calls"]
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "gemini_get_weather"
        assert tool_calls[0]["name"] == "get_weather"
        assert tool_calls[0]["args"] == {"city": "Paris"}

    def test_thought_signature_preserved_on_tool_call(self, adapter: GeminiAdapter) -> None:
        raw = self._make_response(
            [
                {
                    "functionCall": {"name": "my_tool", "args": {}},
                    "thoughtSignature": "sig123",
                }
            ]
        )
        result = adapter.extract_response(raw)
        tc = result["tool_calls"][0]
        assert tc.get("thought_signature") == "sig123"

    def test_raw_function_call_preserved_on_tool_call(self, adapter: GeminiAdapter) -> None:
        part = {"functionCall": {"name": "my_tool", "args": {"k": "v"}}, "thoughtSignature": "abc"}
        raw = self._make_response([part])
        result = adapter.extract_response(raw)
        tc = result["tool_calls"][0]
        assert tc.get("_raw_function_call") == part

    def test_thinking_parts_skipped(self, adapter: GeminiAdapter) -> None:
        raw = self._make_response(
            [
                {"thought": True, "text": "internal reasoning"},
                {"text": "final answer"},
            ]
        )
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "final answer"

    def test_text_concatenated_across_parts(self, adapter: GeminiAdapter) -> None:
        raw = self._make_response([{"text": "Hello "}, {"text": "world"}])
        result = adapter.extract_response(raw)
        assert result["content"] == "Hello world"

    def test_empty_candidates_returns_empty_text(self, adapter: GeminiAdapter) -> None:
        raw = {"candidates": []}
        result = adapter.extract_response(raw)
        assert result == {"type": "text", "content": "", "finish_reason": "stop"}

    def test_tool_call_with_accompanying_text(self, adapter: GeminiAdapter) -> None:
        raw = self._make_response(
            [
                {"text": "Sure, let me call that."},
                {"functionCall": {"name": "do_thing", "args": {}}},
            ]
        )
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["text"] == "Sure, let me call that."


# ---------------------------------------------------------------------------
# extract_stream_events
# ---------------------------------------------------------------------------


class TestExtractStreamEvents:
    def _make_chunk(self, parts: list[dict]) -> dict:
        return {"candidates": [{"content": {"parts": parts, "role": "model"}}]}

    def test_text_chunk(self, adapter: GeminiAdapter) -> None:
        chunk = self._make_chunk([{"text": "streaming text"}])
        result = adapter.extract_stream_events(chunk, tool_acc=None)
        assert result == [{"type": "text", "content": "streaming text"}]

    def test_tool_call_chunk(self, adapter: GeminiAdapter) -> None:
        part = {"functionCall": {"name": "search", "args": {"q": "foo"}}}
        chunk = self._make_chunk([part])
        result = adapter.extract_stream_events(chunk, tool_acc=None)
        assert len(result) == 1
        ev = result[0]
        assert ev["type"] == "tool_call"
        assert ev["name"] == "search"
        assert ev["args"] == {"q": "foo"}

    def test_tool_call_with_thought_signature(self, adapter: GeminiAdapter) -> None:
        part = {
            "functionCall": {"name": "act", "args": {}},
            "thoughtSignature": "ts_abc",
        }
        chunk = self._make_chunk([part])
        result = adapter.extract_stream_events(chunk, tool_acc=None)
        ev = result[0]
        assert ev.get("thought_signature") == "ts_abc"

    def test_tool_call_with_raw_function_call(self, adapter: GeminiAdapter) -> None:
        part = {"functionCall": {"name": "act", "args": {}}, "thoughtSignature": "ts_abc"}
        chunk = self._make_chunk([part])
        result = adapter.extract_stream_events(chunk, tool_acc=None)
        ev = result[0]
        assert ev.get("_raw_function_call") == part

    def test_thinking_parts_skipped(self, adapter: GeminiAdapter) -> None:
        chunk = self._make_chunk(
            [
                {"thought": True, "text": "thinking..."},
                {"text": "real output"},
            ]
        )
        result = adapter.extract_stream_events(chunk, tool_acc=None)
        assert result == [{"type": "text", "content": "real output"}]

    def test_tool_acc_unused_but_accepted(self, adapter: GeminiAdapter) -> None:
        """tool_acc param must be accepted without error even if unused."""
        from custom_components.homeclaw.providers.adapters.stream_utils import ToolAccumulator

        acc = ToolAccumulator()
        chunk = self._make_chunk([{"text": "hi"}])
        result = adapter.extract_stream_events(chunk, tool_acc=acc)
        assert result == [{"type": "text", "content": "hi"}]
