"""Tests for the OpenAI provider."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.providers import ProviderRegistry

# Import to trigger registration
from custom_components.homeclaw.providers import openai as openai_module  # noqa: F401
from custom_components.homeclaw.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestOpenAIProviderRegistration:
    """Tests for OpenAI provider registration."""

    def test_registered_in_registry(self) -> None:
        """Test that 'openai' is in available_providers()."""
        available = ProviderRegistry.available_providers()
        assert "openai" in available


class TestOpenAIProviderSupportsTools:
    """Tests for OpenAI provider tool support."""

    def test_supports_tools(self, hass: HomeAssistant) -> None:
        """Test that OpenAI provider returns True for supports_tools."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)

        assert provider.supports_tools is True


class TestOpenAIProviderBuildHeaders:
    """Tests for OpenAI provider header building."""

    def test_build_headers(self, hass: HomeAssistant) -> None:
        """Test Authorization Bearer token and Content-Type headers."""
        config = {"token": "sk-test-key-12345"}

        provider = OpenAIProvider(hass, config)
        headers = provider._build_headers()

        assert headers["Authorization"] == "Bearer sk-test-key-12345"
        assert headers["Content-Type"] == "application/json"


class TestOpenAIProviderBuildPayload:
    """Tests for OpenAI provider payload building."""

    def test_build_payload(self, hass: HomeAssistant) -> None:
        """Test that model and messages are in payload."""
        config = {"token": "sk-test-key", "model": "gpt-4"}

        provider = OpenAIProvider(hass, config)
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "gpt-4"
        assert payload["messages"] == messages

    def test_build_payload_default_model(self, hass: HomeAssistant) -> None:
        """Test that default model is used when not specified."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        messages = [{"role": "user", "content": "Hello"}]
        payload = provider._build_payload(messages)

        assert payload["model"] == "gpt-4o"
        assert payload["messages"] == messages

    def test_build_payload_with_tools(self, hass: HomeAssistant) -> None:
        """Test that tools are included when passed."""
        config = {"token": "sk-test-key", "model": "gpt-4"}

        provider = OpenAIProvider(hass, config)
        messages = [{"role": "user", "content": "Turn on the lights"}]
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

        payload = provider._build_payload(messages, tools=tools)

        assert payload["model"] == "gpt-4"
        assert payload["messages"] == messages
        assert payload["tools"] == tools

    def test_build_payload_converts_canonical_assistant_tool_calls(
        self, hass: HomeAssistant
    ) -> None:
        """Canonical assistant tool_calls JSON should map to OpenAI tool_calls field."""
        provider = OpenAIProvider(hass, {"token": "sk-test-key", "model": "gpt-4"})
        messages = [
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "tool_calls": [
                            {
                                "id": "toolu_1",
                                "name": "get_entity_state",
                                "args": {"entity_id": "light.kitchen"},
                            }
                        ]
                    }
                ),
            }
        ]

        payload = provider._build_payload(messages)
        msg = payload["messages"][0]
        assert msg["role"] == "assistant"
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["id"] == "toolu_1"
        assert msg["tool_calls"][0]["function"]["name"] == "get_entity_state"


class TestOpenAIProviderExtractResponse:
    """Tests for OpenAI provider response extraction."""

    def test_extract_response(self, hass: HomeAssistant) -> None:
        """Test extraction from choices[0].message.content."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        }

        result = provider._extract_response(response_data)

        assert result == "Hello! How can I help you today?"

    def test_extract_response_with_tool_calls(self, hass: HomeAssistant) -> None:
        """Test handling of tool_calls in response."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
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
            ],
        }

        result = provider._extract_response(response_data)

        # When tool_calls are present, return a JSON string with the tool calls
        parsed_result = json.loads(result)
        assert "tool_calls" in parsed_result
        assert len(parsed_result["tool_calls"]) == 1
        assert parsed_result["tool_calls"][0]["function"]["name"] == "turn_on_light"

    def test_extract_response_empty_content(self, hass: HomeAssistant) -> None:
        """Test handling of empty content in response."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)
        response_data = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                    },
                }
            ],
        }

        result = provider._extract_response(response_data)

        assert result == ""


