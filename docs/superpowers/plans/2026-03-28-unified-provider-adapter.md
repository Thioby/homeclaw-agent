# Unified Provider Adapter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract provider-specific format conversion into a shared adapter layer so the core only deals with one canonical format (OpenAI), eliminating per-provider tool use hacks.

**Architecture:** Each provider gets an adapter that converts OpenAI-format messages/tools/responses to/from the provider's native format. Shared utilities handle SSE parsing and tool call accumulation. Providers delegate all format work to adapters, keeping only auth and HTTP logic.

**Tech Stack:** Python 3.12+, aiohttp, pytest, Home Assistant framework

---

### File Structure

**New files:**
- `providers/adapters/__init__.py` — package init
- `providers/adapters/base.py` — `ProviderAdapter` ABC
- `providers/adapters/openai_compat.py` — adapter for OpenAI/Groq/OpenRouter/z.ai/Xiaomi/Llama
- `providers/adapters/anthropic_adapter.py` — adapter for Anthropic (API key + OAuth)
- `providers/adapters/gemini_adapter.py` — adapter for Gemini (API key + OAuth)
- `providers/adapters/stream_utils.py` — `SSEParser` + `ToolAccumulator` utilities
- `tests/test_providers/test_adapters/__init__.py`
- `tests/test_providers/test_adapters/test_openai_compat.py`
- `tests/test_providers/test_adapters/test_anthropic_adapter.py`
- `tests/test_providers/test_adapters/test_gemini_adapter.py`
- `tests/test_providers/test_adapters/test_stream_utils.py`

**Modified files:**
- `providers/openai.py` — delegate format conversion to adapter
- `providers/anthropic.py` — delegate format conversion to adapter
- `providers/anthropic_oauth.py` — use shared adapter, remove duplication
- `providers/gemini.py` — delegate format conversion to adapter
- `providers/gemini_oauth.py` — use shared adapter for format conversion
- `providers/local.py` — minor: use adapter for message cleanup
- `function_calling.py` — remove `to_anthropic_format()`, `to_gemini_format()`; keep `to_openai_format()`
- `core/function_call_parser.py` — simplify to canonical-only parsing
- `core/tool_call_codec.py` — simplify to canonical-only format
- `core/context_builder.py` — simplify `repair_tool_history()` to canonical format

---

### Task 1: Shared stream utilities — SSEParser + ToolAccumulator

**Files:**
- Create: `custom_components/homeclaw/providers/adapters/__init__.py`
- Create: `custom_components/homeclaw/providers/adapters/stream_utils.py`
- Test: `tests/test_providers/test_adapters/__init__.py`
- Test: `tests/test_providers/test_adapters/test_stream_utils.py`

- [ ] **Step 1: Write failing tests for SSEParser**

```python
"""Tests for stream_utils — SSEParser and ToolAccumulator."""
from __future__ import annotations

from custom_components.homeclaw.providers.adapters.stream_utils import (
    SSEParser,
    ToolAccumulator,
)


class TestSSEParser:
    """Tests for SSE event parsing."""

    def test_single_complete_event(self) -> None:
        parser = SSEParser()
        events = parser.feed("data: {\"id\": 1}\n\n")
        assert events == ["{\"id\": 1}"]

    def test_split_across_chunks(self) -> None:
        parser = SSEParser()
        assert parser.feed("data: {\"id\"") == []
        assert parser.feed(": 1}\n\n") == ["{\"id\": 1}"]

    def test_multiple_events_in_one_chunk(self) -> None:
        parser = SSEParser()
        events = parser.feed("data: {\"a\": 1}\n\ndata: {\"b\": 2}\n\n")
        assert events == ["{\"a\": 1}", "{\"b\": 2}"]

    def test_done_sentinel(self) -> None:
        parser = SSEParser()
        events = parser.feed("data: [DONE]\n\n")
        assert events == ["[DONE]"]

    def test_ignores_non_data_lines(self) -> None:
        parser = SSEParser()
        events = parser.feed("event: ping\ndata: {\"ok\": true}\n\n")
        assert events == ["{\"ok\": true}"]

    def test_multiline_data(self) -> None:
        parser = SSEParser()
        events = parser.feed("data: line1\ndata: line2\n\n")
        assert events == ["line1\nline2"]

    def test_flush_returns_remaining(self) -> None:
        parser = SSEParser()
        parser.feed("data: {\"partial\": true}")
        events = parser.flush()
        assert events == ["{\"partial\": true}"]

    def test_flush_empty_when_no_buffer(self) -> None:
        parser = SSEParser()
        assert parser.flush() == []


class TestToolAccumulator:
    """Tests for streaming tool call accumulation."""

    def test_single_complete_tool_call(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(index=0, id="call_1", name="ha_control", args_delta="{\"entity_id\": \"light.bedroom\"}")
        result = acc.flush_all()
        assert len(result) == 1
        assert result[0] == {"id": "call_1", "name": "ha_control", "args": {"entity_id": "light.bedroom"}}

    def test_incremental_args_accumulation(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(index=0, id="call_1", name="ha_control", args_delta="{\"entity")
        acc.add_fragment(index=0, id=None, name=None, args_delta="_id\": \"light.bedroom\"}")
        result = acc.flush_all()
        assert result[0]["args"] == {"entity_id": "light.bedroom"}

    def test_multiple_parallel_tool_calls(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(index=0, id="call_1", name="tool_a", args_delta="{}")
        acc.add_fragment(index=1, id="call_2", name="tool_b", args_delta="{}")
        result = acc.flush_all()
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"

    def test_flush_all_clears_state(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(index=0, id="call_1", name="tool_a", args_delta="{}")
        acc.flush_all()
        assert acc.flush_all() == []

    def test_malformed_json_args(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(index=0, id="call_1", name="tool_a", args_delta="not json")
        result = acc.flush_all()
        assert result[0]["args"] == {}

    def test_empty_args(self) -> None:
        acc = ToolAccumulator()
        acc.add_fragment(index=0, id="call_1", name="tool_a", args_delta="")
        result = acc.flush_all()
        assert result[0]["args"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_stream_utils.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement SSEParser and ToolAccumulator**

```python
"""Shared streaming utilities for provider adapters.

SSEParser: Parse Server-Sent Events from raw text chunks.
ToolAccumulator: Accumulate partial tool call fragments across streaming chunks.
"""
from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class SSEParser:
    """Parse Server-Sent Events from raw text chunks.

    Handles buffering across chunk boundaries and extracts data lines.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> list[str]:
        """Feed raw text, return list of complete event data strings."""
        self._buffer += chunk
        events: list[str] = []

        while "\n\n" in self._buffer:
            raw_event, self._buffer = self._buffer.split("\n\n", 1)
            if not raw_event.strip():
                continue

            data_lines: list[str] = []
            for line in raw_event.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].strip())

            if data_lines:
                events.append("\n".join(data_lines))

        return events

    def flush(self) -> list[str]:
        """Flush remaining buffer content as events."""
        if not self._buffer.strip():
            self._buffer = ""
            return []

        events: list[str] = []
        for raw_event in self._buffer.strip().split("\n\n"):
            data_lines = [
                line[5:].strip()
                for line in raw_event.splitlines()
                if line.startswith("data:")
            ]
            if data_lines:
                events.append("\n".join(data_lines))

        self._buffer = ""
        return events


class ToolAccumulator:
    """Accumulate partial tool call fragments across streaming chunks.

    Tool calls arrive incrementally in streaming responses. This class
    collects fragments by index and produces complete tool calls when flushed.
    """

    def __init__(self) -> None:
        self._pending: dict[int, dict[str, Any]] = {}

    def add_fragment(
        self,
        index: int,
        id: str | None,
        name: str | None,
        args_delta: str,
    ) -> None:
        """Add a fragment for a tool call at the given index."""
        if index not in self._pending:
            self._pending[index] = {"id": id or "", "name": name or "", "arguments": ""}
        else:
            if id:
                self._pending[index]["id"] = id
            if name:
                self._pending[index]["name"] = name

        if args_delta:
            self._pending[index]["arguments"] += args_delta

    def flush_all(self) -> list[dict[str, Any]]:
        """Flush all pending tool calls. Returns list of {id, name, args}."""
        result: list[dict[str, Any]] = []
        for idx in sorted(self._pending):
            tool = self._pending[idx]
            args: dict[str, Any] = {}
            if tool["arguments"]:
                try:
                    args = json.loads(tool["arguments"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    _LOGGER.warning("Failed to parse tool args for %s", tool["name"])
            result.append({"id": tool["id"], "name": tool["name"], "args": args})
        self._pending.clear()
        return result

    @property
    def has_pending(self) -> bool:
        """Return True if there are pending tool calls."""
        return bool(self._pending)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_stream_utils.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/providers/adapters/__init__.py custom_components/homeclaw/providers/adapters/stream_utils.py tests/test_providers/test_adapters/__init__.py tests/test_providers/test_adapters/test_stream_utils.py
git commit -m "add SSEParser and ToolAccumulator stream utilities"
```

---

### Task 2: ProviderAdapter base class

**Files:**
- Create: `custom_components/homeclaw/providers/adapters/base.py`

- [ ] **Step 1: Write ProviderAdapter ABC**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/homeclaw/providers/adapters/base.py
git commit -m "add ProviderAdapter base class"
```

---

### Task 3: OpenAI-compatible adapter

**Files:**
- Create: `custom_components/homeclaw/providers/adapters/openai_compat.py`
- Test: `tests/test_providers/test_adapters/test_openai_compat.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for OpenAI-compatible adapter."""
from __future__ import annotations

import json

from custom_components.homeclaw.providers.adapters.openai_compat import OpenAICompatAdapter
from custom_components.homeclaw.providers.adapters.stream_utils import ToolAccumulator


class TestTransformTools:
    def test_passthrough(self) -> None:
        adapter = OpenAICompatAdapter()
        tools = [{"type": "function", "function": {"name": "test", "parameters": {}}}]
        assert adapter.transform_tools(tools) == tools

    def test_empty(self) -> None:
        adapter = OpenAICompatAdapter()
        assert adapter.transform_tools([]) == []