class TestOpenAIProviderApiUrl:
    """Tests for OpenAI provider API URL."""

    def test_api_url(self, hass: HomeAssistant) -> None:
        """Test that api_url returns the correct OpenAI endpoint."""
        config = {"token": "sk-test-key"}

        provider = OpenAIProvider(hass, config)

        assert provider.api_url == "https://api.openai.com/v1/chat/completions"


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------


class TestOpenAIProviderExtractStreamChunks:
    """Unit tests for _extract_openai_stream_chunks static method."""

    def test_text_delta(self) -> None:
        """Text delta yields a text chunk."""
        event = {
            "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]
        }
        pending: dict[int, dict[str, Any]] = {}
        chunks = OpenAIProvider._extract_openai_stream_chunks(event, pending)

        assert len(chunks) == 1
        assert chunks[0] == {"type": "text", "content": "Hello"}
        assert pending == {}

    def test_tool_call_single(self) -> None:
        """Tool call start + args deltas + finish_reason yields tool_call chunk."""
        pending: dict[int, dict[str, Any]] = {}

        # First event: tool call start
        event1 = {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "id": "call_abc",
                        "function": {"name": "turn_on_light", "arguments": ""},
                    }]
                },
                "finish_reason": None,
            }]
        }
        chunks1 = OpenAIProvider._extract_openai_stream_chunks(event1, pending)
        assert chunks1 == []
        assert 0 in pending

        # Second event: argument fragment
        event2 = {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "function": {"arguments": '{"entity_id":'},
                    }]
                },
                "finish_reason": None,
            }]
        }
        OpenAIProvider._extract_openai_stream_chunks(event2, pending)

        # Third event: more arguments
        event3 = {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "function": {"arguments": ' "light.kitchen"}'},
                    }]
                },
                "finish_reason": None,
            }]
        }
        OpenAIProvider._extract_openai_stream_chunks(event3, pending)

        # Fourth event: finish
        event4 = {
            "choices": [{"delta": {}, "finish_reason": "tool_calls"}]
        }
        chunks4 = OpenAIProvider._extract_openai_stream_chunks(event4, pending)

        assert len(chunks4) == 1
        assert chunks4[0]["type"] == "tool_call"
        assert chunks4[0]["name"] == "turn_on_light"
        assert chunks4[0]["args"] == {"entity_id": "light.kitchen"}
        assert chunks4[0]["id"] == "call_abc"
        assert pending == {}

    def test_parallel_tool_calls(self) -> None:
        """Multiple tool call indices yield all tool_call chunks."""
        pending: dict[int, dict[str, Any]] = {}

        # Start two tool calls
        event1 = {
            "choices": [{
                "delta": {
                    "tool_calls": [
                        {"index": 0, "id": "call_1", "function": {"name": "tool_a", "arguments": ""}},
                        {"index": 1, "id": "call_2", "function": {"name": "tool_b", "arguments": ""}},
                    ]
                },
                "finish_reason": None,
            }]
        }
        OpenAIProvider._extract_openai_stream_chunks(event1, pending)
        assert len(pending) == 2

        # Args for both
        event2 = {
            "choices": [{
                "delta": {
                    "tool_calls": [
                        {"index": 0, "function": {"arguments": '{"x": 1}'}},
                        {"index": 1, "function": {"arguments": '{"y": 2}'}},
                    ]
                },
                "finish_reason": None,
            }]
        }
        OpenAIProvider._extract_openai_stream_chunks(event2, pending)

        # Finish
        event3 = {
            "choices": [{"delta": {}, "finish_reason": "tool_calls"}]
        }
        chunks = OpenAIProvider._extract_openai_stream_chunks(event3, pending)

        assert len(chunks) == 2
        assert chunks[0]["name"] == "tool_a"
        assert chunks[0]["args"] == {"x": 1}
        assert chunks[1]["name"] == "tool_b"
        assert chunks[1]["args"] == {"y": 2}

    def test_text_and_tool_calls_mixed(self) -> None:
        """Text content + tool calls in sequence."""
        pending: dict[int, dict[str, Any]] = {}

        # Text first
        ev_text = {
            "choices": [{"delta": {"content": "Let me help"}, "finish_reason": None}]
        }
        text_chunks = OpenAIProvider._extract_openai_stream_chunks(ev_text, pending)
        assert text_chunks == [{"type": "text", "content": "Let me help"}]

        # Then tool call
        ev_tool = {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "id": "call_x",
                        "function": {"name": "do_thing", "arguments": "{}"},
                    }]
                },
                "finish_reason": None,
            }]
        }
        OpenAIProvider._extract_openai_stream_chunks(ev_tool, pending)

        ev_finish = {
            "choices": [{"delta": {}, "finish_reason": "tool_calls"}]
        }
        tool_chunks = OpenAIProvider._extract_openai_stream_chunks(ev_finish, pending)
        assert len(tool_chunks) == 1
        assert tool_chunks[0]["type"] == "tool_call"
        assert tool_chunks[0]["name"] == "do_thing"

    def test_malformed_arguments(self) -> None:
        """Malformed JSON arguments yield tool_call with empty args."""
        pending: dict[int, dict[str, Any]] = {}

        ev1 = {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "id": "call_bad",
                        "function": {"name": "broken", "arguments": "{not valid json"},
                    }]
                },
                "finish_reason": None,
            }]
        }
        OpenAIProvider._extract_openai_stream_chunks(ev1, pending)

        ev2 = {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        chunks = OpenAIProvider._extract_openai_stream_chunks(ev2, pending)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "tool_call"
        assert chunks[0]["args"] == {}

    def test_empty_choices(self) -> None:
        """Event with no choices returns nothing."""
        pending: dict[int, dict[str, Any]] = {}
        chunks = OpenAIProvider._extract_openai_stream_chunks({"choices": []}, pending)
        assert chunks == []


def _make_sse_bytes(*events: str) -> list[bytes]:
    """Build raw SSE byte chunks from data strings."""
    parts = []
    for ev in events:
        parts.append(f"data: {ev}\n\n".encode())
    return parts


def _make_mock_response(status: int, sse_chunks: list[bytes] | None = None, text: str = ""):
    """Create a mock aiohttp response with async iterator over SSE chunks."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=text)

    if sse_chunks is not None:
        async def iter_any():
            for chunk in sse_chunks:
                yield chunk

        mock_resp.content = MagicMock()
        mock_resp.content.iter_any = iter_any

    return mock_resp


class _MockContextManager:
    """Reusable async context manager for mocked session.post."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return None


class TestOpenAIProviderGetResponseStream:
    """Integration tests for get_response_stream with mocked aiohttp."""

    @pytest.mark.asyncio
    async def test_stream_text(self, hass: HomeAssistant) -> None:
        """SSE text streaming yields text chunks."""
        sse = _make_sse_bytes(
            json.dumps({"choices": [{"delta": {"content": "Hello "}, "finish_reason": None}]}),
            json.dumps({"choices": [{"delta": {"content": "world"}, "finish_reason": "stop"}]}),
            "[DONE]",
        )
        mock_resp = _make_mock_response(200, sse)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=_MockContextManager(mock_resp))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            provider = OpenAIProvider(hass, {"token": "sk-test"})
            chunks = []
            async for chunk in provider.get_response_stream(
                [{"role": "user", "content": "hi"}]
            ):
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == {"type": "text", "content": "Hello "}
        assert chunks[1] == {"type": "text", "content": "world"}

    @pytest.mark.asyncio
    async def test_stream_tool_call(self, hass: HomeAssistant) -> None:
        """SSE tool call streaming yields tool_call chunk."""
        sse = _make_sse_bytes(
            json.dumps({"choices": [{
                "delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "lights_on", "arguments": ""}}]},
                "finish_reason": None,
            }]}),
            json.dumps({"choices": [{
                "delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"room": "kitchen"}'}}]},
                "finish_reason": None,
            }]}),
            json.dumps({"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}),
            "[DONE]",
        )
        mock_resp = _make_mock_response(200, sse)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=_MockContextManager(mock_resp))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            provider = OpenAIProvider(hass, {"token": "sk-test"})
            chunks = []
            async for chunk in provider.get_response_stream(
                [{"role": "user", "content": "turn on lights"}]
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "tool_call"
        assert chunks[0]["name"] == "lights_on"
        assert chunks[0]["args"] == {"room": "kitchen"}
        assert chunks[0]["id"] == "call_1"

    @pytest.mark.asyncio
    async def test_stream_error_status(self, hass: HomeAssistant) -> None:
        """Non-200 status yields error chunk."""
        mock_resp = _make_mock_response(429, text="Rate limited")
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=_MockContextManager(mock_resp))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            provider = OpenAIProvider(hass, {"token": "sk-test"})
            chunks = []
            async for chunk in provider.get_response_stream(
                [{"role": "user", "content": "hi"}]
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "error"
        assert "429" in chunks[0]["message"]

    @pytest.mark.asyncio
    async def test_stream_sets_stream_true_in_payload(self, hass: HomeAssistant) -> None:
        """Verify stream=true is added to payload."""
        sse = _make_sse_bytes("[DONE]")
        mock_resp = _make_mock_response(200, sse)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=_MockContextManager(mock_resp))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            provider = OpenAIProvider(hass, {"token": "sk-test"})
            async for _ in provider.get_response_stream(
                [{"role": "user", "content": "hi"}]
            ):
                pass

        # Inspect the json= kwarg passed to session.post
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["stream"] is True

    @pytest.mark.asyncio
    async def test_subclass_uses_own_headers_and_url(self, hass: HomeAssistant) -> None:
        """Verify subclass headers/URL are used (test via XiaomiProvider)."""
        from custom_components.homeclaw.providers.xiaomi import XiaomiProvider

        sse = _make_sse_bytes(
            json.dumps({"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}),
            "[DONE]",
        )
        mock_resp = _make_mock_response(200, sse)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=_MockContextManager(mock_resp))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            provider = XiaomiProvider(hass, {"token": "xiaomi-key"})
            chunks = []
            async for chunk in provider.get_response_stream(
                [{"role": "user", "content": "hi"}]
            ):
                chunks.append(chunk)

        # Check URL
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://api.xiaomimimo.com/v1/chat/completions"

        # Check headers use api-key (Xiaomi's format)
        headers = call_args.kwargs.get("headers") or call_args[1].get("headers")
        assert headers["api-key"] == "xiaomi-key"
        assert "Authorization" not in headers

        # Check we got the text chunk
        assert chunks == [{"type": "text", "content": "ok"}]

    @pytest.mark.asyncio
    async def test_safety_flush_pending_tools(self, hass: HomeAssistant) -> None:
        """Pending tools are flushed even if finish_reason never arrives."""
        sse = _make_sse_bytes(
            json.dumps({"choices": [{
                "delta": {"tool_calls": [{"index": 0, "id": "call_z", "function": {"name": "act", "arguments": '{"a":1}'}}]},
                "finish_reason": None,
            }]}),
            # Stream ends without finish_reason="tool_calls"
            "[DONE]",
        )
        mock_resp = _make_mock_response(200, sse)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=_MockContextManager(mock_resp))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            provider = OpenAIProvider(hass, {"token": "sk-test"})
            chunks = []
            async for chunk in provider.get_response_stream(
                [{"role": "user", "content": "do thing"}]
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "tool_call"
        assert chunks[0]["name"] == "act"
        assert chunks[0]["args"] == {"a": 1}