class TestTransformMessages:
    def test_simple_messages(self) -> None:
        adapter = OpenAICompatAdapter()
        msgs = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
        ]
        result, system = adapter.transform_messages(msgs)
        assert system is None  # OpenAI keeps system inline
        assert len(result) == 2

    def test_images_converted_to_multimodal(self) -> None:
        adapter = OpenAICompatAdapter()
        msgs = [
            {
                "role": "user",
                "content": "What's this?",
                "_images": [{"mime_type": "image/png", "data": "abc123"}],
            }
        ]
        result, _ = adapter.transform_messages(msgs)
        content = result[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"
        assert "data:image/png;base64,abc123" in content[1]["image_url"]["url"]

    def test_assistant_tool_call_json_converted(self) -> None:
        adapter = OpenAICompatAdapter()
        tool_json = json.dumps({
            "tool_calls": [{"id": "call_1", "name": "test_tool", "args": {"x": 1}}],
            "tool_use": {"id": "call_1", "name": "test_tool", "input": {"x": 1}},
        })
        msgs = [{"role": "assistant", "content": tool_json}]
        result, _ = adapter.transform_messages(msgs)
        msg = result[0]
        assert msg["role"] == "assistant"
        assert "tool_calls" in msg
        assert msg["tool_calls"][0]["function"]["name"] == "test_tool"


class TestExtractResponse:
    def test_text_response(self) -> None:
        adapter = OpenAICompatAdapter()
        raw = {"choices": [{"message": {"content": "Hello!", "role": "assistant"}}]}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "Hello!"

    def test_tool_call_response(self) -> None:
        adapter = OpenAICompatAdapter()
        raw = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "ha_control", "arguments": "{\"entity_id\": \"light.bedroom\"}"},
                    }],
                },
                "finish_reason": "tool_calls",
            }]
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["tool_calls"][0]["name"] == "ha_control"
        assert result["tool_calls"][0]["args"] == {"entity_id": "light.bedroom"}

    def test_empty_response(self) -> None:
        adapter = OpenAICompatAdapter()
        raw = {"choices": []}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == ""


class TestExtractStreamEvents:
    def test_text_delta(self) -> None:
        adapter = OpenAICompatAdapter()
        acc = ToolAccumulator()
        event = {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]}
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == [{"type": "text", "content": "Hello"}]

    def test_tool_call_deltas_accumulated(self) -> None:
        adapter = OpenAICompatAdapter()
        acc = ToolAccumulator()
        # First delta: tool call start
        event1 = {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "test", "arguments": "{\"x\""}}]}, "finish_reason": None}]}
        chunks1 = adapter.extract_stream_events(event1, acc)
        assert chunks1 == []  # no text, tool not yet complete

        # Second delta: more args
        event2 = {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ": 1}"}}]}, "finish_reason": None}]}
        chunks2 = adapter.extract_stream_events(event2, acc)
        assert chunks2 == []

        # Finish reason triggers flush
        event3 = {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        chunks3 = adapter.extract_stream_events(event3, acc)
        assert len(chunks3) == 1
        assert chunks3[0]["type"] == "tool_call"
        assert chunks3[0]["name"] == "test"
        assert chunks3[0]["args"] == {"x": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_openai_compat.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement OpenAICompatAdapter**

```python
"""OpenAI-compatible adapter — used by OpenAI, Groq, OpenRouter, z.ai, Xiaomi, Llama."""
from __future__ import annotations

import json
import logging
from typing import Any

from ...core.tool_call_codec import extract_tool_calls_from_assistant_content
from .base import ProviderAdapter
from .stream_utils import ToolAccumulator

_LOGGER = logging.getLogger(__name__)


class OpenAICompatAdapter(ProviderAdapter):
    """Adapter for OpenAI-compatible APIs.

    Tools and messages are mostly passthrough. Handles:
    - _images -> multimodal content blocks
    - Canonical assistant tool-call JSON -> OpenAI tool_calls format
    - Response parsing from choices[0].message
    - Streaming SSE event normalization
    """

    def transform_tools(self, openai_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return openai_tools

    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], None]:
        """Convert messages. OpenAI keeps system inline, so system is always None."""
        converted: list[dict[str, Any]] = []
        for msg in messages:
            images = msg.get("_images")
            if images and msg.get("role") == "user":
                content_blocks: list[dict[str, Any]] = [
                    {"type": "text", "text": msg.get("content", "")},
                ]
                for img in images:
                    data_url = f"data:{img['mime_type']};base64,{img['data']}"
                    content_blocks.append(
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}}
                    )
                converted.append({"role": "user", "content": content_blocks})
            else:
                clean = {k: v for k, v in msg.items() if k != "_images"}

                if (
                    clean.get("role") == "assistant"
                    and isinstance(clean.get("content"), str)
                    and clean.get("content")
                ):
                    try:
                        parsed_content = json.loads(clean["content"])
                        if isinstance(parsed_content, dict):
                            calls = extract_tool_calls_from_assistant_content(parsed_content)
                            if calls:
                                clean = {
                                    "role": "assistant",
                                    "content": parsed_content.get("text", ""),
                                    "tool_calls": [
                                        {
                                            "id": call.get("id", ""),
                                            "type": "function",
                                            "function": {
                                                "name": call.get("name", ""),
                                                "arguments": json.dumps(call.get("args", {})),
                                            },
                                        }
                                        for call in calls
                                    ],
                                }
                    except (TypeError, ValueError, json.JSONDecodeError):
                        pass

                converted.append(clean)
        return converted, None

    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        choices = raw_response.get("choices", [])
        if not choices:
            return {"type": "text", "content": "", "finish_reason": "stop"}

        choice = choices[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "stop")

        tool_calls = message.get("tool_calls")
        if tool_calls:
            parsed_calls: list[dict[str, Any]] = []
            for tc in tool_calls:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except (json.JSONDecodeError, TypeError, ValueError):
                    args = {}
                parsed_calls.append({
                    "id": tc.get("id", ""),
                    "name": func.get("name", ""),
                    "args": args,
                })
            return {
                "type": "tool_calls",
                "tool_calls": parsed_calls,
                "text": message.get("content"),
                "finish_reason": "tool_calls",
            }

        content = message.get("content")
        return {"type": "text", "content": content or "", "finish_reason": finish_reason or "stop"}

    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: ToolAccumulator
    ) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        choices = event_data.get("choices", [])
        if not choices:
            return output

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        content = delta.get("content")
        if content:
            output.append({"type": "text", "content": content})

        tool_calls = delta.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                tool_acc.add_fragment(
                    index=tc.get("index", 0),
                    id=tc.get("id"),
                    name=tc.get("function", {}).get("name"),
                    args_delta=tc.get("function", {}).get("arguments", ""),
                )

        if finish_reason is not None and tool_acc.has_pending:
            for tool in tool_acc.flush_all():
                output.append({"type": "tool_call", **tool})

        return output
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_openai_compat.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/providers/adapters/openai_compat.py tests/test_providers/test_adapters/test_openai_compat.py
git commit -m "add OpenAI-compatible adapter"
```

---

### Task 4: Anthropic adapter

**Files:**
- Create: `custom_components/homeclaw/providers/adapters/anthropic_adapter.py`
- Test: `tests/test_providers/test_adapters/test_anthropic_adapter.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for Anthropic adapter."""
from __future__ import annotations

import json

from custom_components.homeclaw.providers.adapters.anthropic_adapter import AnthropicAdapter
from custom_components.homeclaw.providers.adapters.stream_utils import ToolAccumulator


class TestTransformTools:
    def test_converts_openai_to_anthropic(self) -> None:
        adapter = AnthropicAdapter()
        tools = [
            {"type": "function", "function": {"name": "test", "description": "A test", "parameters": {"type": "object", "properties": {"x": {"type": "string"}}}}}
        ]
        result = adapter.transform_tools(tools)
        assert result == [{"name": "test", "description": "A test", "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}}}]

    def test_empty_tools(self) -> None:
        adapter = AnthropicAdapter()
        assert adapter.transform_tools([]) == []


class TestTransformMessages:
    def test_system_extracted(self) -> None:
        adapter = AnthropicAdapter()
        msgs = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ]
        result, system = adapter.transform_messages(msgs)
        assert system == "Be helpful"
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_function_result_converted_to_tool_result(self) -> None:
        adapter = AnthropicAdapter()
        msgs = [
            {"role": "function", "name": "test", "tool_use_id": "call_1", "content": "done"},
        ]
        result, _ = adapter.transform_messages(msgs)
        assert result[0]["role"] == "user"
        assert result[0]["content"][0]["type"] == "tool_result"
        assert result[0]["content"][0]["tool_use_id"] == "call_1"

    def test_function_result_without_id_skipped(self) -> None:
        adapter = AnthropicAdapter()
        msgs = [{"role": "function", "name": "test", "content": "done"}]
        result, _ = adapter.transform_messages(msgs)
        assert len(result) == 0

    def test_assistant_tool_call_json_converted(self) -> None:
        adapter = AnthropicAdapter()
        tool_json = json.dumps({
            "tool_calls": [{"id": "call_1", "name": "test_tool", "args": {"x": 1}}],
            "tool_use": {"id": "call_1", "name": "test_tool", "input": {"x": 1}},
        })
        msgs = [{"role": "assistant", "content": tool_json}]
        result, _ = adapter.transform_messages(msgs)
        msg = result[0]
        assert msg["role"] == "assistant"
        assert msg["content"][0]["type"] == "tool_use"
        assert msg["content"][0]["name"] == "test_tool"

    def test_images_converted(self) -> None:
        adapter = AnthropicAdapter()
        msgs = [
            {"role": "user", "content": "look", "_images": [{"mime_type": "image/png", "data": "abc"}]}
        ]
        result, _ = adapter.transform_messages(msgs)
        content = result[0]["content"]
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image"
        assert content[1]["source"]["type"] == "base64"


class TestExtractResponse:
    def test_text_response(self) -> None:
        adapter = AnthropicAdapter()
        raw = {"content": [{"type": "text", "text": "Hello"}], "stop_reason": "end_turn"}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "Hello"

    def test_tool_use_response(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {"type": "text", "text": "Let me help"},
                {"type": "tool_use", "id": "call_1", "name": "ha_control", "input": {"x": 1}},
            ],
            "stop_reason": "tool_use",
        }
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["tool_calls"][0]["name"] == "ha_control"
        assert result["text"] == "Let me help"

    def test_multiple_tool_calls(self) -> None:
        adapter = AnthropicAdapter()
        raw = {
            "content": [
                {"type": "tool_use", "id": "c1", "name": "t1", "input": {}},
                {"type": "tool_use", "id": "c2", "name": "t2", "input": {}},
            ],
            "stop_reason": "tool_use",
        }
        result = adapter.extract_response(raw)
        assert len(result["tool_calls"]) == 2

    def test_empty_content(self) -> None:
        adapter = AnthropicAdapter()
        raw = {"content": []}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == ""


class TestExtractStreamEvents:
    def test_text_delta(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()
        event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hi"}}
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == [{"type": "text", "content": "Hi"}]

    def test_tool_use_flow(self) -> None:
        adapter = AnthropicAdapter()
        acc = ToolAccumulator()
        # content_block_start
        e1 = {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "call_1", "name": "test"}}
        c1 = adapter.extract_stream_events(e1, acc)
        assert c1 == []

        # input_json_delta
        e2 = {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{\"x\": 1}"}}
        c2 = adapter.extract_stream_events(e2, acc)
        assert c2 == []

        # message_stop flushes
        e3 = {"type": "message_stop"}
        c3 = adapter.extract_stream_events(e3, acc)
        assert len(c3) == 1
        assert c3[0]["type"] == "tool_call"
        assert c3[0]["name"] == "test"
        assert c3[0]["args"] == {"x": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_anthropic_adapter.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement AnthropicAdapter**

```python
"""Anthropic adapter — shared by both API key and OAuth providers."""
from __future__ import annotations

import json
import logging
from typing import Any

from ...core.tool_call_codec import extract_tool_calls_from_assistant_content
from .base import ProviderAdapter
from .stream_utils import ToolAccumulator

_LOGGER = logging.getLogger(__name__)


class AnthropicAdapter(ProviderAdapter):
    """Adapter for Anthropic Claude API.

    Handles:
    - Tool schemas: function.parameters -> input_schema
    - Messages: system extracted, function role -> user tool_result, assistant tool JSON -> tool_use blocks
    - Images: _images -> Anthropic image source blocks
    - Response: content blocks -> canonical format
    - Streaming: Anthropic event types -> normalized chunks
    """

    def transform_tools(self, openai_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                result.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
        return result

    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        system_content: str | None = None
        filtered: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_content = content
            elif role == "function":
                tool_use_id = msg.get("tool_use_id")
                if not tool_use_id:
                    _LOGGER.warning("Skipping tool_result without tool_use_id for '%s'", msg.get("name", "unknown"))
                    continue
                filtered.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": content}],
                })
            elif role == "assistant" and content:
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        calls = extract_tool_calls_from_assistant_content(parsed)
                        if calls:
                            blocks = [
                                {"type": "tool_use", "id": c.get("id", ""), "name": c.get("name", ""), "input": c.get("args", {})}
                                for c in calls
                            ]
                            filtered.append({"role": "assistant", "content": blocks})
                            continue
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
                filtered.append({"role": role, "content": content})
            elif role == "user" and msg.get("_images"):
                content_blocks: list[dict[str, Any]] = [{"type": "text", "text": content}]
                for img in msg["_images"]:
                    content_blocks.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": img["mime_type"], "data": img["data"]},
                    })
                filtered.append({"role": "user", "content": content_blocks})
            elif content:
                filtered.append({"role": role, "content": content})

        return filtered, system_content

    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        content_blocks = raw_response.get("content", [])
        if not content_blocks:
            return {"type": "text", "content": "", "finish_reason": "stop"}

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "args": block.get("input", {}),
                })

        if tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": tool_calls,
                "text": " ".join(text_parts) if text_parts else None,
                "finish_reason": "tool_calls",
            }

        return {"type": "text", "content": " ".join(text_parts) if text_parts else "", "finish_reason": "stop"}

    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: ToolAccumulator
    ) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        event_type = event_data.get("type", "")

        if event_type == "content_block_start":
            block = event_data.get("content_block", {})
            if block.get("type") == "tool_use":
                index = int(event_data.get("index", 0))
                # Register the tool with id/name but NO args yet.
                # Anthropic sends {} as start input and streams real args
                # via input_json_delta — so we must NOT serialize the empty
                # dict here or it will break JSON concatenation.
                tool_acc.add_fragment(
                    index=index,
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    args_delta="",
                )
            return output

        if event_type == "content_block_delta":
            delta = event_data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    output.append({"type": "text", "content": text})
                return output

            if delta_type == "input_json_delta":
                index = int(event_data.get("index", 0))
                partial_json = delta.get("partial_json", "")
                if partial_json:
                    tool_acc.add_fragment(index=index, id=None, name=None, args_delta=partial_json)
                return output

        if event_type in {"message_delta", "message_stop"}:
            if tool_acc.has_pending:
                for tool in tool_acc.flush_all():
                    output.append({"type": "tool_call", **tool})

        return output
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_anthropic_adapter.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/providers/adapters/anthropic_adapter.py tests/test_providers/test_adapters/test_anthropic_adapter.py
git commit -m "add Anthropic adapter"
```

---

### Task 5: Gemini adapter

**Files:**
- Create: `custom_components/homeclaw/providers/adapters/gemini_adapter.py`
- Test: `tests/test_providers/test_adapters/test_gemini_adapter.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for Gemini adapter."""
from __future__ import annotations

import json

from custom_components.homeclaw.providers.adapters.gemini_adapter import GeminiAdapter
from custom_components.homeclaw.providers.adapters.stream_utils import ToolAccumulator


class TestTransformTools:
    def test_converts_to_function_declarations(self) -> None:
        adapter = GeminiAdapter()
        tools = [
            {"type": "function", "function": {"name": "test", "description": "A test", "parameters": {"type": "object"}}}
        ]
        result = adapter.transform_tools(tools)
        assert len(result) == 1
        assert "functionDeclarations" in result[0]
        assert result[0]["functionDeclarations"][0]["name"] == "test"

    def test_empty_tools(self) -> None:
        adapter = GeminiAdapter()
        assert adapter.transform_tools([]) == []


class TestTransformMessages:
    def test_system_extracted(self) -> None:
        adapter = GeminiAdapter()
        msgs = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ]
        result, system = adapter.transform_messages(msgs)
        assert system == "Be helpful"
        assert result[0]["role"] == "user"
        assert result[0]["parts"][0]["text"] == "Hi"

    def test_assistant_text(self) -> None:
        adapter = GeminiAdapter()
        msgs = [{"role": "assistant", "content": "Hello!"}]
        result, _ = adapter.transform_messages(msgs)
        assert result[0]["role"] == "model"
        assert result[0]["parts"][0]["text"] == "Hello!"

    def test_function_result(self) -> None:
        adapter = GeminiAdapter()
        msgs = [{"role": "function", "name": "test", "content": "{\"result\": \"ok\"}"}]
        result, _ = adapter.transform_messages(msgs)
        assert result[0]["role"] == "user"
        assert "functionResponse" in result[0]["parts"][0]

    def test_images(self) -> None:
        adapter = GeminiAdapter()
        msgs = [{"role": "user", "content": "look", "_images": [{"mime_type": "image/png", "data": "abc"}]}]
        result, _ = adapter.transform_messages(msgs)
        parts = result[0]["parts"]
        assert parts[0]["text"] == "look"
        assert parts[1]["inlineData"]["mimeType"] == "image/png"

    def test_assistant_tool_call_preserved(self) -> None:
        adapter = GeminiAdapter()
        tool_json = json.dumps({
            "tool_calls": [{"id": "c1", "name": "test", "args": {"x": 1}}],
            "tool_use": {"id": "c1", "name": "test", "input": {"x": 1}},
        })
        msgs = [{"role": "assistant", "content": tool_json}]
        result, _ = adapter.transform_messages(msgs)
        assert result[0]["role"] == "model"
        assert "functionCall" in result[0]["parts"][0]


class TestExtractResponse:
    def test_text_response(self) -> None:
        adapter = GeminiAdapter()
        raw = {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == "Hello"

    def test_function_call_response(self) -> None:
        adapter = GeminiAdapter()
        raw = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "test", "args": {"x": 1}}}]}}]}
        result = adapter.extract_response(raw)
        assert result["type"] == "tool_calls"
        assert result["tool_calls"][0]["name"] == "test"

    def test_empty_candidates(self) -> None:
        adapter = GeminiAdapter()
        raw = {"candidates": []}
        result = adapter.extract_response(raw)
        assert result["type"] == "text"
        assert result["content"] == ""


class TestExtractStreamEvents:
    def test_text_chunk(self) -> None:
        adapter = GeminiAdapter()
        acc = ToolAccumulator()
        event = {"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]}
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == [{"type": "text", "content": "Hi"}]

    def test_tool_call_chunk(self) -> None:
        adapter = GeminiAdapter()
        acc = ToolAccumulator()
        event = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "test", "args": {"x": 1}}, "thoughtSignature": "sig123"}]}}]}
        chunks = adapter.extract_stream_events(event, acc)
        assert len(chunks) == 1
        assert chunks[0]["type"] == "tool_call"
        assert chunks[0]["name"] == "test"
        assert chunks[0].get("thought_signature") == "sig123"
        assert "_raw_function_call" in chunks[0]

    def test_thinking_parts_skipped(self) -> None:
        adapter = GeminiAdapter()
        acc = ToolAccumulator()
        event = {"candidates": [{"content": {"parts": [{"thought": True, "text": "thinking..."}]}}]}
        chunks = adapter.extract_stream_events(event, acc)
        assert chunks == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_gemini_adapter.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement GeminiAdapter**

The GeminiAdapter delegates to existing `_gemini_convert.py` pure functions for message and tool conversion, adding only the new `extract_response()` and `extract_stream_events()` methods.

```python
"""Gemini adapter — shared by both API key and OAuth providers."""
from __future__ import annotations

import logging
from typing import Any

from .._gemini_convert import convert_messages, convert_tools, process_gemini_chunk
from .base import ProviderAdapter
from .stream_utils import ToolAccumulator

_LOGGER = logging.getLogger(__name__)


class GeminiAdapter(ProviderAdapter):
    """Adapter for Google Gemini API.

    Delegates message/tool conversion to existing _gemini_convert pure functions.
    Adds canonical response extraction and streaming event normalization.
    """

    def transform_tools(self, openai_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return convert_tools(openai_tools)

    def transform_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        return convert_messages(messages)

    def extract_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        candidates = raw_response.get("candidates", [])
        if not candidates:
            return {"type": "text", "content": "", "finish_reason": "stop"}

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for part in parts:
            if part.get("thought"):
                continue
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                call: dict[str, Any] = {
                    "id": f"gemini_{fc.get('name', '')}",
                    "name": fc.get("name", ""),
                    "args": fc.get("args", {}),
                }
                if part.get("thoughtSignature"):
                    call["thought_signature"] = part["thoughtSignature"]
                call["_raw_function_call"] = part
                tool_calls.append(call)

        if tool_calls:
            return {
                "type": "tool_calls",
                "tool_calls": tool_calls,
                "text": " ".join(text_parts) if text_parts else None,
                "finish_reason": "tool_calls",
            }

        return {
            "type": "text",
            "content": " ".join(text_parts) if text_parts else "",
            "finish_reason": "stop",
        }

    def extract_stream_events(
        self, event_data: dict[str, Any], tool_acc: ToolAccumulator
    ) -> list[dict[str, Any]]:
        """Process a Gemini streaming chunk using process_gemini_chunk.

        Gemini sends complete tool calls in single chunks (no incremental
        accumulation needed), so tool_acc is unused here but kept for
        interface consistency.
        """
        return process_gemini_chunk(event_data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_adapters/test_gemini_adapter.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/homeclaw/providers/adapters/gemini_adapter.py tests/test_providers/test_adapters/test_gemini_adapter.py
git commit -m "add Gemini adapter"
```

---

### Task 6: Wire adapters into OpenAI provider

**Files:**
- Modify: `custom_components/homeclaw/providers/openai.py`

This task replaces the inline format conversion in `openai.py` with calls to the adapter. The provider's HTTP, auth, and retry logic stays. Format conversion gets delegated.

- [ ] **Step 1: Write a test verifying adapter is used**

Add to `tests/test_providers/test_openai.py`:

```python
class TestOpenAIUsesAdapter:
    """Verify OpenAI provider delegates format conversion to adapter."""

    def test_has_adapter(self, hass: HomeAssistant) -> None:
        config = {"token": "sk-test"}
        provider = OpenAIProvider(hass, config)
        from custom_components.homeclaw.providers.adapters.openai_compat import OpenAICompatAdapter
        assert isinstance(provider.adapter, OpenAICompatAdapter)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_openai.py::TestOpenAIUsesAdapter -v`
Expected: FAIL — no attribute 'adapter'

- [ ] **Step 3: Wire adapter into OpenAI provider**

Modify `openai.py`:
1. Add `self.adapter = OpenAICompatAdapter()` in `__init__`
2. Replace `_convert_multimodal_messages()` in `_build_payload()` with `self.adapter.transform_messages()`
3. Replace `_extract_response()` body with call to `self.adapter.extract_response()` — keep backward-compat return format (JSON string for tool calls)
4. Replace `_extract_openai_stream_chunks()` in `get_response_stream()` with `self.adapter.extract_stream_events()` + shared `ToolAccumulator`
5. Remove SSE buffer parsing duplication — use `SSEParser`
6. Keep `_convert_multimodal_messages()` and `_extract_openai_stream_chunks()` as thin wrappers initially to avoid breaking Groq/OpenRouter subclasses

Key changes in `__init__`:
```python
from .adapters.openai_compat import OpenAICompatAdapter
from .adapters.stream_utils import SSEParser, ToolAccumulator
# ...
self.adapter = OpenAICompatAdapter()
```

Key changes in `_build_payload`:
```python
converted_messages, _ = self.adapter.transform_messages(messages)
# rest stays same, just uses converted_messages
```

Key changes in `_extract_response`:
```python
def _extract_response(self, response_data: dict[str, Any]) -> str:
    result = self.adapter.extract_response(response_data)
    if result["type"] == "tool_calls":
        return json.dumps({"tool_calls": response_data["choices"][0]["message"]["tool_calls"]})
    return result["content"]
```

Key changes in `get_response_stream`:
```python
async def get_response_stream(self, messages, **kwargs):
    # ... setup ...
    sse_parser = SSEParser()
    tool_acc = ToolAccumulator()
    # ... HTTP request ...
    async for raw_chunk in response.content.iter_any():
        text = raw_chunk.decode("utf-8", errors="ignore")
        for event_text in sse_parser.feed(text):
            if event_text == "[DONE]":
                done = True
                break
            event_data = json.loads(event_text)
            for chunk in self.adapter.extract_stream_events(event_data, tool_acc):
                yield chunk
    # flush
    for event_text in sse_parser.flush():
        if event_text == "[DONE]":
            break
        event_data = json.loads(event_text)
        for chunk in self.adapter.extract_stream_events(event_data, tool_acc):
            yield chunk
    # safety flush
    if tool_acc.has_pending:
        for tool in tool_acc.flush_all():
            yield {"type": "tool_call", **tool}
```

- [ ] **Step 4: Run ALL existing OpenAI tests**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_openai.py -v`
Expected: All PASS (including the new one)

- [ ] **Step 5: Run Groq and OpenRouter tests (they inherit from OpenAI)**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_groq.py tests/test_providers/test_openrouter.py tests/test_providers/test_xiaomi.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/homeclaw/providers/openai.py tests/test_providers/test_openai.py
git commit -m "wire OpenAI adapter into provider"
```

---

### Task 7: Wire adapter into Anthropic providers

**Files:**
- Modify: `custom_components/homeclaw/providers/anthropic.py`
- Modify: `custom_components/homeclaw/providers/anthropic_oauth.py`

- [ ] **Step 1: Wire adapter into anthropic.py**

Add `self.adapter = AnthropicAdapter()` in `__init__`. Replace:
- `_convert_tools()` → `self.adapter.transform_tools()`
- `_extract_system()` → `self.adapter.transform_messages()`
- `_extract_response()` body → `self.adapter.extract_response()` (keep str return for backward compat)
- `_extract_stream_chunks()` → `self.adapter.extract_stream_events()`
- SSE buffer parsing → `SSEParser`
- `pending_tools` dict → `ToolAccumulator`

Remove methods that are now in the adapter:
- `_assistant_tool_use_blocks()` — now in adapter
- `_convert_tools()` — now in adapter
- `_extract_system()` — now in adapter
- `_build_tool_call_chunk()` — now in ToolAccumulator
- `_extract_stream_chunks()` — now in adapter

- [ ] **Step 2: Wire adapter into anthropic_oauth.py**

This is the big win. Replace ~200 LOC of duplicated format conversion with:
```python
from .adapters.anthropic_adapter import AnthropicAdapter
from .adapters.stream_utils import SSEParser, ToolAccumulator
# ...
self.adapter = AnthropicAdapter()
```

Then in `get_response()` and `get_response_stream()`:
- Replace inline message conversion loop → `self.adapter.transform_messages()`
- Replace `_convert_tools()` → `self.adapter.transform_tools()`
- Replace response extraction → `self.adapter.extract_response()`
- Replace `_extract_stream_chunks()` → `self.adapter.extract_stream_events()`
- Replace SSE buffer parsing → `SSEParser`
- Remove `_assistant_tool_use_blocks()`, `_convert_tools()`, `_build_tool_call_chunk()`, `_extract_stream_chunks()` methods

Keep OAuth-specific: `_get_valid_token()`, `_trigger_reauth()`, `_transform_request()`, system prompt prefix logic, beta headers.

- [ ] **Step 3: Run ALL Anthropic tests**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_anthropic.py tests/test_providers/test_anthropic_oauth.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add custom_components/homeclaw/providers/anthropic.py custom_components/homeclaw/providers/anthropic_oauth.py
git commit -m "wire Anthropic adapter, remove duplicated format conversion"
```

---

### Task 8: Wire adapter into Gemini providers

**Files:**
- Modify: `custom_components/homeclaw/providers/gemini.py`
- Modify: `custom_components/homeclaw/providers/gemini_oauth.py`

- [ ] **Step 1: Wire adapter into gemini.py**

Add `self.adapter = GeminiAdapter()` in `__init__`. Replace:
- `_convert_messages()` → `self.adapter.transform_messages()`
- `_convert_tools()` → `self.adapter.transform_tools()`
- `_extract_response()` → `self.adapter.extract_response()` (keep str return for backward compat)

The changes are minimal since `_gemini_convert.py` functions are already shared.

- [ ] **Step 2: Wire adapter into gemini_oauth.py**

Add `self.adapter = GeminiAdapter()`. Replace format conversion calls with adapter calls. Keep all OAuth, project ID, model fallback, retry logic unchanged.

- [ ] **Step 3: Run ALL Gemini tests**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/test_providers/test_gemini.py tests/test_providers/test_gemini_oauth.py tests/test_providers/test_gemini_convert.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add custom_components/homeclaw/providers/gemini.py custom_components/homeclaw/providers/gemini_oauth.py
git commit -m "wire Gemini adapter into providers"
```

---

### Task 9: Simplify core — FunctionCallParser, tool_call_codec, ToolSchemaConverter

**Files:**
- Modify: `custom_components/homeclaw/core/function_call_parser.py`
- Modify: `custom_components/homeclaw/core/tool_call_codec.py`
- Modify: `custom_components/homeclaw/function_calling.py`

- [ ] **Step 1: Simplify tool_call_codec.py**

`build_assistant_tool_message()` — remove the Anthropic compat `tool_use` + `additional_tool_calls` fields. Only store canonical `tool_calls`:

```python
def build_assistant_tool_message(tool_calls: list[dict[str, Any]]) -> str:
    normalized = normalize_tool_calls(tool_calls)
    return json.dumps({"tool_calls": normalized})
```

`extract_tool_calls_from_assistant_content()` — keep the canonical `tool_calls` parsing. Keep Anthropic `tool_use` and Gemini `functionCall` fallbacks as they're needed for reading OLD conversation history. Don't remove those — they support historical data.

- [ ] **Step 2: Remove unused ToolSchemaConverter methods**

In `function_calling.py`, remove `to_anthropic_format()` and `to_gemini_format()` from `ToolSchemaConverter`. Keep `to_openai_format()` and `_build_parameter_schema()`.

Also remove `FunctionCallHandler.parse_anthropic_response()` and `parse_gemini_response()` — these are replaced by adapters. Keep `parse_openai_response()` as it's used by `FunctionCallParser._try_openai()`.

- [ ] **Step 3: Run ALL tests**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/ -v --timeout=30`
Expected: All PASS. If any test used the removed methods, update them to use adapters instead.

- [ ] **Step 4: Commit**

```bash
git add custom_components/homeclaw/core/tool_call_codec.py custom_components/homeclaw/function_calling.py custom_components/homeclaw/core/function_call_parser.py
git commit -m "simplify core: remove provider-specific format code"
```

---

### Task 10: Full test suite + cleanup

**Files:**
- All files in `tests/` and `custom_components/homeclaw/`

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/ -v --timeout=60`
Expected: All PASS

- [ ] **Step 2: Run linters**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && black --check --diff custom_components/ tests/ && isort --check --diff custom_components/ tests/ && flake8 custom_components/ tests/`
Expected: No errors (fix any formatting issues)

- [ ] **Step 3: Remove dead imports and methods**

Search for any unused imports of removed functions (`to_anthropic_format`, `to_gemini_format`, `parse_anthropic_response`, `parse_gemini_response`) and remove them.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "cleanup: remove dead code after adapter migration"
```

- [ ] **Step 5: Run tests one final time**

Run: `cd /Users/anowak/Projects/homeAssistant/ai_agent_ha && pytest tests/ -v --timeout=60`
Expected: All PASS
